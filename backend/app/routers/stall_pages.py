import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/api/stall-pages", tags=["stall-pages"])


def _get_owned(db: Session, page_id: uuid.UUID, tenant_id: uuid.UUID) -> models.StallPage:
    page = db.execute(
        select(models.StallPage).where(models.StallPage.id == page_id, models.StallPage.tenant_id == tenant_id)
    ).scalar_one_or_none()
    if not page:
        raise HTTPException(status_code=404, detail="Seite nicht gefunden")
    return page


@router.get("", response_model=list[schemas.StallPageOut])
def list_stall_pages(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return (
        db.execute(
            select(models.StallPage)
            .where(models.StallPage.tenant_id == current_user.tenant_id)
            .order_by(models.StallPage.position)
        )
        .scalars()
        .all()
    )


@router.post("", response_model=schemas.StallPageOut, status_code=201)
def create_stall_page(
    payload: schemas.StallPageCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    page = models.StallPage(**payload.model_dump(), tenant_id=current_user.tenant_id)
    db.add(page)
    db.commit()
    db.refresh(page)
    return page


@router.patch("/{page_id}", response_model=schemas.StallPageOut)
def update_stall_page(
    page_id: uuid.UUID,
    payload: schemas.StallPageUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    page = _get_owned(db, page_id, current_user.tenant_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(page, key, value)
    db.commit()
    db.refresh(page)
    return page


@router.delete("/{page_id}", status_code=204)
def delete_stall_page(
    page_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    page = _get_owned(db, page_id, current_user.tenant_id)
    # Ställe auf dieser Seite bleiben erhalten, werden nur von der Seite gelöst
    for stall in db.execute(select(models.Stall).where(models.Stall.page_id == page_id)).scalars().all():
        stall.page_id = None
    db.delete(page)
    db.commit()
