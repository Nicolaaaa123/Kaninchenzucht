import statistics
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.services.evaluation_stats import strengths_and_weaknesses
from app.services.feeding import calculate_feeding
from app.services.feeding_phase import detect_feeding_phase
from app.services.growth import (
    descendants_growth_curve,
    growth_rate_estimate,
    growth_status,
    own_trend_line,
    predict_weight_grams,
    suggest_target_weight_grams,
)
from app.services.mating import suggest_mates
from app.services.matching import match_animal_by_identifier
from app.services.naming import generate_names
from app.services.pedigree import PedigreeService

router = APIRouter(prefix="/api/animals", tags=["animals"])


def _load_query():
    return select(models.Animal).options(
        joinedload(models.Animal.breed).joinedload(models.Breed.scoring_positions),
        joinedload(models.Animal.breed).joinedload(models.Breed.growth_points),
        joinedload(models.Animal.feed),
        joinedload(models.Animal.cage_box).joinedload(models.CageBox.stall),
    )


def _get_owned(db: Session, animal_id: uuid.UUID, tenant_id: uuid.UUID, loaded: bool = False) -> models.Animal:
    stmt = (_load_query() if loaded else select(models.Animal)).where(
        models.Animal.id == animal_id, models.Animal.tenant_id == tenant_id
    )
    animal = db.execute(stmt).unique().scalar_one_or_none()
    if not animal:
        raise HTTPException(status_code=404, detail="Tier nicht gefunden")
    return animal


def _verify_related_ids(db: Session, tenant_id: uuid.UUID, data: dict) -> None:
    """Verhindert, dass ein Tier per API auf Rasse/Futter/Box/Eltern eines
    anderen Zuchtbetriebs verweist (die UI bietet ohnehin nur eigene Optionen
    an, das hier ist die serverseitige Absicherung dagegen)."""
    checks = [
        ("breed_id", models.Breed),
        ("feed_id", models.Feed),
        ("mother_id", models.Animal),
        ("father_id", models.Animal),
    ]
    for key, model in checks:
        value = data.get(key)
        if not value:
            continue
        obj = db.get(model, value)
        if not obj or obj.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail=f"Verknüpftes Objekt für {key} nicht gefunden")
    cage_box_id = data.get("cage_box_id")
    if cage_box_id:
        box = db.get(models.CageBox, cage_box_id)
        if not box or box.stall.tenant_id != tenant_id:
            raise HTTPException(status_code=404, detail="Box nicht gefunden")


def _animal_out(db: Session, animal: models.Animal) -> schemas.AnimalOut:
    out = schemas.AnimalOut.model_validate(animal)
    if animal.cage_box:
        out.cage_box_label = f"{animal.cage_box.stall.label} · Box {animal.cage_box.label}"
    out.inbreeding_coefficient = PedigreeService(db).inbreeding_coefficient(animal.mother_id, animal.father_id)
    return out


def _list_item(db: Session, animal: models.Animal) -> schemas.AnimalListItem:
    latest_weight = animal.weight_entries[-1].weight_grams if animal.weight_entries else None
    item = schemas.AnimalListItem.model_validate(animal)
    item.latest_weight_grams = latest_weight
    if animal.feed:
        detected = detect_feeding_phase(db, animal)
        calc = calculate_feeding(
            latest_weight,
            detected.phase,
            animal.feed.energy_mj_per_kg,
            detected.target_weight_grams,
            detected.target_date,
            litter_size=detected.litter_size,
            is_late_gestation=detected.is_late_gestation,
            container_capacity_grams=animal.feed.container_capacity_grams,
        )
        item.daily_feed_grams = calc.daily_feed_grams if calc else None
        item.container_fill_pct = calc.container_fill_pct if calc else None
    return item


