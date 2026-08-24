"""Stammbaum und Inzuchtkoeffizient (Wright'sche Methode).

Der Inzuchtkoeffizient eines Tieres entspricht dem Verwandtschaftsgrad
(Kinship-Koeffizient) seiner beiden Eltern. Wir verwenden den klassischen
rekursiven "tabular method"-Algorithmus (Wright 1922 / Malécot), der auch bei
unvollständigen, unregelmässig tiefen Stammbäumen korrekt terminiert:

    f(x, x) = 0.5 * (1 + f(dam(x), sire(x)))
    f(x, y) = 0.5 * (f(dam(x), y) + f(sire(x), y))   für x != y
    f(x, y) = 0                                       falls x oder y unbekannt

Der Inzuchtkoeffizient eines (auch hypothetischen) Nachkommen zweier Eltern
A und B ist f(A, B).
"""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models


class PedigreeService:
    def __init__(self, db: Session):
        self.db = db
        self._cache: dict[uuid.UUID, models.Animal | None] = {}
        self._kinship_cache: dict[tuple[str, str], float] = {}

    def _get(self, animal_id: uuid.UUID | None) -> models.Animal | None:
        if animal_id is None:
            return None
        if animal_id not in self._cache:
            self._cache[animal_id] = self.db.get(models.Animal, animal_id)
        return self._cache[animal_id]

    def kinship(self, id1: uuid.UUID | None, id2: uuid.UUID | None) -> float:
        if id1 is None or id2 is None:
            return 0.0
        key = tuple(sorted([str(id1), str(id2)]))
        if key in self._kinship_cache:
            return self._kinship_cache[key]

        if id1 == id2:
            a = self._get(id1)
            if a is None:
                result = 0.0
            else:
                result = 0.5 * (1 + self.kinship(a.mother_id, a.father_id))
        else:
            # Expand whichever of the two has recorded parents. Always expanding
            # id1 (regardless of whether id1 or id2 actually has ancestry data)
            # would incorrectly collapse to 0 whenever id1 happens to be a
            # founder, even if id2 descends from id1 (e.g. full siblings whose
            # shared parents are themselves founders).
            a1 = self._get(id1)
            a2 = self._get(id2)
            if a1 is not None and (a1.mother_id or a1.father_id):
                result = 0.5 * (self.kinship(a1.mother_id, id2) + self.kinship(a1.father_id, id2))
            elif a2 is not None and (a2.mother_id or a2.father_id):
                result = 0.5 * (self.kinship(id1, a2.mother_id) + self.kinship(id1, a2.father_id))
            else:
                result = 0.0

        self._kinship_cache[key] = result
        return result

    def inbreeding_coefficient(self, mother_id: uuid.UUID | None, father_id: uuid.UUID | None) -> float:
        """Inzuchtkoeffizient eines (ggf. hypothetischen) Nachkommen der beiden Eltern."""
        return round(self.kinship(mother_id, father_id), 4)

    def animal_inbreeding(self, animal_id: uuid.UUID) -> float:
        a = self._get(animal_id)
        if a is None:
            return 0.0
        return self.inbreeding_coefficient(a.mother_id, a.father_id)

    def descendants(self, animal_id: uuid.UUID) -> list[models.Animal]:
        """Alle Nachkommen (rekursiv über alle Generationen) eines Tieres."""
        result: dict[uuid.UUID, models.Animal] = {}
        frontier = [animal_id]
        while frontier:
            children = (
                self.db.execute(
                    select(models.Animal).where(
                        (models.Animal.mother_id.in_(frontier)) | (models.Animal.father_id.in_(frontier))
                    )
                )
                .scalars()
                .all()
            )
            next_frontier = []
            for c in children:
                if c.id not in result:
                    result[c.id] = c
                    next_frontier.append(c.id)
            frontier = next_frontier
        return list(result.values())

    def build_tree(self, animal_id: uuid.UUID | None, generations: int) -> dict | None:
        a = self._get(animal_id)
        if a is None:
            return None
        node = {
            "id": str(a.id),
            "chip_number": a.chip_number,
            "name": a.name,
            "sex": a.sex.value,
            "breed_name": a.breed.name if a.breed else None,
            "inbreeding_coefficient": self.animal_inbreeding(a.id),
        }
        if generations > 1:
            node["mother"] = self.build_tree(a.mother_id, generations - 1)
            node["father"] = self.build_tree(a.father_id, generations - 1)
        else:
            node["mother"] = None
            node["father"] = None
        return node
