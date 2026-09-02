from fastapi import APIRouter, Depends
from sqlalchemy import func, select
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/api/dashboard", tags=["dashboard"])


@router.get("", response_model=schemas.DashboardOut)
def get_dashboard(db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)):
    tenant_id = current_user.tenant_id

    total_animals = db.execute(
        select(func.count(models.Animal.id)).where(
            models.Animal.status == models.AnimalStatus.ACTIVE, models.Animal.tenant_id == tenant_id
        )
    ).scalar_one()

    status_rows = db.execute(
        select(models.Animal.status, func.count(models.Animal.id))
        .where(models.Animal.tenant_id == tenant_id)
        .group_by(models.Animal.status)
    ).all()
    animals_by_status = {status.value: count for status, count in status_rows}

    category_rows = db.execute(
        select(models.Animal.category, func.count(models.Animal.id))
        .where(models.Animal.status == models.AnimalStatus.ACTIVE, models.Animal.tenant_id == tenant_id)
        .group_by(models.Animal.category)
    ).all()
    animals_by_category = {category.value: count for category, count in category_rows}

    breed_rows = db.execute(
        select(models.Breed.name, func.count(models.Animal.id))
        .join(models.Animal, models.Animal.breed_id == models.Breed.id)
        .where(models.Animal.tenant_id == tenant_id)
        .group_by(models.Breed.name)
        .order_by(models.Breed.name)
    ).all()
    animals_by_breed = [schemas.BreedCount(breed_name=name, count=count) for name, count in breed_rows]

    total_boxes = db.execute(
        select(func.count(models.CageBox.id)).join(models.Stall).where(models.Stall.tenant_id == tenant_id)
    ).scalar_one()
    total_capacity = db.execute(
        select(func.coalesce(func.sum(models.CageBox.capacity), 0))
        .join(models.Stall)
        .where(models.Stall.tenant_id == tenant_id)
    ).scalar_one()
    occupied = db.execute(
        select(func.count(models.Animal.id)).where(
            models.Animal.cage_box_id.is_not(None),
            models.Animal.status == models.AnimalStatus.ACTIVE,
            models.Animal.tenant_id == tenant_id,
        )
    ).scalar_one()
    free_box_capacity = max(total_capacity - occupied, 0)

    recent_weights = (
        db.execute(
            select(models.WeightEntry)
            .join(models.Animal)
            .where(models.Animal.tenant_id == tenant_id)
            .order_by(models.WeightEntry.created_at.desc())
            .limit(10)
        )
        .scalars()
        .all()
    )

    recent_evaluations = (
        db.execute(
            select(models.Evaluation)
            .join(models.Animal)
            .options(joinedload(models.Evaluation.scores))
            .where(models.Animal.tenant_id == tenant_id)
            .order_by(models.Evaluation.created_at.desc())
            .limit(10)
        )
        .unique()
        .scalars()
        .all()
    )

    return schemas.DashboardOut(
        total_animals=total_animals,
        animals_by_status=animals_by_status,
        animals_by_category=animals_by_category,
        animals_by_breed=animals_by_breed,
        total_boxes=total_boxes,
        free_box_capacity=free_box_capacity,
        recent_weight_entries=recent_weights,
        recent_evaluations=recent_evaluations,
    )
