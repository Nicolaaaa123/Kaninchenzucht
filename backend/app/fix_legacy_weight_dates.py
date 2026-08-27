"""Einmalige Korrektur: die Gewichtseinträge aus dem Altbestand-Import
(import_legacy_animals.py) wurden faelschlicherweise auf das Geburtsdatum
statt auf 'eingegeben_am' datiert, wo ein Geburtsdatum bekannt war. Das
Gewicht wurde tatsaechlich am Eingabedatum erfasst (teils Monate/Jahre nach
der Geburt), nicht bei der Geburt selbst.

Liest DATABASE_URL aus backend/.env.production.

Ausfuehren (Vorschau, schreibt nichts):
    venv\\Scripts\\python.exe -m app.fix_legacy_weight_dates

Ausfuehren (schreibt wirklich):
    venv\\Scripts\\python.exe -m app.fix_legacy_weight_dates --commit
"""

import sys
from pathlib import Path

from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker

from app.import_legacy_animals import (
    RAW_VALUES,
    COLUMNS,
    TARGET_TENANT_NAME,
    parse_values,
    parse_date,
    parse_datetime,
)
from app.models import Animal, Tenant, WeightEntry


def main() -> None:
    commit = "--commit" in sys.argv

    env_path = Path(__file__).resolve().parents[1] / ".env.production"
    if not env_path.exists():
        print(f"FEHLER: {env_path} nicht gefunden.")
        sys.exit(1)
    db_url = None
    for line in env_path.read_text(encoding="utf-8").splitlines():
        if line.startswith("DATABASE_URL="):
            db_url = line[len("DATABASE_URL=") :].strip()
    if not db_url:
        print("FEHLER: DATABASE_URL nicht in .env.production gefunden.")
        sys.exit(1)
    if db_url.startswith("postgresql://"):
        db_url = "postgresql+psycopg://" + db_url[len("postgresql://") :]

    engine = create_engine(db_url, pool_pre_ping=True)
    Session = sessionmaker(bind=engine)
    db = Session()

    tenant = db.query(Tenant).filter(Tenant.name == TARGET_TENANT_NAME).one_or_none()
    if tenant is None:
        print(f"FEHLER: Kein Zuchtbetrieb mit Namen '{TARGET_TENANT_NAME}' gefunden.")
        sys.exit(1)

    # Exakt dieselbe Chip-Nummern-Zuordnung wie beim urspruenglichen Import
    # nachvollziehen (inkl. Duplikat-Suffixe), um die richtigen Tiere wiederzufinden.
    rows_raw = parse_values(RAW_VALUES)
    rows = [dict(zip(COLUMNS, r)) for r in rows_raw]

    seen_chip_counts: dict[str, int] = {}
    synthetic_counter = 0
    fixed = 0
    already_correct = 0
    not_found = 0

    for row in rows:
        # Zaehllogik muss ueber ALLE Zeilen laufen (wie im Original-Import),
        # sonst verschieben sich Duplikat-Suffixe/LEGACY-Nummern ab der ersten
        # Zeile ohne Gewicht.
        original_chip = row["chip_nummer"]
        if original_chip:
            count = seen_chip_counts.get(original_chip, 0) + 1
            seen_chip_counts[original_chip] = count
            final_chip = original_chip if count == 1 else f"{original_chip}-{count}"
        else:
            synthetic_counter += 1
            final_chip = f"LEGACY-{synthetic_counter:04d}"

        if not row["gewicht_gramm"]:
            continue

        birth_date = parse_date(row["geburtsdatum"])
        if not birth_date:
            continue  # measured_on war schon korrekt (eingegeben_am), nichts zu tun

        correct_date = parse_datetime(row["eingegeben_am"]).date()

        animal = (
            db.query(Animal)
            .filter(Animal.tenant_id == tenant.id, Animal.chip_number == final_chip)
            .one_or_none()
        )
        if animal is None and row["name"]:
            # Chip-Nummer wurde evtl. inzwischen von Hand durch die echte ersetzt
            # (Platzhalter LEGACY-xxxx) -- Rueckfall auf eindeutigen Namen.
            candidates = db.query(Animal).filter(Animal.tenant_id == tenant.id, Animal.name == row["name"]).all()
            if len(candidates) == 1:
                animal = candidates[0]
                print(f"(Chip-Nr. von '{final_chip}' vermutlich inzwischen auf '{animal.chip_number}' geaendert, per Name gefunden)")
        if animal is None:
            print(f"WARNUNG: Tier mit Chip-Nr. '{final_chip}' nicht gefunden.")
            not_found += 1
            continue

        # Gezielt den (noch falsch datierten) Eintrag vom Import treffen --
        # das Tier kann inzwischen zusaetzliche, echte Gewichtseintraege haben.
        candidates = (
            db.query(WeightEntry)
            .filter(
                WeightEntry.animal_id == animal.id,
                WeightEntry.weight_grams == int(row["gewicht_gramm"]),
                WeightEntry.measured_on == birth_date,
            )
            .all()
        )
        if len(candidates) != 1:
            print(
                f"WARNUNG: Gewichtseintrag fuer Tier '{final_chip}' nicht eindeutig "
                f"({len(candidates)} Treffer fuer {row['gewicht_gramm']}g am {birth_date})."
            )
            not_found += 1
            continue
        entry = candidates[0]

        if entry.measured_on == correct_date:
            already_correct += 1
            continue

        print(f"{final_chip}: {entry.measured_on} -> {correct_date} (Gewicht {entry.weight_grams}g)")
        entry.measured_on = correct_date
        fixed += 1

    print(f"\nKorrigiert: {fixed}, bereits korrekt: {already_correct}, nicht gefunden: {not_found}")

    if not commit:
        db.rollback()
        print("\nNUR VORSCHAU -- nichts wurde gespeichert. Mit --commit erneut ausfuehren, um wirklich zu speichern.")
        return

    db.commit()
    print("\nGespeichert.")


if __name__ == "__main__":
    main()
