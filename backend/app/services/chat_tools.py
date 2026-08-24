"""Read-only Datenbank-Werkzeuge für den KI-Chat-Assistenten.

Jedes Tool ist bewusst lesend/eng begrenzt (keine Schreibzugriffe) und gibt
JSON-taugliche Python-Strukturen zurück, die als tool_result an Claude
zurückgereicht werden.
"""

import uuid
from typing import Any

from sqlalchemy import or_, select
from sqlalchemy.orm import Session, joinedload

from app import models

TOOL_DEFS: list[dict[str, Any]] = [
    {
        "name": "search_animals",
        "description": (
            "Sucht Tiere im Zuchtbestand nach Rasse, Geschlecht, Status oder Freitext "
            "(Chip-Nummer, Ohrmarke oder Name). Alle Parameter sind optional; ohne "
            "Parameter werden alle Tiere zurückgegeben (max. 50)."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "search": {"type": "string", "description": "Freitext für Chip-Nummer/Ohrmarke/Name"},
                "breed_name": {"type": "string", "description": "Rassename, z.B. 'Farbenzwerg'"},
                "sex": {"type": "string", "enum": ["male", "female", "unknown"]},
                "status": {"type": "string", "enum": ["active", "sold", "deceased", "retired"]},
            },
        },
    },
    {
        "name": "get_animal_detail",
        "description": (
            "Liefert alle Details zu einem Tier: Stammdaten, Rasse, Box, Eltern, "
            "Gewichtshistorie und alle Bewertungen. Identifizierung per Chip-Nummer, "
            "Ohrmarke oder (Teil-)Name."
        ),
        "input_schema": {
            "type": "object",
            "properties": {"identifier": {"type": "string"}},
            "required": ["identifier"],
        },
    },
    {
        "name": "get_siblings",
        "description": "Findet Geschwister eines Tieres (gleiche Mutter oder gleicher Vater).",
        "input_schema": {
            "type": "object",
            "properties": {"identifier": {"type": "string"}},
            "required": ["identifier"],
        },
    },
    {
        "name": "find_weak_category",
        "description": (
            "Findet Tiere, deren letzte Bewertung in einer bestimmten Bewertungsposition "
            "(z.B. 'Fell, Fellhaut und Grannenhaare' oder 'Farbe und Glanz') unterhalb "
            "eines Prozent-Schwellenwerts vom Höchstwert liegt. Nützlich für Fragen wie "
            "'welche Tiere haben eine schwache Fellbewertung'."
        ),
        "input_schema": {
            "type": "object",
            "properties": {
                "category_label": {"type": "string"},
                "max_pct": {"type": "number", "description": "Schwellenwert in Prozent, Standard 70"},
            },
            "required": ["category_label"],
        },
    },
    {
        "name": "list_breeds",
        "description": "Listet alle hinterlegten Rassen mit Gruppe und Gewichtsvorgaben.",
        "input_schema": {"type": "object", "properties": {}},
    },
]


def _find_animal(db: Session, identifier: str, tenant_id: uuid.UUID) -> models.Animal | None:
    needle = identifier.strip()
    if not needle:
        return None
    return db.execute(
        select(models.Animal)
        .options(joinedload(models.Animal.breed))
        .where(
            models.Animal.tenant_id == tenant_id,
            (models.Animal.chip_number.ilike(f"%{needle}%"))
            | (models.Animal.tattoo_number.ilike(f"%{needle}%"))
            | (models.Animal.name.ilike(f"%{needle}%")),
        )
        .limit(1)
    ).scalars().first()


def _animal_summary(a: models.Animal) -> dict[str, Any]:
    return {
        "id": str(a.id),
        "chip_number": a.chip_number,
        "tattoo_number": a.tattoo_number,
        "name": a.name,
        "sex": a.sex.value,
        "status": a.status.value,
        "breed": a.breed.name if a.breed else None,
        "birth_date": a.birth_date.isoformat() if a.birth_date else None,
    }


def search_animals(db: Session, tenant_id: uuid.UUID, search: str | None = None, breed_name: str | None = None,
                    sex: str | None = None, status: str | None = None) -> dict[str, Any]:
    stmt = select(models.Animal).options(joinedload(models.Animal.breed)).where(models.Animal.tenant_id == tenant_id)
    if search:
        like = f"%{search}%"
        stmt = stmt.where(
            (models.Animal.chip_number.ilike(like))
            | (models.Animal.tattoo_number.ilike(like))
            | (models.Animal.name.ilike(like))
        )
    if breed_name:
        stmt = stmt.join(models.Breed).where(models.Breed.name.ilike(f"%{breed_name}%"))
    if sex:
        stmt = stmt.where(models.Animal.sex == models.Sex(sex))
    if status:
        stmt = stmt.where(models.Animal.status == models.AnimalStatus(status))
    animals = db.execute(stmt.limit(50)).unique().scalars().all()
    return {"count": len(animals), "animals": [_animal_summary(a) for a in animals]}


