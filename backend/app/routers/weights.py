import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/api/animals/{animal_id}/weights", tags=["weights"])


def _get_animal_or_404(db: Session, animal_id: uuid.UUID, tenant_id: uuid.UUID) -> models.Animal:
    animal = db.execute(
        select(models.Animal).where(models.Animal.id == animal_id, models.Animal.tenant_id == tenant_id)
    ).scalar_one_or_none()
    if not animal:
        raise HTTPException(status_code=404, detail="Tier nicht gefunden")
    return animal


@router.get("", response_model=list[schemas.WeightEntryOut])
def list_weights(
    animal_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    _get_animal_or_404(db, animal_id, current_user.tenant_id)
    stmt = (
        select(models.WeightEntry)
        .where(models.WeightEntry.animal_id == animal_id)
        .order_by(models.WeightEntry.measured_on)
    )
    return db.execute(stmt).scalars().all()


@router.post("", response_model=schemas.WeightEntryOut, status_code=201)
def add_weight(
    animal_id: uuid.UUID,
    payload: schemas.WeightEntryCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    animal = _get_animal_or_404(db, animal_id, current_user.tenant_id)
    existing = db.execute(
        select(models.WeightEntry).where(
            models.WeightEntry.animal_id == animal_id,
            models.WeightEntry.measured_on == payload.measured_on,
        )
    ).scalar_one_or_none()
    if existing:
        raise HTTPException(status_code=409, detail="Für dieses Datum existiert bereits ein Eintrag")
    entry = models.WeightEntry(animal_id=animal_id, **payload.model_dump())
    db.add(entry)
    # Die Fütterungsphase wird bei jeder Abfrage automatisch frisch aus den
    # aktuellen Tierdaten erkannt (app.services.feeding_phase) -- kein
    # manuelles Umstellen des gespeicherten Status mehr nötig.
    db.commit()
    db.refresh(entry)
    return entry


@router.delete("/{entry_id}", status_code=204)
def delete_weight(
    animal_id: uuid.UUID,
    entry_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_animal_or_404(db, animal_id, current_user.tenant_id)
    entry = db.get(models.WeightEntry, entry_id)
    if not entry or entry.animal_id != animal_id:
        raise HTTPException(status_code=404, detail="Eintrag nicht gefunden")
    db.delete(entry)
    db.commit()
