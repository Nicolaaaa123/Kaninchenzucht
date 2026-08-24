import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/api/feeds", tags=["feeds"])


def _get_owned(db: Session, feed_id: uuid.UUID, tenant_id: uuid.UUID) -> models.Feed:
    feed = db.execute(
        select(models.Feed).where(models.Feed.id == feed_id, models.Feed.tenant_id == tenant_id)
    ).scalar_one_or_none()
    if not feed:
        raise HTTPException(status_code=404, detail="Futter nicht gefunden")
    return feed


@router.get("", response_model=list[schemas.FeedOut])
def list_feeds(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return (
        db.execute(select(models.Feed).where(models.Feed.tenant_id == current_user.tenant_id).order_by(models.Feed.name))
        .scalars()
        .all()
    )


@router.post("", response_model=schemas.FeedOut, status_code=201)
def create_feed(
    payload: schemas.FeedCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    feed = models.Feed(**payload.model_dump(), tenant_id=current_user.tenant_id)
    db.add(feed)
    db.commit()
    db.refresh(feed)
    return feed


@router.patch("/{feed_id}", response_model=schemas.FeedOut)
def update_feed(
    feed_id: uuid.UUID,
    payload: schemas.FeedUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    feed = _get_owned(db, feed_id, current_user.tenant_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(feed, key, value)
    db.commit()
    db.refresh(feed)
    return feed


@router.delete("/{feed_id}", status_code=204)
def delete_feed(
    feed_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    feed = _get_owned(db, feed_id, current_user.tenant_id)
    db.delete(feed)
    db.commit()
