import secrets
from datetime import datetime, timedelta, timezone

import bcrypt
from fastapi import Cookie, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.database import get_db

SESSION_COOKIE_NAME = "session_token"
SESSION_TTL_DAYS = 30


def hash_password(password: str) -> str:
    return bcrypt.hashpw(password.encode("utf-8"), bcrypt.gensalt()).decode("utf-8")


def verify_password(password: str, password_hash: str) -> bool:
    try:
        return bcrypt.checkpw(password.encode("utf-8"), password_hash.encode("utf-8"))
    except ValueError:
        return False


def generate_invite_code() -> str:
    """8 gut lesbare Grossbuchstaben/Ziffern (hex) — zum Weitergeben/Abtippen."""
    return secrets.token_hex(4).upper()


def create_session(db: Session, user: models.User) -> str:
    token = secrets.token_urlsafe(32)
    expires = datetime.now(timezone.utc) + timedelta(days=SESSION_TTL_DAYS)
    db.add(models.UserSession(token=token, user_id=user.id, expires_at=expires))
    db.commit()
    return token


def get_current_user(
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
) -> models.User:
    if not session_token:
        raise HTTPException(status_code=401, detail="Nicht angemeldet")
    user_session = db.get(models.UserSession, session_token)
    if not user_session or user_session.expires_at < datetime.now(timezone.utc):
        raise HTTPException(status_code=401, detail="Sitzung abgelaufen, bitte erneut anmelden")
    user = db.get(models.User, user_session.user_id)
    if not user:
        raise HTTPException(status_code=401, detail="Nicht angemeldet")
    return user


def require_admin(user: models.User = Depends(get_current_user)) -> models.User:
    if not user.is_admin:
        raise HTTPException(status_code=403, detail="Nur für Administratoren")
    return user


def get_username_taken(db: Session, username: str) -> bool:
    return db.execute(select(models.User).where(models.User.username == username)).scalar_one_or_none() is not None
