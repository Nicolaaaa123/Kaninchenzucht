import base64

from fastapi import APIRouter, Depends, HTTPException, UploadFile
from sqlalchemy.orm import Session

from app import models, schemas
from app.auth import get_current_user
from app.database import get_db
from app.services.matching import match_animal_by_identifier
from app.services.vision import VisionNotConfigured, extract_evaluation_card

router = APIRouter(prefix="/api/scan", tags=["scan"])

ALLOWED_TYPES = {
    "image/jpeg": "jpg",
    "image/png": "png",
    "image/webp": "webp",
    "image/heic": "heic",
}


@router.post("/evaluation-card", response_model=schemas.ScanResultOut)
async def scan_evaluation_card(
    file: UploadFile,
    db: Session = Depends(get_db),
    current_user: models.User = Depends(get_current_user),
):
    """Liest die Karte per Vision aus und gibt das Foto nur kurzzeitig als
    Data-URI zur Anzeige/Kontrolle zurück — es wird NICHT auf der Platte
    gespeichert, um Speicherplatz zu sparen. Nach dem Bestätigen ist nur noch
    die ausgelesene Bewertung (Zahlen/Text) dauerhaft gespeichert."""
    if file.content_type not in ALLOWED_TYPES:
        raise HTTPException(status_code=415, detail="Bitte ein Foto (JPEG, PNG, WEBP oder HEIC) hochladen")

    image_bytes = await file.read()
    if not image_bytes:
        raise HTTPException(status_code=400, detail="Leere Datei")

    try:
        extraction = extract_evaluation_card(image_bytes, file.content_type)
    except VisionNotConfigured as e:
        raise HTTPException(status_code=503, detail=str(e))

    photo_data_uri = f"data:{file.content_type};base64,{base64.standard_b64encode(image_bytes).decode('utf-8')}"

    matched, candidates = match_animal_by_identifier(db, extraction.identification_number, current_user.tenant_id)

    return schemas.ScanResultOut(
        photo_data_uri=photo_data_uri,
        exhibitor_number=extraction.exhibitor_number,
        exhibitor_name=extraction.exhibitor_name,
        exhibitor_address=extraction.exhibitor_address,
        show_name=extraction.show_name,
        breed_name=extraction.breed_name,
        identification_number=extraction.identification_number,
        sex=extraction.sex,
        weight_grams=extraction.weight_grams,
        scores=[schemas.ScannedScoreOut(**s.model_dump()) for s in extraction.scores],
        total_score=extraction.total_score,
        notes=extraction.notes,
        matched_animal=schemas.AnimalListItem.model_validate(matched) if matched else None,
        candidate_animals=[schemas.AnimalListItem.model_validate(a) for a in candidates],
    )
