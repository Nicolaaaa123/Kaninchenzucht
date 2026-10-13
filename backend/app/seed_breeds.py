"""Befüllt die Rassentabelle mit den 42 vom Standard 2015 (Rassekaninchen
Schweiz) anerkannten Rassen inkl. Gewichtsvorgaben und Bewertungsskala.

Ausführen mit: venv\\Scripts\\python.exe -m app.seed_breeds
"""

import json
from pathlib import Path

from app.database import SessionLocal
from app.models import Breed, BreedGroup, BreedScoringPosition, Tenant

DATA_PATH = Path(__file__).parent / "data" / "ch_standard_breeds.json"


def load_breeds_data() -> list[dict]:
    with open(DATA_PATH, encoding="utf-8") as f:
        return json.load(f)


def seed_tenant_breeds(db, tenant: Tenant, breeds_data: list[dict] | None = None) -> tuple[int, int]:
    """Legt die Standard-Rassen für einen Zuchtbetrieb an (fehlende ergänzt,
    vorhandene bleiben). Kein Commit -- das macht der Aufrufer.
    Gibt (neu angelegt, bereits vorhanden) zurück."""
    breeds_data = breeds_data if breeds_data is not None else load_breeds_data()
    existing = {b.name for b in db.query(Breed).filter(Breed.tenant_id == tenant.id).all()}
    created = 0
    for entry in breeds_data:
        if entry["name"] in existing:
            continue
        breed = Breed(
            tenant_id=tenant.id,
            name=entry["name"],
            abbreviation=entry["abbr"],
            group=BreedGroup(entry["group"]),
            min_weight_kg=float(entry["min_kg"]) if entry["min_kg"] else None,
            ideal_weight_min_kg=float(entry["ideal_min_kg"]) if entry["ideal_min_kg"] else None,
            ideal_weight_max_kg=float(entry["ideal_max_kg"]) if entry["ideal_max_kg"] else None,
            max_weight_kg=float(entry["max_kg"]) if entry["max_kg"] else None,
        )
        breed.scoring_positions = [
            BreedScoringPosition(position_number=i + 1, label=p["label"], max_points=p["points"])
            for i, p in enumerate(entry["positions"])
        ]
        db.add(breed)
        created += 1
    return created, len(existing)


def run() -> None:
    breeds_data = load_breeds_data()

    db = SessionLocal()
    try:
        tenants = db.query(Tenant).all()
        if not tenants:
            print("Kein Zuchtbetrieb (Tenant) vorhanden -- zuerst `alembic upgrade head` ausführen.")
            return
        total_created = 0
        for tenant in tenants:
            created, existing_count = seed_tenant_breeds(db, tenant, breeds_data)
            total_created += created
            print(f"Zuchtbetrieb '{tenant.name}': {created} Rassen neu angelegt, {existing_count} bereits vorhanden.")
        db.commit()
        print(f"Seed abgeschlossen: {total_created} Rassen insgesamt neu angelegt.")
    finally:
        db.close()


if __name__ == "__main__":
    run()
