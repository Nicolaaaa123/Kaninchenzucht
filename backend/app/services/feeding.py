"""Berechnung des täglichen Futterbedarfs.

Die Fütterungsphase wird automatisch erkannt (app.services.feeding_phase) --
diese Funktion nimmt nur noch die bereits aufgelöste Phase samt Zielwerten
entgegen und berechnet daraus die Menge:

- Wachstum / über Idealgewicht: die benötigte Menge ergibt sich aus der
  nötigen täglichen Zu-/Abnahme, um das Zielgewicht zum Zieldatum zu
  erreichen (Zielgewicht/-datum kommen aus der Peak-/Idealkurven-Berechnung
  der Rasse, sofern kein individuelles Zieldatum gesetzt ist). Ein Tier, das
  weit vor dem Zieldatum schon nah dran ist, bremst sich dadurch von selbst
  auf eine kleine Zu-/Abnahme herunter -- keine zusätzliche Sonderregel nötig.
- Trächtigkeit: pauschaler Aufschlag auf den Erhaltungsbedarf, in der
  letzten Tragzeit-Drittel höher als in den ersten zwei Dritteln.
- Säugezeit: pauschaler, wurfgrössenabhängiger Aufschlag (3.0-4.0x).
- Erhaltung: Grundbedarf beim aktuellen Gewicht.

Referenz-Erhaltungsbedarf: 50 g/Tag für ein 3 kg-Tier bei Standard-
Energiedichte (10.5 MJ/kg), allometrisch (Körpergewicht^0.75) skaliert.
Der letzte Schritt -- Umrechnung des Energiebedarfs in eine Futtermenge über
die tatsächliche Energiedichte des hinterlegten Futters -- war bereits
korrekt und bleibt unverändert:

Futtermenge (g/Tag) = Tagesenergiebedarf (MJ) / Energiegehalt des Futters (MJ/kg) * 1000
"""

from dataclasses import dataclass
from datetime import date

STANDARD_ENERGY_MJ_PER_KG = 10.5
REFERENCE_WEIGHT_KG = 3.0
REFERENCE_MAINTENANCE_GRAMS = 50.0

GROWTH_ENERGY_MJ_PER_KG_GAIN = 20.0  # Energieaufwand je kg Zu-/Abnahme
MIN_ADJUSTMENT_DAYS = 7  # Untergrenze für die Resttage, um Spitzen bei knappem/verpasstem Zieldatum zu vermeiden
MIN_ENERGY_FACTOR = 0.5  # Untergrenze relativ zum Erhaltungsbedarf, auch bei starker Diät
GROWTH_BOOST_FACTOR = 5 / 3  # Aufschlag auf die gesamte Futtermenge während der Wachstumsphase

GESTATION_EARLY_FACTOR = 1.1  # erste zwei Drittel der Trächtigkeit
GESTATION_LATE_FACTOR = 1.5  # letztes Drittel

LACTATION_FACTOR_MIN = 3.0
LACTATION_FACTOR_MAX = 4.0
LACTATION_LITTER_SIZE_MIN = 3  # ab hier voller Min-Faktor (kleiner Wurf)
LACTATION_LITTER_SIZE_MAX = 8  # ab hier voller Max-Faktor (grosser Wurf)
LACTATION_DEFAULT_FACTOR = 3.5  # falls Wurfgrösse nicht erfasst ist


@dataclass
class FeedingCalculation:
    daily_feed_grams: float
    daily_energy_mj: float
    reason: str
    target_weight_grams: float | None = None
    target_date: date | None = None
    days_remaining: int | None = None
    required_daily_gain_grams: float | None = None
    container_fill_pct: float | None = None


def _reference_maintenance_grams(weight_kg: float) -> float:
    """Erhaltungsbedarf (g/Tag) bei Standard-Energiedichte, allometrisch
    (Körpergewicht^0.75) auf den 3 kg-Referenzwert (50 g/Tag) skaliert."""
    if weight_kg <= 0:
        return 0.0
    return REFERENCE_MAINTENANCE_GRAMS * (weight_kg / REFERENCE_WEIGHT_KG) ** 0.75


