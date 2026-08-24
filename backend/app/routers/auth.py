from fastapi import APIRouter, Cookie, Depends, HTTPException, Response
from sqlalchemy import delete, select, update
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import (
    SESSION_COOKIE_NAME,
    SESSION_TTL_DAYS,
    create_session,
    generate_invite_code,
    get_current_user,
    get_username_taken,
    hash_password,
    require_admin,
    verify_password,
)
from app.config import settings
from app.database import get_db

router = APIRouter(prefix="/api/auth", tags=["auth"])

# Tabellen, die direkt einem Zuchtbetrieb (Tenant) gehören — beim Zusammenschluss
# zweier Logins werden alle Zeilen des alten Tenants hierher umgehängt.
_TENANT_SCOPED_MODELS = (models.Breed, models.Stall, models.StallPage, models.Feed, models.Animal)


@router.post("/login", response_model=schemas.UserOut)
def login(payload: schemas.LoginRequest, response: Response, db: Session = Depends(get_db)):
    user = db.execute(select(models.User).where(models.User.username == payload.username)).scalar_one_or_none()
    if not user or not verify_password(payload.password, user.password_hash):
        raise HTTPException(status_code=401, detail="Benutzername oder Passwort falsch")
    token = create_session(db, user)
    response.set_cookie(
        SESSION_COOKIE_NAME,
        token,
        httponly=True,
        samesite="lax",
        secure=settings.secure_cookies,
        max_age=60 * 60 * 24 * SESSION_TTL_DAYS,
        path="/",
    )
    return user


@router.post("/logout")
def logout(
    response: Response,
    session_token: str | None = Cookie(default=None, alias=SESSION_COOKIE_NAME),
    db: Session = Depends(get_db),
):
    if session_token:
        db.execute(delete(models.UserSession).where(models.UserSession.token == session_token))
        db.commit()
    response.delete_cookie(SESSION_COOKIE_NAME, path="/")
    return {"ok": True}


@router.get("/me", response_model=schemas.UserOut)
def me(user: models.User = Depends(get_current_user)):
    return user


@router.post("/merge")
def merge_tenant(payload: schemas.MergeRequest, user: models.User = Depends(get_current_user), db: Session = Depends(get_db)):
    """Führt den Datenbestand des Logins mit diesem Code dauerhaft mit dem
    eigenen zusammen — ab sofort sehen und bearbeiten beide Logins dieselben
    Tiere, Ställe, Rassen, Futter und Würfe. Nicht umkehrbar."""
    code = payload.code.strip().upper()
    other = db.execute(select(models.User).where(models.User.invite_code == code)).scalar_one_or_none()
    if not other:
        raise HTTPException(status_code=404, detail="Kein Login mit diesem Code gefunden")
    if other.id == user.id:
        raise HTTPException(status_code=422, detail="Das ist dein eigener Code")
    if other.tenant_id == user.tenant_id:
        raise HTTPException(status_code=422, detail="Ihr seid bereits im selben Zuchtbetrieb")

    old_tenant_id = other.tenant_id
    new_tenant_id = user.tenant_id
    for model in _TENANT_SCOPED_MODELS:
        db.execute(update(model).where(model.tenant_id == old_tenant_id).values(tenant_id=new_tenant_id))
    db.execute(update(models.User).where(models.User.tenant_id == old_tenant_id).values(tenant_id=new_tenant_id))
    db.execute(delete(models.Tenant).where(models.Tenant.id == old_tenant_id))
    db.commit()
    return {"ok": True}


@router.post("/users", response_model=schemas.UserOut, status_code=201)
def create_user(payload: schemas.CreateUserRequest, admin: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    """Legt ein neues Login mit einem frischen, eigenen (leeren) Zuchtbetrieb
    an — nur für Administratoren. Der Zuchtbetrieb lässt sich danach über den
    Einlade-Code mit einem bestehenden zusammenführen."""
    username = payload.username.strip()
    if not username or not payload.password:
        raise HTTPException(status_code=422, detail="Benutzername und Passwort erforderlich")
    if get_username_taken(db, username):
        raise HTTPException(status_code=422, detail="Benutzername bereits vergeben")

    tenant = models.Tenant(name=payload.display_name or username)
    db.add(tenant)
    db.flush()

    user = models.User(
        username=username,
        password_hash=hash_password(payload.password),
        display_name=payload.display_name.strip() if payload.display_name else None,
        invite_code=generate_invite_code(),
        is_admin=payload.is_admin,
        tenant_id=tenant.id,
    )
    db.add(user)
    db.commit()
    db.refresh(user)
    return user


@router.get("/users", response_model=list[schemas.UserOut])
def list_users(admin: models.User = Depends(require_admin), db: Session = Depends(get_db)):
    return db.execute(select(models.User).order_by(models.User.username)).scalars().all()
