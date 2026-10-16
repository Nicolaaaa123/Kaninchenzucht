"""Stärken/Schwächen je Tier: Durchschnitt der eigenen Bewertungspositionen im
Vergleich zum Durchschnitt aller vorliegenden Bewertungskarten derselben Rasse.
Überdurchschnittlich = Stärke, unterdurchschnittlich = Schwäche -- aber nur bei einem
spürbaren Unterschied (MIN_DIFF_PCT), sonst würde auch "−0 %" als Schwäche erscheinen."""

import statistics
import uuid
from dataclasses import dataclass

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models

MIN_BREED_SAMPLES = 2
TOP_N = 3
# Unterschiede unter 1 Prozentpunkt (z.B. 0,2 Punkte bei einer 20er-Position) sind Rauschen
MIN_DIFF_PCT = 1.0


@dataclass
class CategoryComparison:
    category_label: str
    animal_avg_pct: float
    breed_avg_pct: float
    diff_pct: float
    breed_sample_count: int


def _category_pct_by_animal(db: Session, animal_id: uuid.UUID) -> dict[str, list[float]]:
    stmt = (
        select(models.EvaluationScore.category_label, models.EvaluationScore.points, models.EvaluationScore.max_points)
        .join(models.Evaluation)
        .where(models.Evaluation.animal_id == animal_id)
    )
    buckets: dict[str, list[float]] = {}
    for label, points, max_points in db.execute(stmt).all():
        if max_points:
            buckets.setdefault(label, []).append(points / max_points * 100)
    return buckets


def _category_pct_by_breed(db: Session, breed_id: uuid.UUID) -> dict[str, list[float]]:
    stmt = (
        select(models.EvaluationScore.category_label, models.EvaluationScore.points, models.EvaluationScore.max_points)
        .join(models.Evaluation)
        .join(models.Animal, models.Evaluation.animal_id == models.Animal.id)
        .where(models.Animal.breed_id == breed_id)
    )
    buckets: dict[str, list[float]] = {}
    for label, points, max_points in db.execute(stmt).all():
        if max_points:
            buckets.setdefault(label, []).append(points / max_points * 100)
    return buckets


def strengths_and_weaknesses(
    db: Session, animal_id: uuid.UUID, breed_id: uuid.UUID | None
) -> tuple[list[CategoryComparison], list[CategoryComparison]]:
    if not breed_id:
        return [], []
    own = _category_pct_by_animal(db, animal_id)
    if not own:
        return [], []
    breed = _category_pct_by_breed(db, breed_id)

    comparisons: list[CategoryComparison] = []
    for label, values in own.items():
        breed_values = breed.get(label, [])
        if len(breed_values) < MIN_BREED_SAMPLES:
            continue
        animal_avg = statistics.mean(values)
        breed_avg = statistics.mean(breed_values)
        comparisons.append(
            CategoryComparison(
                category_label=label,
                animal_avg_pct=round(animal_avg, 1),
                breed_avg_pct=round(breed_avg, 1),
                diff_pct=round(animal_avg - breed_avg, 1),
                breed_sample_count=len(breed_values),
            )
        )

    strengths = sorted((c for c in comparisons if c.diff_pct >= MIN_DIFF_PCT), key=lambda c: c.diff_pct, reverse=True)[:TOP_N]
    weaknesses = sorted((c for c in comparisons if c.diff_pct <= -MIN_DIFF_PCT), key=lambda c: c.diff_pct)[:TOP_N]
    return strengths, weaknesses
