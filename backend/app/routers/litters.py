import statistics
import uuid
from datetime import date

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.services.growth import descendants_growth_curve

router = APIRouter(prefix="/api/litters", tags=["litters"])


def _members_query(tenant_id: uuid.UUID, litter_name: str | None = None):
    stmt = (
        select(models.Animal)
        .options(
            joinedload(models.Animal.breed),
            joinedload(models.Animal.mother),
            joinedload(models.Animal.father),
        )
        .where(
            models.Animal.tenant_id == tenant_id,
            models.Animal.litter_name.is_not(None),
            models.Animal.litter_name != "",
        )
    )
    if litter_name is not None:
        stmt = stmt.where(models.Animal.litter_name == litter_name)
    return stmt


@router.get("", response_model=list[schemas.LitterSummaryOut])
def list_litters(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    """Alle benannten Würfe, gruppiert nach Wurfname — für die Wurf-Reiter bei
    den Tieren. Unbenannte Jungtiere (kein litter_name) erscheinen hier nicht;
    ein Wurfname lässt sich beim Anlegen oder nachträglich am Tier vergeben."""
    animals = db.execute(_members_query(current_user.tenant_id)).unique().scalars().all()

    groups: dict[str, list[models.Animal]] = {}
    for a in animals:
        groups.setdefault(a.litter_name, []).append(a)

    summaries = [_summary_from_members(litter_name, members) for litter_name, members in groups.items()]
    summaries.sort(key=lambda s: s.birth_date or date.min, reverse=True)
    return summaries


@router.patch("/{litter_name}", response_model=schemas.LitterSummaryOut)
def update_litter(
    litter_name: str,
    payload: schemas.LitterUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Sammel-Bearbeitung eines Wurfes: wendet Wurfname/Wurfdatum/Rasse auf alle
    Tiere des Wurfes an, Deckdatum auf die Mutter — statt jedes Tier einzeln
    öffnen zu müssen."""
    members = db.execute(_members_query(current_user.tenant_id, litter_name)).unique().scalars().all()
    if not members:
        raise HTTPException(status_code=404, detail="Wurf nicht gefunden")

    if payload.breed_id:
        breed = db.get(models.Breed, payload.breed_id)
        if not breed or breed.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=404, detail="Rasse nicht gefunden")

    new_name = payload.new_litter_name.strip() if payload.new_litter_name else None
    for m in members:
        if new_name:
            m.litter_name = new_name
        if payload.birth_date:
            m.birth_date = payload.birth_date
        if payload.breed_id:
            m.breed_id = payload.breed_id

    if payload.mating_date:
        mother_ids = {m.mother_id for m in members if m.mother_id}
        if len(mother_ids) == 1:
            mother = db.get(models.Animal, next(iter(mother_ids)))
            if mother:
                mother.mating_date = payload.mating_date

    db.commit()
    return _summary_from_members(new_name or litter_name, members)


def _summary_from_members(litter_name: str, members: list[models.Animal]) -> schemas.LitterSummaryOut:
    birth_dates = [m.birth_date for m in members if m.birth_date]
    breed_names = sorted({m.breed.name for m in members if m.breed})
    mothers = sorted({m.mother.chip_number for m in members if m.mother})
    fathers = sorted({m.father.chip_number for m in members if m.father})
    latest_weights = [m.weight_entries[-1].weight_grams for m in members if m.weight_entries]
    total_scores = [m.evaluations[-1].total_score for m in members if m.evaluations and m.evaluations[-1].total_score]
    return schemas.LitterSummaryOut(
        litter_name=litter_name,
        birth_date=min(birth_dates) if birth_dates else None,
        breed_name=", ".join(breed_names) if breed_names else None,
        mother_chip=", ".join(mothers) if mothers else None,
        father_chip=", ".join(fathers) if fathers else None,
        animal_count=len(members),
        avg_latest_weight_grams=round(statistics.mean(latest_weights), 1) if latest_weights else None,
        avg_total_score=round(statistics.mean(total_scores), 1) if total_scores else None,
    )


@router.get("/{litter_name}/animals", response_model=list[schemas.AnimalListItem])
def get_litter_animals(
    litter_name: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    from app.routers.animals import _list_item

    members = db.execute(_members_query(current_user.tenant_id, litter_name)).unique().scalars().all()
    if not members:
        raise HTTPException(status_code=404, detail="Wurf nicht gefunden")
    return [_list_item(db, a) for a in members]


@router.get("/{litter_name}/stats", response_model=schemas.LitterStatsOut)
def get_litter_stats(
    litter_name: str, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    """Durchschnittliche Gewichtskurve und positionsgenaue Durchschnittsbewertung
    des Wurfes — zum Vergleich der Würfe einer Saison."""
    members = db.execute(_members_query(current_user.tenant_id, litter_name)).unique().scalars().all()
    if not members:
        raise HTTPException(status_code=404, detail="Wurf nicht gefunden")

    member_ids = [m.id for m in members]
    evaluations = (
        db.execute(
            select(models.Evaluation)
            .options(joinedload(models.Evaluation.scores))
            .where(models.Evaluation.animal_id.in_(member_ids))
        )
        .unique()
        .scalars()
        .all()
    )

    buckets: dict[str, list[tuple[float, int, int]]] = {}
    for ev in evaluations:
        for s in ev.scores:
            buckets.setdefault(s.category_label, []).append((s.points, s.max_points, s.position_number))

    score_positions = []
    for label, values in sorted(buckets.items(), key=lambda kv: kv[1][0][2]):
        points = [p for p, _, _ in values]
        max_points = [m for _, m, _ in values if m]
        position_number = values[0][2]
        score_positions.append(
            schemas.LitterScorePositionOut(
                position_number=position_number,
                category_label=label,
                avg_points=round(statistics.mean(points), 1),
                max_points=max(set(max_points), key=max_points.count) if max_points else 0,
                sample_count=len(values),
            )
        )
    score_positions.sort(key=lambda p: p.position_number)

    total_scores = [ev.total_score for ev in evaluations if ev.total_score]

    weight_points = descendants_growth_curve(members)

    return schemas.LitterStatsOut(
        litter_name=litter_name,
        animal_count=len(members),
        weight_curve=[schemas.DescendantGrowthPointOut(**vars(p)) for p in weight_points],
        score_positions=score_positions,
        avg_total_score=round(statistics.mean(total_scores), 1) if total_scores else None,
        evaluation_count=len(evaluations),
    )
