import statistics
import uuid
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.services.seasons import season_label, season_start_year

router = APIRouter(prefix="/api/stats", tags=["stats"])


@router.get("/yearly-weights", response_model=list[schemas.YearlyWeightStatOut])
def yearly_weights(
    breed_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Gewichte gruppiert nach Jahr (und Rasse) — zum Vergleich der Jahrgänge."""
    stmt = (
        select(
            models.WeightEntry.measured_on, models.WeightEntry.weight_grams, models.Animal.breed_id, models.Breed.name
        )
        .select_from(models.WeightEntry)
        .join(models.Animal)
        .outerjoin(models.Breed)
        .where(models.Animal.tenant_id == current_user.tenant_id)
    )
    if breed_id:
        stmt = stmt.where(models.Animal.breed_id == breed_id)

    buckets: dict[tuple[int, str], list[int]] = {}
    for measured_on, weight_grams, _breed_id, breed_name in db.execute(stmt).all():
        key = (measured_on.year, breed_name or "Ohne Rasse")
        buckets.setdefault(key, []).append(weight_grams)

    return [
        schemas.YearlyWeightStatOut(
            year=year,
            breed_name=breed_name,
            avg_grams=round(statistics.mean(values), 1),
            min_grams=min(values),
            max_grams=max(values),
            sample_count=len(values),
        )
        for (year, breed_name), values in sorted(buckets.items())
    ]


@router.get("/evaluated-breeds", response_model=list[schemas.EvaluatedBreedOut])
def evaluated_breeds(
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Nur Rassen (samt Farbenschlägen), zu denen es mindestens eine
    Bewertungskarte gibt -- für die Rassen-/Farbenschlag-Filter der Auswertungen."""
    rows = db.execute(
        select(models.Breed.id, models.Breed.name, models.Animal.color_variant)
        .select_from(models.Evaluation)
        .join(models.Animal, models.Evaluation.animal_id == models.Animal.id)
        .join(models.Breed, models.Animal.breed_id == models.Breed.id)
        .where(models.Animal.tenant_id == current_user.tenant_id)
        .distinct()
    ).all()
    breeds: dict[uuid.UUID, schemas.EvaluatedBreedOut] = {}
    for breed_id, breed_name, color_variant in rows:
        entry = breeds.setdefault(
            breed_id, schemas.EvaluatedBreedOut(breed_id=breed_id, breed_name=breed_name, color_variants=[])
        )
        if color_variant and color_variant not in entry.color_variants:
            entry.color_variants.append(color_variant)
    result = sorted(breeds.values(), key=lambda b: b.breed_name)
    for b in result:
        b.color_variants.sort()
    return result


@router.get("/experts", response_model=schemas.ExpertsOverviewOut)
def experts_overview(
    breed_id: uuid.UUID | None = None,
    color_variant: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Auswertung der Bewertungskarten pro Experte (Preisrichter): wie viele
    Karten/Tiere, Durchschnittspunkte gesamt und je Position. Steht auf einer
    Karte mit " / " mehr als ein Experte, zählt sie für jeden von ihnen.
    Optional auf eine Rasse (und deren Farbenschlag) eingegrenzt."""
    stmt = (
        select(models.Evaluation)
        .options(joinedload(models.Evaluation.scores), joinedload(models.Evaluation.animal))
        .join(models.Animal, models.Evaluation.animal_id == models.Animal.id)
        .where(models.Animal.tenant_id == current_user.tenant_id)
        .order_by(models.Evaluation.evaluated_on.desc())
    )
    if breed_id:
        stmt = stmt.where(models.Animal.breed_id == breed_id)
    if color_variant:
        stmt = stmt.where(models.Animal.color_variant == color_variant)
    evaluations = db.execute(stmt).unique().scalars().all()

    by_expert: dict[str, list[models.Evaluation]] = {}
    without_expert = 0
    for ev in evaluations:
        names = [n.strip() for n in (ev.expert_name or "").split(" / ") if n.strip()]
        if not names:
            without_expert += 1
            continue
        for name in dict.fromkeys(names):
            by_expert.setdefault(name, []).append(ev)

    experts = []
    for name, evs in by_expert.items():
        totals = [e.total_score for e in evs if e.total_score is not None]
        position_buckets: dict[tuple[int, str], list[tuple[float, int]]] = {}
        for e in evs:
            for s in e.scores:
                position_buckets.setdefault((s.position_number, s.category_label), []).append((s.points, s.max_points))
        positions = [
            schemas.ExpertPositionAvgOut(
                position_number=pos,
                category_label=label,
                avg_points=round(statistics.mean(p for p, _ in values), 2),
                max_points=Counter(m for _, m in values).most_common(1)[0][0],
            )
            for (pos, label), values in sorted(position_buckets.items())
        ]
        experts.append(
            schemas.ExpertStatOut(
                expert_name=name,
                evaluation_count=len(evs),
                animal_count=len({e.animal_id for e in evs}),
                avg_total_score=round(statistics.mean(totals), 1) if totals else None,
                positions=positions,
                evaluations=[
                    schemas.ExpertEvaluationRefOut(
                        evaluation_id=e.id,
                        animal_id=e.animal_id,
                        animal_chip_number=e.animal.chip_number,
                        animal_name=e.animal.name,
                        evaluated_on=e.evaluated_on,
                        show_name=e.show_name,
                        total_score=e.total_score,
                    )
                    for e in evs
                ],
            )
        )
    experts.sort(key=lambda x: (-x.evaluation_count, x.expert_name))
    return schemas.ExpertsOverviewOut(experts=experts, without_expert_count=without_expert)


@router.get("/season-evaluations", response_model=list[schemas.SeasonEvaluationStatOut])
def season_evaluations(
    breed_id: uuid.UUID | None = None,
    color_variant: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Bewertungspositionen gruppiert nach Saison (1.9.–31.8.), Rasse und
    Kategorie — zeigt, in welchen Saisons welche Positionen besonders
    gut/schlecht abschnitten."""
    stmt = (
        select(
            models.Evaluation.evaluated_on,
            models.EvaluationScore.category_label,
            models.EvaluationScore.points,
            models.EvaluationScore.max_points,
            models.Breed.name,
        )
        .select_from(models.EvaluationScore)
        .join(models.Evaluation)
        .join(models.Animal, models.Evaluation.animal_id == models.Animal.id)
        .outerjoin(models.Breed)
        .where(models.Animal.tenant_id == current_user.tenant_id)
    )
    if breed_id:
        stmt = stmt.where(models.Animal.breed_id == breed_id)
    if color_variant:
        stmt = stmt.where(models.Animal.color_variant == color_variant)

    # Getrennt nach Positionsname UND Höchstpunktzahl: dieselbe Bezeichnung
    # kann je nach Kartenformat 10 oder 20 Punkte wert sein (z.B. "Farbe und
    # Glanz"), das darf nicht in einem Durchschnitt landen.
    buckets: dict[tuple[int, str, str, int], list[float]] = {}
    for evaluated_on, category_label, points, max_points, breed_name in db.execute(stmt).all():
        if not max_points:
            continue
        key = (season_start_year(evaluated_on), breed_name or "Ohne Rasse", category_label, max_points)
        buckets.setdefault(key, []).append(points)

    return [
        schemas.SeasonEvaluationStatOut(
            season=season_label(start_year),
            season_start=start_year,
            breed_name=breed_name,
            category_label=category_label,
            avg_points=round(statistics.mean(values), 1),
            max_points=max_points,
            sample_count=len(values),
        )
        for (start_year, breed_name, category_label, max_points), values in sorted(buckets.items())
    ]


@router.get("/season-totals", response_model=list[schemas.SeasonTotalOut])
def season_totals(
    breed_id: uuid.UUID | None = None,
    color_variant: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Durchschnittliche Gesamtpunktzahl je Saison und Rasse, umgerechnet auf
    100 Punkte. Jede Karte zählt als Ganzes (Summe ihrer Positionen), damit
    unterschiedliche Kartenformate die Auswertung nicht verfälschen."""
    stmt = (
        select(
            models.Evaluation.id,
            models.Evaluation.evaluated_on,
            models.EvaluationScore.points,
            models.EvaluationScore.max_points,
            models.Breed.name,
        )
        .select_from(models.EvaluationScore)
        .join(models.Evaluation)
        .join(models.Animal, models.Evaluation.animal_id == models.Animal.id)
        .outerjoin(models.Breed)
        .where(models.Animal.tenant_id == current_user.tenant_id)
    )
    if breed_id:
        stmt = stmt.where(models.Animal.breed_id == breed_id)
    if color_variant:
        stmt = stmt.where(models.Animal.color_variant == color_variant)

    cards: dict[uuid.UUID, dict] = {}
    for evaluation_id, evaluated_on, points, max_points, breed_name in db.execute(stmt).all():
        card = cards.setdefault(
            evaluation_id,
            {"on": evaluated_on, "breed": breed_name or "Ohne Rasse", "points": 0.0, "max": 0},
        )
        card["points"] += points
        card["max"] += max_points or 0

    buckets: dict[tuple[int, str], list[float]] = {}
    for card in cards.values():
        if card["max"] > 0:
            key = (season_start_year(card["on"]), card["breed"])
            buckets.setdefault(key, []).append(card["points"] / card["max"] * 100)

    return [
        schemas.SeasonTotalOut(
            season=season_label(start_year),
            season_start=start_year,
            breed_name=breed_name,
            avg_points=round(statistics.mean(values), 1),
            sample_count=len(values),
        )
        for (start_year, breed_name), values in sorted(buckets.items())
    ]
