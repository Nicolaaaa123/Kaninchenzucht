"""Namensgenerator für Jungtiere: junge Rammler bekommen denselben
Anfangsbuchstaben wie der Vater, junge Zibben denselben wie die Mutter — eine
in der Kaninchenzucht gebräuchliche Namenskonvention. Rammler bekommen dabei
ausschliesslich männliche, Zibben ausschliesslich weibliche Namen."""

import uuid

from sqlalchemy import select
from sqlalchemy.orm import Session

from app.models import Animal, Sex

NAME_POOL_MALE: dict[str, list[str]] = {
    "A": ["Anton", "Aslan", "Ares", "Athos", "Achilles"],
    "B": ["Balu", "Bruno", "Barney", "Basti"],
    "C": ["Charly", "Cosmo", "Carlo", "Chester", "Caspar"],
    "D": ["Django", "Dexter", "Dino", "Dax"],
    "E": ["Emil", "Elias", "Enzo", "Erik"],
    "F": ["Felix", "Finn", "Ferdi", "Franz"],
    "G": ["Gustav", "George", "Gizmo", "Gandalf"],
    "H": ["Hugo", "Henry", "Hoppel"],
    "I": ["Ivo", "Iggy", "Igor", "Ivar"],
    "J": ["Jack", "Jonas", "Jimmy", "Jerry"],
    "K": ["Karlo", "Kimba", "Kalle", "Kasimir"],
    "L": ["Leo", "Lasse", "Linus", "Louis"],
    "M": ["Max", "Milo", "Moritz", "Merlin"],
    "N": ["Nico", "Nero", "Nemo", "Noah"],
    "O": ["Otto", "Oskar", "Odin", "Ole"],
    "P": ["Paul", "Pepe", "Pino", "Piet"],
    "Q": ["Quentin", "Quinn"],
    "R": ["Rex", "Remo", "Rocky", "Ricco"],
    "S": ["Simba", "Sammy", "Struppi", "Sepp"],
    "T": ["Timo", "Theo", "Tapsi", "Titus"],
    "U": ["Uwe", "Ulf", "Urban"],
    "V": ["Vito", "Vincent", "Valentin"],
    "W": ["Willi", "Wolfi", "Wastl", "Waldo"],
    "X": ["Xaver", "Xander"],
    "Y": ["Yoshi", "Yuma"],
    "Z": ["Zorro", "Ziggy", "Zeus"],
}

NAME_POOL_FEMALE: dict[str, list[str]] = {
    "A": ["Amy", "Alma", "Amelie"],
    "B": ["Bella", "Bibi", "Bianca", "Bonnie"],
    "C": ["Chiara", "Cleo", "Coco"],
    "D": ["Diva", "Dana", "Delia", "Dodo"],
    "E": ["Elsa", "Emma", "Elke", "Ella"],
    "F": ["Frieda", "Fiona", "Flocke", "Fee"],
    "G": ["Greta", "Gina", "Gaia", "Gretel"],
    "H": ["Hanna", "Heidi", "Hazel", "Havanna", "Hexe"],
    "I": ["Ida", "Ines", "Iris", "Isolde"],
    "J": ["Julia", "Jule", "Josie", "Juna"],
    "K": ["Kira", "Klara", "Kim", "Kessy"],
    "L": ["Luna", "Lotte", "Lilly", "Lea"],
    "M": ["Mia", "Molly", "Mira", "Marla"],
    "N": ["Nala", "Nele", "Nina", "Nova"],
    "O": ["Oda", "Olina", "Olivia", "Ora"],
    "P": ["Pia", "Paula", "Pixie", "Pucki"],
    "Q": ["Quinta", "Quilla"],
    "R": ["Rosa", "Ronja", "Ruby", "Rike"],
    "S": ["Sina", "Susi", "Stella", "Sky"],
    "T": ["Tessa", "Tilda", "Tara", "Tina"],
    "U": ["Uma", "Ulli", "Una"],
    "V": ["Vera", "Vicky", "Vroni"],
    "W": ["Wanda", "Wolke", "Wendy", "Winnie", "Wickie"],
    "X": ["Xenia"],
    "Y": ["Yara", "Yvonne"],
    "Z": ["Zoe", "Zita", "Zilla"],
}


def _pool_for(sex: Sex | None) -> dict[str, list[str]]:
    if sex == Sex.FEMALE:
        return NAME_POOL_FEMALE
    if sex == Sex.MALE:
        return NAME_POOL_MALE
    # Ohne bekanntes Geschlecht beide Pools kombinieren, damit trotzdem ein
    # Vorschlag möglich ist.
    combined: dict[str, list[str]] = {}
    for key in set(NAME_POOL_MALE) | set(NAME_POOL_FEMALE):
        combined[key] = NAME_POOL_MALE.get(key, []) + NAME_POOL_FEMALE.get(key, [])
    return combined


def generate_names(
    db: Session,
    letter: str | None,
    count: int,
    tenant_id: uuid.UUID,
    sex: Sex | None = None,
    extra_exclude: set[str] | None = None,
) -> list[str | None]:
    """Liefert `count` Namensvorschläge, die mit `letter` beginnen, zum
    Geschlecht passen und noch nicht im Bestand vergeben sind. Ohne
    Buchstabe wird `None` je Tier zurückgegeben (Name bleibt leer, manuell
    nachtragbar). `extra_exclude` schliesst zusätzlich Namen aus, die noch
    nicht gespeichert sind (z.B. bereits im selben Wurf-Formular
    vorgeschlagene Namen)."""
    if count <= 0:
        return []
    if not letter:
        return [None] * count

    key = letter.strip().upper()[:1]
    pool = _pool_for(sex).get(key, [])
    if not pool:
        return [f"{key}-Tier {i + 1}" for i in range(count)]

    existing = {
        n
        for (n,) in db.execute(
            select(Animal.name).where(Animal.name.isnot(None), Animal.tenant_id == tenant_id)
        ).all()
    }
    existing |= extra_exclude or set()
    available = [n for n in pool if n not in existing]

    names: list[str | None] = []
    suffix = 2
    idx = 0
    while len(names) < count:
        if idx < len(available):
            names.append(available[idx])
            idx += 1
        else:
            base = pool[len(names) % len(pool)]
            candidate = f"{base} {suffix}"
            while candidate in existing or candidate in names:
                suffix += 1
                candidate = f"{base} {suffix}"
            names.append(candidate)
    return names
