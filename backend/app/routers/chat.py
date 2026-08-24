import json

import anthropic
from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.config import settings
from app.database import get_db
from app.services.chat_tools import TOOL_DEFS, execute_tool

router = APIRouter(prefix="/api/chat", tags=["chat"])

MODEL = "claude-sonnet-5"
MAX_TOOL_ITERATIONS = 5

SYSTEM_PROMPT = """Du bist der Zucht-Assistent einer Kaninchenzucht-App (Schweizer Standard \
2015, Rassekaninchen Schweiz). Du hilfst der Züchterin/dem Züchter bei Fragen zu ihrem \
Bestand und zu allgemeinen Zuchtfragen.

Für Fragen zu den eigenen Tieren (z.B. "welche Tiere haben eine schwache Fellbewertung", \
"zeig mir die Geschwister von Tier X", "welche Rassen habe ich hinterlegt") nutze die \
bereitgestellten Werkzeuge, um die Datenbank abzufragen — rate nichts, was du nachschlagen \
kannst. Für allgemeine Fragen zur Kaninchenzucht (Haltung, Genetik, Krankheiten usw.) kannst \
du direkt aus deinem Wissen antworten, ohne ein Werkzeug zu benutzen.

Antworte auf Deutsch, klar und knapp. Wenn eine Anfrage mehrdeutig ist (z.B. mehrere Tiere \
mit ähnlichem Namen), frag kurz nach oder nenne alle Treffer."""


@router.post("", response_model=schemas.ChatResponse)
def chat(
    payload: schemas.ChatRequest,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if not settings.anthropic_api_key:
        raise HTTPException(
            status_code=503,
            detail="ANTHROPIC_API_KEY ist nicht gesetzt. Bitte in backend/.env eintragen, um den Chat zu nutzen.",
        )

    client = anthropic.Anthropic(api_key=settings.anthropic_api_key)
    messages = list(payload.messages)

    try:
        response = None
        for _ in range(MAX_TOOL_ITERATIONS):
            response = client.messages.create(
                model=MODEL,
                max_tokens=4096,
                system=SYSTEM_PROMPT,
                tools=TOOL_DEFS,
                messages=messages,
            )
            messages.append({"role": "assistant", "content": [b.model_dump() for b in response.content]})

            if response.stop_reason != "tool_use":
                break

            tool_results = []
            for block in response.content:
                if block.type == "tool_use":
                    result = execute_tool(db, current_user.tenant_id, block.name, block.input)
                    tool_results.append(
                        {
                            "type": "tool_result",
                            "tool_use_id": block.id,
                            "content": json.dumps(result, ensure_ascii=False, default=str),
                        }
                    )
            messages.append({"role": "user", "content": tool_results})
    except anthropic.AuthenticationError:
        raise HTTPException(status_code=502, detail="Ungültiger Anthropic API-Key.")
    except anthropic.RateLimitError:
        raise HTTPException(status_code=429, detail="Anthropic-Anfragelimit erreicht, bitte kurz warten.")
    except anthropic.APIStatusError as e:
        raise HTTPException(status_code=502, detail=f"Anthropic-API-Fehler: {e.message}")
    except anthropic.APIConnectionError:
        raise HTTPException(status_code=502, detail="Verbindung zur Anthropic-API fehlgeschlagen.")

    return schemas.ChatResponse(messages=messages)
