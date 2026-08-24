"""Automatische Erkennung der Fütterungsphase eines Tiers -- Wachstum,
über Idealgewicht, Trächtigkeit, Säugezeit oder Erhaltung -- rein aus den
vorhandenen Tierdaten. Keine manuelle Auswahl nötig; Trächtigkeit und
Säugezeit sind bei Rammlern kategorisch ausgeschlossen."""

from dataclasses import dataclass
from datetime import date, timedelta

from sqlalchemy import select
from sqlalchemy.orm import Session

from app import models
from app.services.growth import (
    DEFAULT_T95_WEEKS,
    T95_WEEKS_BY_GROUP,
    breed_target_weight_kg,
    growth_status,
    peak_window,
    predict_weight_grams,
)

GROWTH_ASYMPTOTE_THRESHOLD = 0.95  # Anteil des Rasse-Endgewichts, ab dem "ausgewachsen"
MAX_GROWTH_AGE_MULTIPLIER = 1.75  # Vielfaches der typischen Reifezeit T95 -- danach nicht mehr "im Wachstum"
GROWTH_FALLBACK_HORIZON_DAYS = 84  # Zeitrahmen, wenn kein Zieldatum/Peak-Fenster berechenbar ist (12 Wochen)

DEFAULT_GESTATION_DAYS = 31  # rassenübergreifend bei Kaninchen recht einheitlich
GESTATION_END_BUFFER_DAYS = 5  # Nachlauf, falls der genaue Wurftermin abweicht
DEFAULT_LACTATION_WEEKS = 8

PHASE_GROWTH = "growth"
PHASE_OVER_IDEAL = "over_ideal"
PHASE_GESTATION = "gestation"
PHASE_LACTATION = "lactation"
PHASE_MAINTENANCE = "maintenance"


@dataclass
class FeedingPhase:
    phase: str
    target_weight_grams: float | None = None
    target_date: date | None = None
    litter_size: int | None = None
    gestation_week: int | None = None
    is_late_gestation: bool = False
    lactation_week: int | None = None
    error: str | None = None


def _current_litter(db: Session, animal: models.Animal) -> tuple[date, int] | None:
    dates = db.execute(
        select(models.Animal.birth_date).where(models.Animal.mother_id == animal.id)
    ).scalars().all()
    dates = [d for d in dates if d]
    if not dates:
        return None
    latest = max(dates)
    return latest, sum(1 for d in dates if d == latest)


def detect_feeding_phase(db: Session, animal: models.Animal, today: date | None = None) -> FeedingPhase:
    today = today or date.today()
    breed = animal.breed

    error = None
    if animal.sex == models.Sex.MALE and animal.feeding_stage in (
        models.FeedingStage.GESTATION,
        models.FeedingStage.LACTATION,
    ):
        error = (
            "Für dieses Tier ist manuell 'Trächtigkeit'/'Säugezeit' hinterlegt, obwohl es als Rammler "
            "markiert ist — dieser (fehlerhafte) Altwert wird für die Futterberechnung ignoriert."
        )

    if animal.sex == models.Sex.FEMALE:
        # Säugezeit: jüngster Wurf noch innerhalb der (rassespezifischen) Säugezeit-Dauer
        litter = _current_litter(db, animal)
        if litter:
            litter_date, litter_size = litter
            lactation_weeks = (breed.lactation_weeks if breed and breed.lactation_weeks else DEFAULT_LACTATION_WEEKS)
            weeks_since = (today - litter_date).days / 7
            if 0 <= weeks_since <= lactation_weeks:
                return FeedingPhase(
                    phase=PHASE_LACTATION,
                    litter_size=litter_size,
                    lactation_week=int(weeks_since) + 1,
                    error=error,
                )

        # Trächtigkeit: Deckdatum + Rasse-Tragzeit, nur falls seither kein (neuerer) Wurf da ist
        if animal.mating_date:
            gestation_days = breed.gestation_days if breed and breed.gestation_days else DEFAULT_GESTATION_DAYS
            days_since_mating = (today - animal.mating_date).days
            has_delivered = litter is not None and litter[0] >= animal.mating_date
            if not has_delivered and 0 <= days_since_mating <= gestation_days + GESTATION_END_BUFFER_DAYS:
                return FeedingPhase(
                    phase=PHASE_GESTATION,
                    gestation_week=days_since_mating // 7 + 1,
                    is_late_gestation=days_since_mating >= gestation_days * 2 / 3,
                    error=error,
                )

    latest_entry = animal.weight_entries[-1] if animal.weight_entries else None
    if not breed or not latest_entry:
        return FeedingPhase(phase=PHASE_MAINTENANCE, error=error)

    weight_kg = latest_entry.weight_grams / 1000
    target_kg = breed_target_weight_kg(breed, animal.sex)
    age_weeks = (latest_entry.measured_on - animal.birth_date).days / 7 if animal.birth_date else None

    still_growing = False
    if target_kg and weight_kg < target_kg * GROWTH_ASYMPTOTE_THRESHOLD:
        if age_weeks is None:
            still_growing = True
        else:
            t95 = T95_WEEKS_BY_GROUP.get(breed.group, DEFAULT_T95_WEEKS) if breed.group else DEFAULT_T95_WEEKS
            still_growing = age_weeks <= t95 * MAX_GROWTH_AGE_MULTIPLIER

    if still_growing:
        target_date = animal.target_date
        if not target_date and animal.birth_date:
            peak = peak_window(breed, animal.birth_date, animal.sex)
            target_date = peak.start_date if peak else None
        target_weight = None
        if target_date and animal.birth_date:
            target_age_weeks = (target_date - animal.birth_date).days / 7
            target_weight = predict_weight_grams(breed, target_age_weeks, animal.sex)
        if target_weight is None and target_kg:
            # Auch ohne individuelles Zieldatum und ohne berechenbares
            # Peak-Fenster (z.B. fehlendes Geburtsdatum, oder Rasse nur mit
            # Maximalgewicht statt Ideal-Spanne hinterlegt) trotzdem anhand
            # der Rassekurve rechnen, statt auf einen pauschalen Richtwert
            # ohne Rassebezug zurückzufallen.
            target_weight = target_kg * 1000
            if not target_date:
                target_date = today + timedelta(days=GROWTH_FALLBACK_HORIZON_DAYS)
        return FeedingPhase(phase=PHASE_GROWTH, target_weight_grams=target_weight, target_date=target_date, error=error)

    status = growth_status(
        breed=breed,
        birth_date=animal.birth_date,
        latest_weight_grams=latest_entry.weight_grams,
        latest_weight_date=latest_entry.measured_on,
        target_date=None,
        sex=animal.sex,
        today=today,
    )
    if status.status == "voraus":
        target_date = animal.target_date
        if not target_date:
            target_date = today + timedelta(days=56)  # sanfte, mehrwöchige Korrektur
        target_weight = animal.target_weight_grams or (target_kg * 1000 if target_kg else None)
        return FeedingPhase(phase=PHASE_OVER_IDEAL, target_weight_grams=target_weight, target_date=target_date, error=error)

    return FeedingPhase(phase=PHASE_MAINTENANCE, error=error)
