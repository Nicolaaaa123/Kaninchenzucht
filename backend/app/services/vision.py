"""Bewertungskarten-Scan: liest ein Foto einer (handschriftlichen) Bewertungskarte
per Claude Vision aus und liefert die erkannten Werte als Vorschlag zurück.

Wichtig: Die erkannten Werte werden NIE automatisch übernommen — sie kommen
immer nur als Vorschlag zurück, den die Zuchtperson im Frontend bestätigen
oder korrigieren muss, bevor irgendetwas gespeichert wird.
"""

import base64

import anthropic
from pydantic import BaseModel

from app.config import settings

MODEL = "claude-sonnet-5"


class ExtractedScore(BaseModel):
    category_label: str
    points: float | None = None


class EvaluationCardExtraction(BaseModel):
    exhibitor_number: str | None = None
    exhibitor_name: str | None = None
    exhibitor_address: str | None = None
    show_name: str | None = None
    breed_name: str | None = None
    identification_number: str | None = None  # Chip-Nummer oder Ohrmarke, wie auf der Karte vermerkt
    sex: str | None = None  # "male" | "female" | "unknown", nach bestem Ermessen
    weight_grams: int | None = None
    scores: list[ExtractedScore] = []
    total_score: float | None = None
    notes: str | None = None  # alles, was nicht in ein anderes Feld passt (z.B. Vermerke, unleserliche Stellen)


PROMPT = """Das ist ein Foto einer Bewertungskarte für eine Kaninchenausstellung \
(Standard Rassekaninchen Schweiz). Die Karte ist oft handschriftlich ausgefüllt.

Lies alle erkennbaren Felder aus:
- Ausstellernummer, Name und Adresse des Ausstellers
- Name der Ausstellung/Schau, falls vermerkt
- Rasse und Farbenschlag
- Chip-Nummer oder Ohrmarken-/Tätowierungsnummer des Tieres — auf Karten steht \
oft nur ein Teil davon (z.B. nur die letzten paar Ziffern), das ist normal: gib \
einfach genau das wieder, was auf der Karte steht, ohne die Nummer zu vervollständigen
- Geschlecht (Rammler/Häsin)
- Gewicht, falls notiert
- Die einzelnen Bewertungspositionen (z.B. "Kopf, Ohren, Hals", "Fell, Fellhaut und \
Grannenhaare" usw.) mit ihrer jeweiligen Punktzahl — in der Reihenfolge, wie sie auf \
der Karte stehen
- Die Gesamtpunktzahl

Wenn ein Feld nicht lesbar oder nicht vorhanden ist, lass es leer (null) — rate nichts. \
Handschrift ist nicht immer eindeutig; gib deine beste Einschätzung, aber erfinde keine \
Werte, die nicht erkennbar sind. Notiere unklare oder besondere Stellen im notes-Feld."""


class VisionNotConfigured(RuntimeError):
    pass


def extract_evaluation_card(image_bytes: bytes, media_type: str) -> EvaluationCardExtraction:
    if not settings.anthropic_api_key:
        raise VisionNotConfigured(
            "ANTHROPIC_API_KEY ist nicht gesetzt. Bitte in backend/.env eintragen, um den "
            "Bewertungskarten-Scan zu nutzen."
        )

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    image_data = base64.standard_b64encode(image_bytes).decode("utf-8")

    response = client.messages.parse(
        model=MODEL,
        max_tokens=4096,
        messages=[
            {
                "role": "user",
                "content": [
                    {
                        "type": "image",
                        "source": {"type": "base64", "media_type": media_type, "data": image_data},
                    },
                    {"type": "text", "text": PROMPT},
                ],
            }
        ],
        output_format=EvaluationCardExtraction,
    )
    return response.parsed_output
