import uuid

from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy import select
from sqlalchemy.orm import Session, joinedload

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db

router = APIRouter(prefix="/api/animals/{animal_id}/evaluations", tags=["evaluations"])


def _get_animal_or_404(db: Session, animal_id: uuid.UUID, tenant_id: uuid.UUID) -> models.Animal:
    animal = db.execute(
        select(models.Animal).where(models.Animal.id == animal_id, models.Animal.tenant_id == tenant_id)
    ).scalar_one_or_none()
    if not animal:
        raise HTTPException(status_code=404, detail="Tier nicht gefunden")
    return animal


@router.get("", response_model=list[schemas.EvaluationOut])
def list_evaluations(
    animal_id: uuid.UUID, db: Session = Depends(get_db), current_user: models.User = Depends(get_current_user)
):
    _get_animal_or_404(db, animal_id, current_user.tenant_id)
    stmt = (
        select(models.Evaluation)
        .options(joinedload(models.Evaluation.scores))
        .where(models.Evaluation.animal_id == animal_id)
        .order_by(models.Evaluation.evaluated_on.desc())
    )
    return db.execute(stmt).unique().scalars().all()


@router.post("", response_model=schemas.EvaluationOut, status_code=201)
def add_evaluation(
    animal_id: uuid.UUID,
    payload: schemas.EvaluationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_animal_or_404(db, animal_id, current_user.tenant_id)
    data = payload.model_dump(exclude={"scores"})
    evaluation = models.Evaluation(animal_id=animal_id, confirmed=True, **data)
    evaluation.scores = [models.EvaluationScore(**s.model_dump()) for s in payload.scores]
    db.add(evaluation)

    # Ein auf der Karte notiertes Gewicht landet automatisch auch in der
    # Gewichtsliste, statt nur im Bewertungsdatensatz vergraben zu bleiben —
    # aber nur, wenn für dieses Datum noch kein Eintrag existiert.
    if payload.weight_grams:
        existing = db.execute(
            select(models.WeightEntry).where(
                models.WeightEntry.animal_id == animal_id,
                models.WeightEntry.measured_on == payload.evaluated_on,
            )
        ).scalar_one_or_none()
        if not existing:
            db.add(
                models.WeightEntry(
                    animal_id=animal_id,
                    measured_on=payload.evaluated_on,
                    weight_grams=payload.weight_grams,
                    notes="automatisch von Bewertungskarte übernommen",
                )
            )

    db.commit()
    db.refresh(evaluation)
    return evaluation


@router.patch("/{evaluation_id}", response_model=schemas.EvaluationOut)
def update_evaluation(
    animal_id: uuid.UUID,
    evaluation_id: uuid.UUID,
    payload: schemas.EvaluationCreate,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_animal_or_404(db, animal_id, current_user.tenant_id)
    evaluation = db.get(models.Evaluation, evaluation_id)
    if not evaluation or evaluation.animal_id != animal_id:
        raise HTTPException(status_code=404, detail="Bewertung nicht gefunden")

    data = payload.model_dump(exclude={"scores"})
    for key, value in data.items():
        setattr(evaluation, key, value)
    evaluation.scores = [models.EvaluationScore(**s.model_dump()) for s in payload.scores]

    db.commit()
    db.refresh(evaluation)
    return evaluation


@router.delete("/{evaluation_id}", status_code=204)
def delete_evaluation(
    animal_id: uuid.UUID,
    evaluation_id: uuid.UUID,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    _get_animal_or_404(db, animal_id, current_user.tenant_id)
    evaluation = db.get(models.Evaluation, evaluation_id)
    if not evaluation or evaluation.animal_id != animal_id:
        raise HTTPException(status_code=404, detail="Bewertung nicht gefunden")
    db.delete(evaluation)
    db.commit()
