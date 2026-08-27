import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.services.growth import descendants_growth_curve, sample_curve

router = APIRouter(prefix="/api/breeds", tags=["breeds"])


def _load_query():
    return select(models.Breed).options(
        joinedload(models.Breed.scoring_positions), joinedload(models.Breed.growth_points)
    )


def _get_owned(db: Session, breed_id: uuid.UUID, tenant_id: uuid.UUID, loaded: bool = False) -> models.Breed:
    stmt = (_load_query() if loaded else select(models.Breed)).where(
        models.Breed.id == breed_id, models.Breed.tenant_id == tenant_id
    )
    breed = db.execute(stmt).unique().scalar_one_or_none()
    if not breed:
        raise HTTPException(status_code=404, detail="Rasse nicht gefunden")
    return breed


@router.get("", response_model=list[schemas.BreedOut])
def list_breeds(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    return (
        db.execute(_load_query().where(models.Breed.tenant_id == current_user.tenant_id).order_by(models.Breed.name))
        .unique()
        .scalars()
        .all()
    )


@router.post("", response_model=schemas.BreedOut, status_code=201)
def create_breed(
    payload: schemas.BreedCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    if db.execute(
        select(models.Breed).where(models.Breed.name == payload.name, models.Breed.tenant_id == current_user.tenant_id)
    ).scalar_one_or_none():
        raise HTTPException(status_code=409, detail="Rasse existiert bereits")
    data = payload.model_dump(exclude={"scoring_positions"})
    breed = models.Breed(**data, tenant_id=current_user.tenant_id)
    breed.scoring_positions = [
        models.BreedScoringPosition(**p.model_dump()) for p in payload.scoring_positions
    ]
    db.add(breed)
    db.commit()
    db.refresh(breed)
    return breed


@router.get("/{breed_id}", response_model=schemas.BreedOut)
def get_breed(
    breed_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    return _get_owned(db, breed_id, current_user.tenant_id, loaded=True)


@router.patch("/{breed_id}", response_model=schemas.BreedOut)
def update_breed(
    breed_id: uuid.UUID,
    payload: schemas.BreedUpdate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    breed = _get_owned(db, breed_id, current_user.tenant_id)
    for key, value in payload.model_dump(exclude_unset=True).items():
        setattr(breed, key, value)
    db.commit()
    db.refresh(breed)
    return breed


@router.put("/{breed_id}/scoring-positions", response_model=schemas.BreedOut)
def replace_scoring_positions(
    breed_id: uuid.UUID,
    positions: list[schemas.BreedScoringPositionCreate],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    breed = _get_owned(db, breed_id, current_user.tenant_id)
    breed.scoring_positions = [models.BreedScoringPosition(**p.model_dump()) for p in positions]
    db.commit()
    db.refresh(breed)
    return breed


@router.get("/{breed_id}/growth-curve", response_model=schemas.GrowthCurveOut)
def get_growth_curve(
    breed_id: uuid.UUID,
    sex: models.Sex | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    breed = _get_owned(db, breed_id, current_user.tenant_id, loaded=True)
    curve = sample_curve(breed, sex=sex)
    return schemas.GrowthCurveOut(
        breed_id=breed.id,
        source="custom" if breed.growth_points else "predicted",
        custom_points=breed.growth_points,
        curve=[schemas.GrowthCurvePointOut(age_weeks=w, weight_grams=g) for w, g in curve],
    )


@router.get("/{breed_id}/growth-curve-actual", response_model=schemas.BreedGrowthCurveActualOut)
def get_growth_curve_actual(
    breed_id: uuid.UUID,
    color_variant: str | None = None,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Tatsächliche Durchschnittsgewichtskurve aus allen erfassten
    Gewichtseinträgen aller Tiere dieser Rasse (optional zusätzlich auf einen
    Farbenschlag eingegrenzt) — im Unterschied zur theoretischen Gompertz-/
    Stützpunkt-Kurve unter /growth-curve."""
    _get_owned(db, breed_id, current_user.tenant_id)
    conditions = [models.Animal.breed_id == breed_id, models.Animal.tenant_id == current_user.tenant_id]
    if color_variant:
        conditions.append(models.Animal.color_variant == color_variant)
    animals = (
        db.execute(select(models.Animal).options(joinedload(models.Animal.weight_entries)).where(*conditions))
        .unique()
        .scalars()
        .all()
    )
    points = descendants_growth_curve(animals)
    return schemas.BreedGrowthCurveActualOut(
        breed_id=breed_id,
        animal_count=len(animals),
        points=[schemas.DescendantGrowthPointOut(**vars(p)) for p in points],
    )


@router.put("/{breed_id}/growth-curve", response_model=schemas.GrowthCurveOut)
def replace_growth_curve(
    breed_id: uuid.UUID,
    points: list[schemas.BreedGrowthPointCreate],
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    breed = _get_owned(db, breed_id, current_user.tenant_id, loaded=True)
    breed.growth_points = [models.BreedGrowthPoint(**p.model_dump()) for p in points]
    db.commit()
    breed = _get_owned(db, breed_id, current_user.tenant_id, loaded=True)
    curve = sample_curve(breed)
    return schemas.GrowthCurveOut(
        breed_id=breed.id,
        source="custom" if breed.growth_points else "predicted",
        custom_points=breed.growth_points,
        curve=[schemas.GrowthCurvePointOut(age_weeks=w, weight_grams=g) for w, g in curve],
    )


@router.delete("/{breed_id}", status_code=204)
def delete_breed(
    breed_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    breed = _get_owned(db, breed_id, current_user.tenant_id)
    db.delete(breed)
    db.commit()
