import statistics
import uuid
from collections import Counter

from fastapi import APIRouter, Depends, HTTPException, Query
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db

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


@router.get("/yearly-evaluations", response_model=list[schemas.YearlyEvaluationStatOut])
def yearly_evaluations(
    breed_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Bewertungspositionen gruppiert nach Jahr, Rasse und Kategorie — zeigt,
    in welchen Jahren welche Positionen besonders gut/schlecht abschnitten."""
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

    buckets: dict[tuple[int, str, str], list[float]] = {}
    max_points_buckets: dict[tuple[int, str, str], list[int]] = {}
    for evaluated_on, category_label, points, max_points, breed_name in db.execute(stmt).all():
        if not max_points:
            continue
        key = (evaluated_on.year, breed_name or "Ohne Rasse", category_label)
        buckets.setdefault(key, []).append(points)
        max_points_buckets.setdefault(key, []).append(max_points)

    return [
        schemas.YearlyEvaluationStatOut(
            year=year,
            breed_name=breed_name,
            category_label=category_label,
            avg_points=round(statistics.mean(values), 1),
            # häufigster max_points-Wert der Position (Rassestandard) statt
            # Mittelwert, falls durch Alt-/Scanfehler mal ein falscher Wert
            # zwischendrin steckt.
            max_points=Counter(max_points_buckets[(year, breed_name, category_label)]).most_common(1)[0][0],
            sample_count=len(values),
        )
        for (year, breed_name, category_label), values in sorted(buckets.items())
    ]
