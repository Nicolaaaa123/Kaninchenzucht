"""Paarungsvorschläge mit einstellbarem Fokus.

Kein genetisches Zuchtwert-Modell — eine transparente, nachvollziehbare
Faustregel, die vier Signale gewichtet zusammenführt:

1. Gesamtpunktzahl der letzten Bewertung des Partners (Qualität an sich)
2. Inzuchtkoeffizient der (hypothetischen) Nachkommen (niedriger = besser)
3. "Ergänzung": wie sehr die Stärken des Partners genau dort liegen, wo das
   Basistier in seiner letzten Bewertung schwächer abschnitt (über alle
   gemeinsamen Bewertungspositionen)
4. "Fokus-Positionen": frei wählbare einzelne Bewertungspositionen (z.B.
   "Farbe und Glanz"), bei denen gezielt nur die Stärke des Partners in genau
   diesen Positionen zählt — unabhängig davon, wie das Basistier dort selbst
   abschneidet

Jede Komponente wird auf 0–1 normiert, die vier Gewichte (Default je 1.0)
bestimmen den gewichteten Mittelwert. Die Rangliste ist als Diskussionsbasis
gedacht, nicht als automatische Zuchtentscheidung.
"""

import uuid
from dataclasses import dataclass, field

from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app import models
from app.services.pedigree import PedigreeService


@dataclass
class MatingCandidate:
    animal: models.Animal
    total_score: float | None
    inbreeding_coefficient: float
    complement_score: float | None
    focus_score: float | None
    final_score: float
    reasons: list[str] = field(default_factory=list)


def _latest_evaluation(db: Session, animal_id: uuid.UUID) -> models.Evaluation | None:
    return (
        db.execute(
            select(models.Evaluation)
            .options(joinedload(models.Evaluation.scores))
            .where(models.Evaluation.animal_id == animal_id)
            .order_by(models.Evaluation.evaluated_on.desc())
            .limit(1)
        )
        .unique()
        .scalar_one_or_none()
    )


def _pct_by_category(evaluation: models.Evaluation | None) -> dict[str, float]:
    if not evaluation:
        return {}
    return {s.category_label: (s.points / s.max_points * 100) for s in evaluation.scores if s.max_points}


def suggest_mates(
    db: Session,
    base_animal: models.Animal,
    weight_total: float = 1.0,
    weight_inbreeding: float = 1.0,
    weight_complement: float = 1.0,
    weight_focus: float = 1.0,
    focus_categories: list[str] | None = None,
    limit: int = 10,
) -> list[MatingCandidate]:
    if base_animal.sex not in (models.Sex.MALE, models.Sex.FEMALE):
        return []
    # Paarungsvorschläge nur innerhalb derselben Rasse -- ohne zugeordnete
    # Rasse beim Basistier lässt sich das nicht sinnvoll einschränken, dann
    # gibt es keine Vorschläge statt möglicherweise rassefremder Paare.
    if not base_animal.breed_id:
        return []
    opposite = models.Sex.FEMALE if base_animal.sex == models.Sex.MALE else models.Sex.MALE
    focus_categories = [c.strip() for c in (focus_categories or []) if c.strip()]

    candidates = (
        db.execute(
            select(models.Animal)
            .options(joinedload(models.Animal.breed))
            .where(
                models.Animal.sex == opposite,
                models.Animal.status == models.AnimalStatus.ACTIVE,
                models.Animal.id != base_animal.id,
                models.Animal.breed_id == base_animal.breed_id,
                models.Animal.tenant_id == base_animal.tenant_id,
            )
        )
        .unique()
        .scalars()
        .all()
    )
    if not candidates:
        return []

    pedigree = PedigreeService(db)
    base_eval = _latest_evaluation(db, base_animal.id)
    base_pct = _pct_by_category(base_eval)

    results: list[MatingCandidate] = []
    for candidate in candidates:
        cand_eval = _latest_evaluation(db, candidate.id)
        cand_pct = _pct_by_category(cand_eval)

        coefficient = pedigree.inbreeding_coefficient(base_animal.id, candidate.id)

        shared = set(base_pct) & set(cand_pct)
        complement_diffs = {label: cand_pct[label] - base_pct[label] for label in shared}
        complement_score = (
            sum(max(d, 0) for d in complement_diffs.values()) / len(complement_diffs) / 100
            if complement_diffs
            else None
        )

        focus_values = [cand_pct[label] for label in focus_categories if label in cand_pct]
        focus_score = (sum(focus_values) / len(focus_values) / 100) if focus_values else None

        total_norm = (cand_eval.total_score / 100) if cand_eval and cand_eval.total_score else None
        inbreeding_norm = max(0.0, 1 - coefficient)

        parts: list[tuple[float, float]] = [(inbreeding_norm, weight_inbreeding)]
        if total_norm is not None:
            parts.append((total_norm, weight_total))
        if complement_score is not None:
            parts.append((complement_score, weight_complement))
        if focus_score is not None:
            parts.append((focus_score, weight_focus))
        weight_sum = sum(w for _, w in parts) or 1.0
        final_score = sum(v * w for v, w in parts) / weight_sum

        reasons = []
        if cand_eval and cand_eval.total_score:
            reasons.append(f"Gesamtpunktzahl letzte Bewertung: {cand_eval.total_score}")
        reasons.append(f"Inzuchtkoeffizient der Nachkommen: {round(coefficient * 100, 2)}%")
        if focus_categories:
            for label in focus_categories:
                if label in cand_pct:
                    reasons.append(f"Fokus-Position „{label}“: {round(cand_pct[label], 1)}%")
                else:
                    reasons.append(f"Fokus-Position „{label}“: keine Bewertungsdaten")
        if complement_diffs:
            best = sorted(complement_diffs.items(), key=lambda kv: kv[1], reverse=True)[:2]
            for label, diff in best:
                if diff > 5:
                    reasons.append(
                        f"Stark bei {label} ({round(cand_pct[label], 1)}%), "
                        f"ergänzt deine Schwäche dort ({round(base_pct[label], 1)}%)"
                    )

        results.append(
            MatingCandidate(
                animal=candidate,
                total_score=cand_eval.total_score if cand_eval else None,
                inbreeding_coefficient=round(coefficient, 4),
                complement_score=round(complement_score, 3) if complement_score is not None else None,
                focus_score=round(focus_score, 3) if focus_score is not None else None,
                final_score=round(final_score, 4),
                reasons=reasons,
            )
        )

    results.sort(key=lambda r: r.final_score, reverse=True)
    return results[:limit]
