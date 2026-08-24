"""Ordnet eine gelesene Chip-/Ohrmarken-Nummer einem Tier zu.

Wird sowohl vom Bewertungskarten-Scan als auch vom Bluetooth-Chip-Scanner
genutzt. Karten und mancher Leser liefern oft nur die letzten paar Stellen
der vollen Nummer — wir versuchen daher zuerst eine exakte Übereinstimmung
und fallen andernfalls auf einen Endstellen-Abgleich zurück: eindeutig ⇒
automatisch zugeordnet, mehrdeutig ⇒ als Auswahl-Kandidaten zurückgegeben
statt geraten.
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models

MIN_SUFFIX_LENGTH = 3


def match_animal_by_identifier(
    db: Session, identifier: str | None, tenant_id: uuid.UUID
) -> tuple[models.Animal | None, list[models.Animal]]:
    if not identifier:
        return None, []
    needle = identifier.strip().upper()
    if not needle:
        return None, []

    animals = db.execute(select(models.Animal).where(models.Animal.tenant_id == tenant_id)).scalars().all()

    exact = [
        a
        for a in animals
        if a.chip_number.strip().upper() == needle or (a.tattoo_number or "").strip().upper() == needle
    ]
    if len(exact) == 1:
        return exact[0], []
    if len(exact) > 1:
        return None, exact

    if len(needle) < MIN_SUFFIX_LENGTH:
        return None, []

    suffix_matches = [
        a
        for a in animals
        if a.chip_number.strip().upper().endswith(needle)
        or (a.tattoo_number or "").strip().upper().endswith(needle)
    ]
    if len(suffix_matches) == 1:
        return suffix_matches[0], []
    return None, suffix_matches
