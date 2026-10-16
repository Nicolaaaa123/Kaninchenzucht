import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user, require_admin
from app.database import get_db
from app.services import usage

router = APIRouter(prefix="/api/usage", tags=["usage"])


@router.get("/me", response_model=schemas.UsageStatusOut)
def my_usage(db: Session = Depends(get_db), user: models.User = Depends(get_current_user)):
    """Eigenes KI-Kontingent und Verbrauch im laufenden Monat."""
    return schemas.UsageStatusOut(
        month=usage.month_label(),
        scan_used=usage.used_this_month(db, user.id, usage.KIND_SCAN),
        scan_limit=user.scan_limit,
        chat_used=usage.used_this_month(db, user.id, usage.KIND_CHAT),
        chat_limit=user.chat_limit,
    )


@router.get("/overview", response_model=list[schemas.UserUsageOut])
def usage_overview(db: Session = Depends(get_db), admin: models.User = Depends(require_admin)):
    """Alle Logins mit Limits und Verbrauch (laufender Monat) -- nur für Administratoren."""
    rows = db.execute(
        select(
            models.UsageEvent.user_id,
            models.UsageEvent.kind,
            func.count(models.UsageEvent.id),
            func.coalesce(func.sum(models.UsageEvent.input_tokens), 0),
            func.coalesce(func.sum(models.UsageEvent.output_tokens), 0),
        )
        .where(models.UsageEvent.created_at >= usage.month_start())
        .group_by(models.UsageEvent.user_id, models.UsageEvent.kind)
    ).all()
    by_user: dict[uuid.UUID, dict] = {}
    for user_id, kind, count, tokens_in, tokens_out in rows:
        entry = by_user.setdefault(user_id, {"scan": 0, "chat": 0, "in": 0, "out": 0})
        entry[kind] = count
        entry["in"] += int(tokens_in)
        entry["out"] += int(tokens_out)

    users = db.execute(select(models.User).order_by(models.User.username)).scalars().all()
    return [
        schemas.UserUsageOut(
            user_id=u.id,
            username=u.username,
            display_name=u.display_name,
            is_admin=u.is_admin,
            scan_limit=u.scan_limit,
            chat_limit=u.chat_limit,
            scan_used=by_user.get(u.id, {}).get("scan", 0),
            chat_used=by_user.get(u.id, {}).get("chat", 0),
            input_tokens=by_user.get(u.id, {}).get("in", 0),
            output_tokens=by_user.get(u.id, {}).get("out", 0),
        )
        for u in users
    ]


@router.put("/users/{user_id}/limits", response_model=schemas.UserUsageOut)
def set_limits(
    user_id: uuid.UUID,
    payload: schemas.UsageLimitsUpdate,
    db: Session = Depends(get_db),
    admin: models.User = Depends(require_admin),
):
    """Legt fest, wie viele Scans / KI-Anfragen ein Login pro Monat hat.
    Leer (null) = unbegrenzt, 0 = nicht freigeschaltet."""
    user = db.get(models.User, user_id)
    if not user:
        raise HTTPException(status_code=404, detail="Login nicht gefunden")
    user.scan_limit = payload.scan_limit
    user.chat_limit = payload.chat_limit
    db.commit()
    return next(u for u in usage_overview(db, admin) if u.user_id == user_id)
