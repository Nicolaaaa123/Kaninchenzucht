"""Monatskontingent für die kostenpflichtigen KI-Funktionen (Foto-Scan, Chat).

Jedes Login hat optional ein Limit pro Kalendermonat (UTC): `scan_limit` für
Bewertungskarten-Scans, `chat_limit` für Chat-Anfragen. NULL = unbegrenzt,
0 = nicht freigeschaltet. Verbrauch wird in `usage_events` mitgeschrieben
(inkl. Tokens, damit sich die Kosten abschätzen lassen).
"""

from datetime import datetime, timezone

from fastapi import HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models

KIND_SCAN = "scan"
KIND_CHAT = "chat"
KIND_LABELS = {KIND_SCAN: "Scans", KIND_CHAT: "KI-Anfragen"}


def month_start(now: datetime | None = None) -> datetime:
    now = now or datetime.now(timezone.utc)
    return now.replace(day=1, hour=0, minute=0, second=0, microsecond=0)


def limit_for(user: models.User, kind: str) -> int | None:
    return user.scan_limit if kind == KIND_SCAN else user.chat_limit


def used_this_month(db: Session, user_id, kind: str) -> int:
    return db.execute(
        select(func.count(models.UsageEvent.id)).where(
            models.UsageEvent.user_id == user_id,
            models.UsageEvent.kind == kind,
            models.UsageEvent.created_at >= month_start(),
        )
    ).scalar_one()


def check_quota(db: Session, user: models.User, kind: str) -> None:
    """Bricht mit einer verständlichen Meldung ab, wenn das Kontingent fehlt/aufgebraucht ist."""
    limit = limit_for(user, kind)
    if limit is None:
        return
    label = KIND_LABELS[kind]
    if limit <= 0:
        raise HTTPException(
            status_code=403,
            detail=f"{label} sind für dein Login nicht freigeschaltet. Bitte beim Administrator nachfragen.",
        )
    used = used_this_month(db, user.id, kind)
    if used >= limit:
        raise HTTPException(
            status_code=429,
            detail=(
                f"Dein Kontingent für {label} in diesem Monat ist aufgebraucht ({used} von {limit}). "
                "Es füllt sich zum Monatsbeginn wieder auf, oder frag den Administrator nach mehr."
            ),
        )


def record_usage(db: Session, user: models.User, kind: str, input_tokens: int = 0, output_tokens: int = 0) -> None:
    db.add(
        models.UsageEvent(
            user_id=user.id,
            kind=kind,
            input_tokens=input_tokens or 0,
            output_tokens=output_tokens or 0,
        )
    )
    db.commit()


def month_label() -> str:
    return month_start().strftime("%Y-%m")