def get_animal_detail(db: Session, tenant_id: uuid.UUID, identifier: str) -> dict[str, Any]:
    a = _find_animal(db, identifier, tenant_id)
    if not a:
        return {"error": f"Kein Tier gefunden für '{identifier}'"}
    weights = db.execute(
        select(models.WeightEntry).where(models.WeightEntry.animal_id == a.id).order_by(models.WeightEntry.measured_on)
    ).scalars().all()
    evaluations = db.execute(
        select(models.Evaluation)
        .options(joinedload(models.Evaluation.scores))
        .where(models.Evaluation.animal_id == a.id)
        .order_by(models.Evaluation.evaluated_on.desc())
    ).unique().scalars().all()
    mother = db.get(models.Animal, a.mother_id) if a.mother_id else None
    father = db.get(models.Animal, a.father_id) if a.father_id else None
    return {
        **_animal_summary(a),
        "color_variant": a.color_variant,
        "notes": a.notes,
        "mother": _animal_summary(mother) if mother else None,
        "father": _animal_summary(father) if father else None,
        "weight_history": [{"date": w.measured_on.isoformat(), "grams": w.weight_grams} for w in weights],
        "evaluations": [
            {
                "date": e.evaluated_on.isoformat(),
                "show_name": e.show_name,
                "total_score": e.total_score,
                "scores": [{"category": s.category_label, "points": s.points, "max_points": s.max_points} for s in e.scores],
            }
            for e in evaluations
        ],
    }


def get_siblings(db: Session, tenant_id: uuid.UUID, identifier: str) -> dict[str, Any]:
    a = _find_animal(db, identifier, tenant_id)
    if not a:
        return {"error": f"Kein Tier gefunden für '{identifier}'"}
    if not a.mother_id and not a.father_id:
        return {"animal": _animal_summary(a), "siblings": [], "note": "Keine Eltern hinterlegt"}
    conditions = []
    if a.mother_id:
        conditions.append(models.Animal.mother_id == a.mother_id)
    if a.father_id:
        conditions.append(models.Animal.father_id == a.father_id)
    stmt = (
        select(models.Animal)
        .options(joinedload(models.Animal.breed))
        .where(models.Animal.id != a.id, models.Animal.tenant_id == tenant_id, or_(*conditions))
    )
    siblings = db.execute(stmt).unique().scalars().all()
    return {"animal": _animal_summary(a), "siblings": [_animal_summary(s) for s in siblings]}


def find_weak_category(db: Session, tenant_id: uuid.UUID, category_label: str, max_pct: float = 70) -> dict[str, Any]:
    scores = db.execute(
        select(models.EvaluationScore, models.Evaluation)
        .join(models.Evaluation, models.EvaluationScore.evaluation_id == models.Evaluation.id)
        .join(models.Animal, models.Evaluation.animal_id == models.Animal.id)
        .where(
            models.EvaluationScore.category_label.ilike(f"%{category_label}%"),
            models.Animal.tenant_id == tenant_id,
        )
    ).all()
    results = []
    seen_animal_ids = set()
    for score, evaluation in scores:
        if not score.max_points:
            continue
        pct = score.points / score.max_points * 100
        if pct <= max_pct and evaluation.animal_id not in seen_animal_ids:
            seen_animal_ids.add(evaluation.animal_id)
            a = db.get(models.Animal, evaluation.animal_id)
            if a:
                results.append({**_animal_summary(a), "category": score.category_label, "points_pct": round(pct, 1)})
    return {"category_searched": category_label, "threshold_pct": max_pct, "count": len(results), "animals": results}


def list_breeds(db: Session, tenant_id: uuid.UUID) -> dict[str, Any]:
    breeds = db.execute(
        select(models.Breed).where(models.Breed.tenant_id == tenant_id).order_by(models.Breed.name)
    ).scalars().all()
    return {
        "breeds": [
            {
                "name": b.name,
                "group": b.group.value if b.group else None,
                "ideal_weight_min_kg": b.ideal_weight_min_kg,
                "ideal_weight_max_kg": b.ideal_weight_max_kg,
            }
            for b in breeds
        ]
    }


def execute_tool(db: Session, tenant_id: uuid.UUID, name: str, tool_input: dict[str, Any]) -> dict[str, Any]:
    handlers = {
        "search_animals": lambda: search_animals(db, tenant_id, **tool_input),
        "get_animal_detail": lambda: get_animal_detail(db, tenant_id, **tool_input),
        "get_siblings": lambda: get_siblings(db, tenant_id, **tool_input),
        "find_weak_category": lambda: find_weak_category(db, tenant_id, **tool_input),
        "list_breeds": lambda: list_breeds(db, tenant_id),
    }
    handler = handlers.get(name)
    if not handler:
        return {"error": f"Unbekanntes Tool: {name}"}
    try:
        return handler()
    except Exception as e:  # bewusst breit: Tool-Fehler sollen als tool_result zurückgehen, nicht die Anfrage abbrechen
        return {"error": str(e)}