def lactation_factor(litter_size: int | None) -> float:
    """Skaliert linear zwischen 3.0 (kleiner Wurf) und 4.0 (grosser Wurf).
    Ohne bekannte Wurfgrösse gilt der Standardfaktor 3.5."""
    if litter_size is None:
        return LACTATION_DEFAULT_FACTOR
    if litter_size <= LACTATION_LITTER_SIZE_MIN:
        return LACTATION_FACTOR_MIN
    if litter_size >= LACTATION_LITTER_SIZE_MAX:
        return LACTATION_FACTOR_MAX
    ratio = (litter_size - LACTATION_LITTER_SIZE_MIN) / (LACTATION_LITTER_SIZE_MAX - LACTATION_LITTER_SIZE_MIN)
    return LACTATION_FACTOR_MIN + ratio * (LACTATION_FACTOR_MAX - LACTATION_FACTOR_MIN)


def calculate_feeding(
    weight_grams: int | None,
    phase: str,
    feed_energy_mj_per_kg: float | None,
    target_weight_grams: float | None = None,
    target_date: date | None = None,
    today: date | None = None,
    litter_size: int | None = None,
    is_late_gestation: bool | None = None,
    container_capacity_grams: float | None = None,
) -> FeedingCalculation | None:
    if not weight_grams or weight_grams <= 0 or not feed_energy_mj_per_kg or feed_energy_mj_per_kg <= 0:
        return None

    weight_kg = weight_grams / 1000
    maintenance_me = _reference_maintenance_grams(weight_kg) / 1000 * STANDARD_ENERGY_MJ_PER_KG

    days_remaining = None
    required_daily_gain_grams = None

    if phase in ("growth", "over_ideal") and target_weight_grams and target_date:
        today = today or date.today()
        days_remaining = (target_date - today).days
        effective_days = max(days_remaining, MIN_ADJUSTMENT_DAYS)
        gain_grams = target_weight_grams - weight_grams
        required_daily_gain_grams = round(gain_grams / effective_days, 1)
        growth_me = (required_daily_gain_grams / 1000) * GROWTH_ENERGY_MJ_PER_KG_GAIN
        total_me = max(maintenance_me + growth_me, maintenance_me * MIN_ENERGY_FACTOR)
        if phase == "growth":
            total_me *= GROWTH_BOOST_FACTOR

        weekly = required_daily_gain_grams * 7
        if phase == "growth":
            reason = (
                f"Wachstumsphase, muss bis {target_date.isoformat()} noch {round(gain_grams)} g zunehmen "
                f"(ca. {abs(round(weekly))} g/Woche nötig)"
                if gain_grams > 0
                else "Wachstumsphase, Zielgewicht bereits erreicht"
            )
        else:
            reason = (
                f"über der Idealkurve, muss bis {target_date.isoformat()} {abs(round(gain_grams))} g abnehmen "
                f"(ca. {abs(round(weekly))} g/Woche)"
                if gain_grams < 0
                else "über der Idealkurve, Zielgewicht bereits erreicht"
            )
    elif phase == "growth":
        # Kein Zieldatum/-gewicht ermittelbar (z.B. Rasse ohne hinterlegte Idealwerte) --
        # einfacher Wachstums-Richtwert ohne Datumsbezug.
        total_me = maintenance_me * 2.0 * GROWTH_BOOST_FACTOR
        reason = "Wachstumsphase (kein Zieldatum ermittelbar, Richtwert)"
    elif phase == "over_ideal":
        total_me = maintenance_me * 0.8
        reason = "über der Idealkurve, reduzierte Menge (Diät)"
    elif phase == "gestation":
        factor = GESTATION_LATE_FACTOR if is_late_gestation else GESTATION_EARLY_FACTOR
        total_me = maintenance_me * factor
        reason = "Trächtig, letztes Drittel" if is_late_gestation else "Trächtig, erste zwei Drittel"
    elif phase == "lactation":
        factor = lactation_factor(litter_size)
        total_me = maintenance_me * factor
        reason = f"Säugend (Wurfgrösse {litter_size})" if litter_size is not None else "Säugend (Wurfgrösse unbekannt)"
    else:
        total_me = maintenance_me
        reason = "Erhaltung, Tier liegt auf der Idealkurve"

    grams = total_me / feed_energy_mj_per_kg * 1000
    container_fill_pct = round(grams / container_capacity_grams * 100, 1) if container_capacity_grams else None

    return FeedingCalculation(
        daily_feed_grams=round(grams, 1),
        daily_energy_mj=round(total_me, 3),
        reason=reason,
        target_weight_grams=target_weight_grams,
        target_date=target_date,
        days_remaining=days_remaining,
        required_daily_gain_grams=required_daily_gain_grams,
        container_fill_pct=container_fill_pct,
    )