@router.get("", response_model=list[schemas.AnimalListItem])
def list_animals(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
    search: str | None = Query(None, description="Sucht in Chip-Nummer/Name"),
    breed_id: uuid.UUID | None = None,
    color_variant: str | None = None,
    status: models.AnimalStatus | None = None,
    category: models.BreedingCategory | None = None,
):
    stmt = _load_query().where(models.Animal.tenant_id == current_user.tenant_id)
    if search:
        like = f"%{search}%"
        stmt = stmt.where((models.Animal.chip_number.ilike(like)) | (models.Animal.name.ilike(like)))
    if breed_id:
        stmt = stmt.where(models.Animal.breed_id == breed_id)
    if color_variant:
        stmt = stmt.where(models.Animal.color_variant == color_variant)
    if status:
        stmt = stmt.where(models.Animal.status == status)
    if category:
        stmt = stmt.where(models.Animal.category == category)
    stmt = stmt.order_by(models.Animal.chip_number)

    animals = db.execute(stmt).unique().scalars().all()
    return [_list_item(db, a) for a in animals]


@router.get("/pairing-check", response_model=schemas.PairingCheckOut)
def pairing_check(
    mother_id: uuid.UUID,
    father_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_owned(db, mother_id, current_user.tenant_id)
    _get_owned(db, father_id, current_user.tenant_id)
    coeff = PedigreeService(db).inbreeding_coefficient(mother_id, father_id)
    if coeff >= 0.125:
        risk = "hoch"
    elif coeff >= 0.03125:
        risk = "mittel"
    else:
        risk = "niedrig"
    return schemas.PairingCheckOut(
        mother_id=mother_id, father_id=father_id, inbreeding_coefficient=coeff, risk_level=risk
    )


@router.get("/lookup", response_model=schemas.AnimalLookupOut)
def lookup_animal(
    identifier: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Ordnet eine gelesene Chip-/Tätowierung-Nummer einem Tier zu (z.B. für den
    Bluetooth-Chip-Scanner). Unterstützt auch nur die letzten paar Stellen."""
    matched, candidates = match_animal_by_identifier(db, identifier, current_user.tenant_id)
    return schemas.AnimalLookupOut(
        identifier=identifier,
        matched_animal=schemas.AnimalListItem.model_validate(matched) if matched else None,
        candidate_animals=[schemas.AnimalListItem.model_validate(a) for a in candidates],
    )


@router.get("/relatedness", response_model=schemas.RelatednessOut)
def get_relatedness(
    animal_a: uuid.UUID,
    animal_b: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_owned(db, animal_a, current_user.tenant_id)
    _get_owned(db, animal_b, current_user.tenant_id)
    coeff = PedigreeService(db).kinship(animal_a, animal_b)
    return schemas.RelatednessOut(animal_a=animal_a, animal_b=animal_b, coefficient=round(coeff, 4))


@router.post("", response_model=schemas.AnimalOut, status_code=201)
def create_animal(
    payload: schemas.AnimalCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if payload.sex == models.Sex.MALE and payload.feeding_stage in (
        models.FeedingStage.GESTATION,
        models.FeedingStage.LACTATION,
    ):
        raise HTTPException(status_code=422, detail="Trächtigkeit/Säugezeit ist bei Rammlern nicht möglich")
    if payload.sex == models.Sex.MALE and payload.mating_date:
        raise HTTPException(status_code=422, detail="Ein Deckdatum ist bei Rammlern nicht möglich")
    data = payload.model_dump()
    if db.execute(
        select(models.Animal).where(
            models.Animal.chip_number == data["chip_number"], models.Animal.tenant_id == current_user.tenant_id
        )
    ).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Chip-Nummer bereits vergeben")
    _verify_related_ids(db, current_user.tenant_id, data)
    animal = models.Animal(**data, tenant_id=current_user.tenant_id)
    db.add(animal)
    db.commit()
    animal = db.execute(_load_query().where(models.Animal.id == animal.id)).unique().scalar_one()
    return _animal_out(db, animal)


@router.post("/litter", response_model=schemas.LitterResultOut, status_code=201)
def create_litter(
    payload: schemas.LitterCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Legt für einen Wurf auf einmal mehrere Jungtiere an, statt sie einzeln
    eintragen zu müssen. Namen werden automatisch nach der Konvention
    vergeben (Rammler = Anfangsbuchstabe des Vaters, Zibbe = der Mutter),
    Chip-Nummern erhalten einen Platzhalter zur späteren Ersetzung."""
    mother = _get_owned(db, payload.mother_id, current_user.tenant_id)
    father = _get_owned(db, payload.father_id, current_user.tenant_id) if payload.father_id else None
    if payload.breed_id:
        _verify_related_ids(db, current_user.tenant_id, {"breed_id": payload.breed_id})
    total = payload.count_male + payload.count_female + payload.count_unknown
    if total <= 0:
        raise HTTPException(status_code=422, detail="Mindestens ein Jungtier angeben")

    breed_id = payload.breed_id or mother.breed_id

    if payload.mating_date:
        mother.mating_date = payload.mating_date

    male_letter = payload.male_name_letter or (father.name[0] if father and father.name else None)
    female_letter = payload.female_name_letter or (mother.name[0] if mother.name else None)
    if payload.male_names is not None and len(payload.male_names) == payload.count_male:
        male_names = payload.male_names
    else:
        male_names = generate_names(db, male_letter, payload.count_male, current_user.tenant_id, models.Sex.MALE)
    if payload.female_names is not None and len(payload.female_names) == payload.count_female:
        female_names = payload.female_names
    else:
        female_names = generate_names(
            db, female_letter, payload.count_female, current_user.tenant_id, models.Sex.FEMALE
        )

    created: list[models.Animal] = []

    def _chip_placeholder() -> str:
        return f"J-{uuid.uuid4().hex[:6].upper()}-{payload.birth_date.strftime('%y%m%d')}"

    for i in range(payload.count_male):
        created.append(
            models.Animal(
                tenant_id=current_user.tenant_id,
                chip_number=_chip_placeholder(),
                name=male_names[i],
                sex=models.Sex.MALE,
                birth_date=payload.birth_date,
                breed_id=breed_id,
                mother_id=mother.id,
                father_id=father.id if father else None,
                litter_name=payload.litter_name,
                notes=payload.notes,
            )
        )
    for i in range(payload.count_female):
        created.append(
            models.Animal(
                tenant_id=current_user.tenant_id,
                chip_number=_chip_placeholder(),
                name=female_names[i],
                sex=models.Sex.FEMALE,
                birth_date=payload.birth_date,
                breed_id=breed_id,
                mother_id=mother.id,
                father_id=father.id if father else None,
                litter_name=payload.litter_name,
                notes=payload.notes,
            )
        )
    for i in range(payload.count_unknown):
        created.append(
            models.Animal(
                tenant_id=current_user.tenant_id,
                chip_number=_chip_placeholder(),
                sex=models.Sex.UNKNOWN,
                birth_date=payload.birth_date,
                breed_id=breed_id,
                mother_id=mother.id,
                father_id=father.id if father else None,
                litter_name=payload.litter_name,
                notes=payload.notes,
            )
        )

    db.add_all(created)
    db.commit()
    return schemas.LitterResultOut(created=[_list_item(db, a) for a in created], count=len(created))


@router.get("/name-suggestions", response_model=schemas.NameSuggestionsOut)
def name_suggestions(
    letter: str | None = None,
    count: int = Query(1, ge=1, le=50),
    sex: models.Sex | None = None,
    exclude: str | None = Query(None, description="Kommagetrennte, bereits vergebene Namen im selben Formular"),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Schlägt Namen vor (z.B. für den Wurf-Namensgenerator) — auch einzeln
    zum Neu-Würfeln eines einzelnen Namens nutzbar (count=1)."""
    extra_exclude = {n.strip() for n in exclude.split(",") if n.strip()} if exclude else None
    return schemas.NameSuggestionsOut(
        names=generate_names(db, letter, count, current_user.tenant_id, sex, extra_exclude)
    )


@router.get("/{animal_id}", response_model=schemas.AnimalOut)
def get_animal(
    animal_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    animal = _get_owned(db, animal_id, current_user.tenant_id, loaded=True)
    return _animal_out(db, animal)


@router.patch("/{animal_id}", response_model=schemas.AnimalOut)
def update_animal(
    animal_id: uuid.UUID,
    payload: schemas.AnimalUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    animal = _get_owned(db, animal_id, current_user.tenant_id)
    data = payload.model_dump(exclude_unset=True)
    effective_sex = data.get("sex", animal.sex)
    if (
        data.get("feeding_stage") in (models.FeedingStage.GESTATION, models.FeedingStage.LACTATION)
        and effective_sex == models.Sex.MALE
    ):
        raise HTTPException(status_code=422, detail="Trächtigkeit/Säugezeit ist bei Rammlern nicht möglich")
    if data.get("mating_date") and effective_sex == models.Sex.MALE:
        raise HTTPException(status_code=422, detail="Ein Deckdatum ist bei Rammlern nicht möglich")
    if "chip_number" in data and data["chip_number"] != animal.chip_number:
        exists = db.execute(
            select(models.Animal).where(
                models.Animal.chip_number == data["chip_number"],
                models.Animal.tenant_id == current_user.tenant_id,
            )
        ).scalar_one_or_none()
        if exists:
            raise HTTPException(status_code=409, detail="Chip-Nummer bereits vergeben")
    _verify_related_ids(db, current_user.tenant_id, data)
    for key, value in data.items():
        setattr(animal, key, value)
    db.commit()
    animal = db.execute(_load_query().where(models.Animal.id == animal_id)).unique().scalar_one()
    return _animal_out(db, animal)


@router.delete("/{animal_id}", status_code=204)
def delete_animal(
    animal_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    animal = _get_owned(db, animal_id, current_user.tenant_id)
    try:
        db.delete(animal)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Tier kann nicht gelöscht werden, da es noch anderswo referenziert wird")


@router.get("/{animal_id}/children", response_model=list[schemas.AnimalListItem])
def list_children(
    animal_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    _get_owned(db, animal_id, current_user.tenant_id)
    stmt = _load_query().where(
        (models.Animal.mother_id == animal_id) | (models.Animal.father_id == animal_id)
    )
    animals = db.execute(stmt).unique().scalars().all()
    return [_list_item(db, a) for a in animals]


@router.get("/{animal_id}/pedigree", response_model=schemas.PedigreeNode)
def get_pedigree(
    animal_id: uuid.UUID,
    generations: int = Query(4, ge=1, le=6),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_owned(db, animal_id, current_user.tenant_id)
    tree = PedigreeService(db).build_tree(animal_id, generations)
    return tree


def _related_animals(db: Session, animal: models.Animal) -> list[models.Animal]:
    """Eltern + volle Geschwister (gleiche Mutter+Vater) — die 'Erfahrung der
    Vorfahren und der schon gehabten Jungen', aus der ein Zielgewicht
    abgeleitet werden kann."""
    related: list[models.Animal] = []
    if animal.mother_id:
        mother = db.get(models.Animal, animal.mother_id)
        if mother:
            related.append(mother)
    if animal.father_id:
        father = db.get(models.Animal, animal.father_id)
        if father:
            related.append(father)
    if animal.mother_id and animal.father_id:
        siblings = db.execute(
            select(models.Animal).where(
                models.Animal.mother_id == animal.mother_id,
                models.Animal.father_id == animal.father_id,
                models.Animal.id != animal.id,
            )
        ).scalars().all()
        related.extend(siblings)
    return related


@router.get("/{animal_id}/feeding-plan", response_model=schemas.FeedingPlanOut)
def get_feeding_plan(
    animal_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    animal = _get_owned(db, animal_id, current_user.tenant_id, loaded=True)
    latest_weight = animal.weight_entries[-1].weight_grams if animal.weight_entries else None

    detected = detect_feeding_phase(db, animal)

    calc = None
    if animal.feed:
        calc = calculate_feeding(
            latest_weight,
            detected.phase,
            animal.feed.energy_mj_per_kg,
            detected.target_weight_grams,
            detected.target_date,
            litter_size=detected.litter_size,
            is_late_gestation=detected.is_late_gestation,
            container_capacity_grams=animal.feed.container_capacity_grams,
        )

    # Rückkopplung: (a) entwickelt sich das Tier über mehrere Wiegungen
    # hinweg langsamer/schneller als von der Rassekurve erwartet, und (b) ist
    # das gesetzte Zieldatum beim aktuellen Tempo überhaupt noch erreichbar?
    # Läuft bei jedem Aufruf frisch, also automatisch bei jeder neuen
    # Gewichtseingabe neu.
    feedback_hint = None
    if calc and calc.required_daily_gain_grams is not None and calc.days_remaining is not None:
        sorted_entries = sorted(animal.weight_entries, key=lambda e: e.measured_on)
        if len(sorted_entries) >= 2:
            prev, latest = sorted_entries[-2], sorted_entries[-1]
            days_between = (latest.measured_on - prev.measured_on).days
            remaining_gain = (detected.target_weight_grams or 0) - (latest_weight or 0)
            if days_between > 0 and abs(remaining_gain) >= 5:
                actual_rate = (latest.weight_grams - prev.weight_grams) / days_between
                same_direction = actual_rate != 0 and (actual_rate > 0) == (remaining_gain > 0)
                if same_direction:
                    projected_days = remaining_gain / actual_rate
                    miss_days = round(projected_days - calc.days_remaining)
                    if miss_days > 3:
                        feedback_hint = (
                            f"Bei aktuellem Tempo wird das Zieldatum voraussichtlich um {miss_days} Tage "
                            "verfehlt — Futtermenge ggf. anpassen."
                        )
                else:
                    feedback_hint = (
                        "Bei aktuellem Tempo wird das Zieldatum voraussichtlich verfehlt — Tier entwickelt "
                        "sich nicht in die nötige Richtung. Futtermenge ggf. anpassen."
                    )
    if not feedback_hint and detected.phase == "growth" and animal.breed:
        rate = growth_rate_estimate(animal.breed, animal.birth_date, animal.weight_entries, animal.sex)
        if rate == "langsam":
            feedback_hint = "Zunahme über mehrere Wiegungen langsamer als erwartet — Futtermenge ggf. erhöhen."
        elif rate == "schnell":
            feedback_hint = "Zunahme über mehrere Wiegungen schneller als erwartet — im Blick behalten."

    return schemas.FeedingPlanOut(
        animal_id=animal.id,
        weight_grams=latest_weight,
        detected_phase=detected.phase,
        feed_id=animal.feed_id,
        feed_name=animal.feed.name if animal.feed else None,
        daily_feed_grams=calc.daily_feed_grams if calc else None,
        reason=calc.reason if calc else None,
        target_weight_grams=detected.target_weight_grams,
        target_date=detected.target_date,
        days_remaining=calc.days_remaining if calc else None,
        required_daily_gain_grams=calc.required_daily_gain_grams if calc else None,
        litter_size=detected.litter_size,
        gestation_week=detected.gestation_week,
        is_late_gestation=detected.is_late_gestation if detected.phase == "gestation" else None,
        phase_error=detected.error,
        feedback_hint=feedback_hint,
        container_fill_pct=calc.container_fill_pct if calc else None,
    )


@router.get("/{animal_id}/growth-plan", response_model=schemas.GrowthStatusOut)
def get_growth_plan(
    animal_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    animal = _get_owned(db, animal_id, current_user.tenant_id, loaded=True)
    latest_entry = animal.weight_entries[-1] if animal.weight_entries else None
    status = growth_status(
        breed=animal.breed,
        birth_date=animal.birth_date,
        latest_weight_grams=latest_entry.weight_grams if latest_entry else None,
        latest_weight_date=latest_entry.measured_on if latest_entry else None,
        target_date=animal.target_date,
        target_date_end=animal.target_date_end,
        sex=animal.sex,
    )

    growth_rate = None
    own_trend: list[tuple[float, float]] = []
    suggested_target = None
    target_source = None
    sample_count = 0
    if animal.breed:
        growth_rate = growth_rate_estimate(animal.breed, animal.birth_date, animal.weight_entries, animal.sex)
        if status.status == "voraus":
            own_trend = own_trend_line(animal.weight_entries, animal.birth_date)
        suggested_target, target_source, sample_count = suggest_target_weight_grams(
            animal.breed, animal.sex, _related_animals(db, animal)
        )

    return schemas.GrowthStatusOut(
        age_weeks=round(status.age_weeks, 1) if status.age_weeks is not None else None,
        predicted_weight_grams=round(status.predicted_weight_grams, 1) if status.predicted_weight_grams else None,
        actual_weight_grams=status.actual_weight_grams,
        deviation_pct=status.deviation_pct,
        status=status.status,
        peak=schemas.PeakWindowOut(start_date=status.peak.start_date, end_date=status.peak.end_date)
        if status.peak
        else None,
        target_date=animal.target_date,
        target_date_end=animal.target_date_end,
        target_date_in_peak_window=status.target_date_in_peak_window,
        growth_rate=growth_rate,
        own_trend=[schemas.TrendPointOut(age_weeks=w, weight_grams=g) for w, g in own_trend],
        suggested_target_weight_grams=suggested_target,
        target_weight_source=target_source,
        target_weight_sample_count=sample_count,
    )


@router.get("/{animal_id}/feed-plan-year", response_model=schemas.FeedPlanYearOut)
def get_feed_plan_year(
    animal_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Prognostizierter Futterbedarf über die nächsten 52 Wochen, basierend
    auf der Wachstumskurve der Rasse ab dem heutigen Alter."""
    animal = _get_owned(db, animal_id, current_user.tenant_id, loaded=True)

    points: list[schemas.FeedPlanPointOut] = []
    if animal.breed and animal.birth_date:
        today = date.today()
        current_age_weeks = (today - animal.birth_date).days / 7
        for week in range(0, 53, 1):
            age_weeks = current_age_weeks + week
            predicted = predict_weight_grams(animal.breed, age_weeks)
            daily_grams = None
            if predicted and animal.feed:
                calc = calculate_feeding(
                    round(predicted), animal.feeding_stage, animal.feed.energy_mj_per_kg
                )
                daily_grams = calc.daily_feed_grams if calc else None
            points.append(
                schemas.FeedPlanPointOut(
                    week=week,
                    age_weeks=round(age_weeks, 1),
                    predicted_weight_grams=round(predicted, 1) if predicted else None,
                    daily_feed_grams=daily_grams,
                )
            )

    return schemas.FeedPlanYearOut(animal_id=animal.id, points=points)


@router.get("/{animal_id}/strengths-weaknesses", response_model=schemas.StrengthsWeaknessesOut)
def get_strengths_weaknesses(
    animal_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    animal = _get_owned(db, animal_id, current_user.tenant_id)
    strengths, weaknesses = strengths_and_weaknesses(db, animal_id, animal.breed_id)
    return schemas.StrengthsWeaknessesOut(
        strengths=[schemas.CategoryComparisonOut(**vars(c)) for c in strengths],
        weaknesses=[schemas.CategoryComparisonOut(**vars(c)) for c in weaknesses],
    )


@router.get("/{animal_id}/descendants-growth", response_model=schemas.DescendantsGrowthOut)
def get_descendants_growth(
    animal_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    _get_owned(db, animal_id, current_user.tenant_id)
    descendants = PedigreeService(db).descendants(animal_id)
    points = descendants_growth_curve(descendants)
    return schemas.DescendantsGrowthOut(
        animal_id=animal_id,
        descendant_count=len(descendants),
        points=[schemas.DescendantGrowthPointOut(**vars(p)) for p in points],
    )


@router.get("/{animal_id}/siblings-growth-curve", response_model=schemas.SiblingsGrowthCurveOut)
def get_siblings_growth_curve(
    animal_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Altersbasierte Durchschnittsgewichtskurve der vollen Geschwister
    (gleiche Mutter + Vater) dieses Tiers."""
    animal = _get_owned(db, animal_id, current_user.tenant_id)
    siblings: list[models.Animal] = []
    if animal.mother_id and animal.father_id:
        siblings = (
            db.execute(
                select(models.Animal)
                .options(joinedload(models.Animal.weight_entries))
                .where(
                    models.Animal.tenant_id == current_user.tenant_id,
                    models.Animal.mother_id == animal.mother_id,
                    models.Animal.father_id == animal.father_id,
                    models.Animal.id != animal.id,
                )
            )
            .unique()
            .scalars()
            .all()
        )
    points = descendants_growth_curve(siblings)
    return schemas.SiblingsGrowthCurveOut(
        animal_id=animal_id,
        sibling_count=len(siblings),
        points=[schemas.DescendantGrowthPointOut(**vars(p)) for p in points],
    )


@router.get("/{animal_id}/offspring-scores", response_model=schemas.OffspringScoresOut)
def get_offspring_scores(
    animal_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    _get_owned(db, animal_id, current_user.tenant_id)

    children = (
        db.execute(
            select(models.Animal).where(
                (models.Animal.mother_id == animal_id) | (models.Animal.father_id == animal_id)
            )
        )
        .scalars()
        .all()
    )
    child_ids = [c.id for c in children]

    evaluations = []
    if child_ids:
        evaluations = (
            db.execute(
                select(models.Evaluation)
                .options(joinedload(models.Evaluation.scores))
                .where(models.Evaluation.animal_id.in_(child_ids))
            )
            .unique()
            .scalars()
            .all()
        )

    buckets: dict[str, list[tuple[float, int]]] = {}
    for ev in evaluations:
        for s in ev.scores:
            buckets.setdefault(s.category_label, []).append((s.points, s.max_points))

    categories = []
    for label, values in buckets.items():
        pct_values = [p / m * 100 for p, m in values if m]
        categories.append(
            schemas.OffspringScoreCategory(
                category_label=label,
                average_points=round(statistics.mean(p for p, _ in values), 2),
                average_pct=round(statistics.mean(pct_values), 1) if pct_values else None,
                sample_count=len(values),
            )
        )

    return schemas.OffspringScoresOut(
        animal_id=animal_id,
        child_count=len(children),
        evaluation_count=len(evaluations),
        categories=categories,
    )


@router.get("/{animal_id}/mating-suggestions", response_model=list[schemas.MatingSuggestionOut])
def get_mating_suggestions(
    animal_id: uuid.UUID,
    weight_total: float = Query(1.0, ge=0),
    weight_inbreeding: float = Query(1.0, ge=0),
    weight_complement: float = Query(1.0, ge=0),
    weight_focus: float = Query(1.0, ge=0),
    focus_categories: list[str] = Query([]),
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    animal = _get_owned(db, animal_id, current_user.tenant_id)
    if animal.sex not in (models.Sex.MALE, models.Sex.FEMALE):
        raise HTTPException(status_code=422, detail="Geschlecht des Tieres muss bekannt sein")

    suggestions = suggest_mates(
        db, animal, weight_total, weight_inbreeding, weight_complement, weight_focus, focus_categories
    )
    return [
        schemas.MatingSuggestionOut(
            animal=schemas.AnimalListItem.model_validate(s.animal),
            total_score=s.total_score,
            inbreeding_coefficient=s.inbreeding_coefficient,
            complement_score=s.complement_score,
            focus_score=s.focus_score,
            final_score=s.final_score,
            reasons=s.reasons,
        )
        for s in suggestions
    ]
