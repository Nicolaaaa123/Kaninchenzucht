import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.services.feeding import calculate_feeding
from app.services.feeding_phase import detect_feeding_phase

router = APIRouter(prefix="/api/stalls", tags=["stalls"])


def _load_query():
    return select(models.Stall).options(
        joinedload(models.Stall.boxes).joinedload(models.CageBox.animals).joinedload(models.Animal.breed),
        joinedload(models.Stall.boxes).joinedload(models.CageBox.animals).joinedload(models.Animal.feed),
        joinedload(models.Stall.boxes).joinedload(models.CageBox.animals).joinedload(models.Animal.weight_entries),
    )


def _get_owned_stall(db: Session, stall_id: uuid.UUID, tenant_id: uuid.UUID, loaded: bool = False) -> models.Stall:
    stmt = (_load_query() if loaded else select(models.Stall)).where(
        models.Stall.id == stall_id, models.Stall.tenant_id == tenant_id
    )
    stall = db.execute(stmt).unique().scalar_one_or_none()
    if not stall:
        raise HTTPException(status_code=404, detail="Stall nicht gefunden")
    return stall


def _get_owned_box(db: Session, box_id: uuid.UUID, tenant_id: uuid.UUID) -> models.CageBox:
    box = db.execute(
        select(models.CageBox).join(models.Stall).where(models.CageBox.id == box_id, models.Stall.tenant_id == tenant_id)
    ).scalar_one_or_none()
    if not box:
        raise HTTPException(status_code=404, detail="Box nicht gefunden")
    return box


def _animal_list_item(db: Session, animal: models.Animal) -> schemas.AnimalListItem:
    latest_weight = animal.weight_entries[-1].weight_grams if animal.weight_entries else None
    item = schemas.AnimalListItem.model_validate(animal)
    item.latest_weight_grams = latest_weight
    if animal.feed:
        detected = detect_feeding_phase(db, animal)
        calc = calculate_feeding(
            latest_weight,
            detected.phase,
            animal.feed.energy_mj_per_kg,
            detected.target_weight_grams,
            detected.target_date,
            litter_size=detected.litter_size,
            is_late_gestation=detected.is_late_gestation,
            container_capacity_grams=animal.feed.container_capacity_grams,
        )
        item.daily_feed_grams = calc.daily_feed_grams if calc else None
        item.container_fill_pct = calc.container_fill_pct if calc else None
    return item


def _box_out(db: Session, box: models.CageBox) -> schemas.CageBoxOut:
    out = schemas.CageBoxOut.model_validate(box)
    out.occupants = [_animal_list_item(db, a) for a in box.animals if a.status == models.AnimalStatus.ACTIVE]
    return out


def _stall_out(db: Session, stall: models.Stall) -> schemas.StallOut:
    out = schemas.StallOut.model_validate(stall)
    out.boxes = [_box_out(db, b) for b in stall.boxes]
    return out


@router.get("", response_model=list[schemas.StallOut])
def list_stalls(
    page_id: uuid.UUID | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    stmt = _load_query().where(models.Stall.tenant_id == current_user.tenant_id)
    if page_id:
        stmt = stmt.where(models.Stall.page_id == page_id)
    stalls = db.execute(stmt.order_by(models.Stall.position)).unique().scalars().all()
    return [_stall_out(db, s) for s in stalls]


@router.post("", response_model=schemas.StallOut, status_code=201)
def create_stall(
    payload: schemas.StallCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if payload.rows < 1 or payload.columns < 1:
        raise HTTPException(status_code=422, detail="Reihen und Spalten müssen mindestens 1 sein")
    if payload.page_id:
        page = db.get(models.StallPage, payload.page_id)
        if not page or page.tenant_id != current_user.tenant_id:
            raise HTTPException(status_code=404, detail="Seite nicht gefunden")
    stall = models.Stall(
        tenant_id=current_user.tenant_id,
        label=payload.label,
        rows=payload.rows,
        columns=payload.columns,
        position=payload.position,
        page_id=payload.page_id,
    )
    boxes = []
    for r in range(payload.rows):
        for c in range(payload.columns):
            boxes.append(models.CageBox(row_index=r, col_index=c, label=f"{r + 1}.{c + 1}"))
    stall.boxes = boxes
    db.add(stall)
    db.commit()
    stall = db.execute(_load_query().where(models.Stall.id == stall.id)).unique().scalar_one()
    return _stall_out(db, stall)


@router.patch("/{stall_id}", response_model=schemas.StallOut)
def update_stall(
    stall_id: uuid.UUID,
    payload: schemas.StallUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    stall = _get_owned_stall(db, stall_id, current_user.tenant_id, loaded=True)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(stall, key, value)
    db.commit()
    db.refresh(stall)
    return _stall_out(db, stall)


@router.delete("/{stall_id}", status_code=204)
def delete_stall(
    stall_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    stall = _get_owned_stall(db, stall_id, current_user.tenant_id)
    try:
        db.delete(stall)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Stall kann nicht gelöscht werden, da er noch anderswo referenziert wird")


@router.post("/{stall_id}/add-row", response_model=schemas.StallOut)
def add_row(
    stall_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    stall = _get_owned_stall(db, stall_id, current_user.tenant_id)
    new_row = stall.rows
    for c in range(stall.columns):
        db.add(models.CageBox(stall_id=stall.id, row_index=new_row, col_index=c, label=f"{new_row + 1}.{c + 1}"))
    stall.rows += 1
    db.commit()
    stall = db.execute(_load_query().where(models.Stall.id == stall_id)).unique().scalar_one()
    return _stall_out(db, stall)


@router.post("/{stall_id}/add-column", response_model=schemas.StallOut)
def add_column(
    stall_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    stall = _get_owned_stall(db, stall_id, current_user.tenant_id)
    new_col = stall.columns
    for r in range(stall.rows):
        db.add(models.CageBox(stall_id=stall.id, row_index=r, col_index=new_col, label=f"{r + 1}.{new_col + 1}"))
    stall.columns += 1
    db.commit()
    stall = db.execute(_load_query().where(models.Stall.id == stall_id)).unique().scalar_one()
    return _stall_out(db, stall)


@router.patch("/boxes/{box_id}", response_model=schemas.CageBoxOut)
def update_box(
    box_id: uuid.UUID,
    payload: schemas.CageBoxUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    box = _get_owned_box(db, box_id, current_user.tenant_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(box, key, value)
    db.commit()
    db.refresh(box)
    return _box_out(db, box)


@router.delete("/boxes/{box_id}", status_code=204)
def delete_box(
    box_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    box = _get_owned_box(db, box_id, current_user.tenant_id)
    try:
        db.delete(box)
        db.commit()
    except IntegrityError:
        db.rollback()
        raise HTTPException(status_code=409, detail="Box kann nicht gelöscht werden, da sie noch anderswo referenziert wird")
