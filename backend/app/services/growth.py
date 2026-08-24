"""Wachstumskurven und Peak-Zeitfenster-Berechnung.

Ohne hinterlegte rassespezifische Stützpunkte wird eine generische
Gompertz-Wachstumskurve als Startpunkt verwendet — ein in der Tierzucht
gebräuchliches Modell für sigmoidales Wachstum:

    W(t) = A * exp(-B * exp(-k * t))

mit A = angenommenes Ausstellungs-/Idealgewicht (Mittel aus Ideal-Min/Max),
t = Alter in Wochen. B und k werden so bestimmt, dass die Kurve bei Geburt
(t=0) ein typisches Wurfgewicht (~55 g) und nach einer rassegruppenabhängigen
Reifezeit T95 rund 95% von A erreicht. Sobald für eine Rasse eigene
Stützpunkte hinterlegt sind, wird stattdessen linear zwischen diesen
interpoliert (und ausserhalb des Bereichs der letzte/erste Wert gehalten).
"""

import math
import statistics
from dataclasses import dataclass
from datetime import date, timedelta

from app import models

BIRTH_WEIGHT_GRAMS = 55.0

T95_WEEKS_BY_GROUP: dict[models.BreedGroup, float] = {
    models.BreedGroup.DWARF: 14,
    models.BreedGroup.SMALL: 18,
    models.BreedGroup.MEDIUM: 22,
    models.BreedGroup.LARGE: 30,
}
DEFAULT_T95_WEEKS = 22


# Zibben bleiben im Schnitt leichter als Rammler und legen vor allem in der
# Endphase (nahe der Asymptote der Gompertz-Kurve) weniger zu -- als
# Faustregel wird der Zielwert (Asymptote) der generischen Kurve bei Zibben
# etwas tiefer angesetzt. Gilt nur für die generische Kurve, nicht für
# manuell hinterlegte Stützpunkte (die sind explizit vom Betrieb erfasst).
SEX_ASYMPTOTE_FACTOR: dict[models.Sex, float] = {
    models.Sex.MALE: 1.0,
    models.Sex.FEMALE: 0.94,
    models.Sex.UNKNOWN: 1.0,
}


def _asymptote_grams(breed: models.Breed, sex: models.Sex | None = None) -> float | None:
    if breed.ideal_weight_min_kg and breed.ideal_weight_max_kg:
        base = (breed.ideal_weight_min_kg + breed.ideal_weight_max_kg) / 2 * 1000
    elif breed.max_weight_kg:
        base = breed.max_weight_kg * 1000
    else:
        return None
    return base * SEX_ASYMPTOTE_FACTOR.get(sex, 1.0)


def breed_target_weight_kg(breed: models.Breed, sex: models.Sex | None = None) -> float | None:
    """Öffentlicher Zugriff auf das (geschlechtsabhängige) Rasse-Endgewicht
    in kg -- z.B. als Referenzgrösse für die Fütterung während des
    Wachstums, unabhängig vom aktuellen Körpergewicht des Jungtiers."""
    grams = _asymptote_grams(breed, sex)
    return grams / 1000 if grams else None


def _gompertz_params(breed: models.Breed, sex: models.Sex | None = None) -> tuple[float, float, float] | None:
    a = _asymptote_grams(breed, sex)
    if not a or a <= BIRTH_WEIGHT_GRAMS:
        return None
    t95 = T95_WEEKS_BY_GROUP.get(breed.group, DEFAULT_T95_WEEKS) if breed.group else DEFAULT_T95_WEEKS
    b = math.log(a / BIRTH_WEIGHT_GRAMS)
    k = -math.log(-math.log(0.95) / b) / t95
    return a, b, k


def predict_weight_grams(breed: models.Breed, age_weeks: float, sex: models.Sex | None = None) -> float | None:
    age_weeks = max(age_weeks, 0)
    points = sorted(breed.growth_points, key=lambda p: p.age_weeks) if breed.growth_points else []
    if points:
        if age_weeks <= points[0].age_weeks:
            return float(points[0].weight_grams)
        if age_weeks >= points[-1].age_weeks:
            return float(points[-1].weight_grams)
        for p1, p2 in zip(points, points[1:]):
            if p1.age_weeks <= age_weeks <= p2.age_weeks:
                span = p2.age_weeks - p1.age_weeks
                if span == 0:
                    return float(p1.weight_grams)
                ratio = (age_weeks - p1.age_weeks) / span
                return p1.weight_grams + ratio * (p2.weight_grams - p1.weight_grams)

    params = _gompertz_params(breed, sex)
    if not params:
        return None
    a, b, k = params
    return a * math.exp(-b * math.exp(-k * age_weeks))


def sample_curve(
    breed: models.Breed, max_weeks: int = 32, step: int = 1, sex: models.Sex | None = None
) -> list[tuple[int, float]]:
    return [
        (w, round(predict_weight_grams(breed, w, sex) or 0, 1))
        for w in range(0, max_weeks + 1, step)
        if predict_weight_grams(breed, w, sex) is not None
    ]


@dataclass
class PeakWindow:
    start_weeks: float
    end_weeks: float | None  # None = weiterhin im Idealbereich (Kurve erreicht Max nicht innerhalb Horizont)
    start_date: date
    end_date: date | None


# Rammler halten die Ausstellungskondition erfahrungsgemäss länger als Zibben
# (langsamere, gleichmässigere Ausreifung) — als Faustregel wird die obere
# Idealgewichts-Grenze für die Peak-Berechnung bei Rammlern etwas grosszügiger
# angesetzt, wodurch sich das berechnete Zeitfenster entsprechend verlängert.
PEAK_IDEAL_MAX_TOLERANCE: dict[models.Sex, float] = {
    models.Sex.MALE: 1.08,
    models.Sex.FEMALE: 1.0,
    models.Sex.UNKNOWN: 1.0,
}


def peak_window(
    breed: models.Breed, birth_date: date | None, sex: models.Sex | None = None, horizon_weeks: int = 60
) -> PeakWindow | None:
    if birth_date is None or not breed.ideal_weight_min_kg or not breed.ideal_weight_max_kg:
        return None
    ideal_min = breed.ideal_weight_min_kg * 1000
    ideal_max = breed.ideal_weight_max_kg * 1000 * PEAK_IDEAL_MAX_TOLERANCE.get(sex, 1.0)

    start_weeks: float | None = None
    end_weeks: float | None = None
    # feine Schrittweite für eine brauchbare Datumsgenauigkeit
    step = 0.5
    w = 0.0
    while w <= horizon_weeks:
        weight = predict_weight_grams(breed, w, sex)
        if weight is not None:
            if start_weeks is None and weight >= ideal_min:
                start_weeks = w
            if start_weeks is not None and end_weeks is None and weight > ideal_max:
                end_weeks = w
                break
        w += step

    if start_weeks is None:
        return None

    start_date = birth_date + timedelta(weeks=start_weeks)
    end_date = birth_date + timedelta(weeks=end_weeks) if end_weeks is not None else None
    return PeakWindow(start_weeks=start_weeks, end_weeks=end_weeks, start_date=start_date, end_date=end_date)


@dataclass
class GrowthStatus:
    age_weeks: float | None
    predicted_weight_grams: float | None
    actual_weight_grams: int | None
    deviation_pct: float | None
    status: str | None  # "im_plan" | "voraus" | "hinterher"
    peak: PeakWindow | None
    target_date_in_peak_window: bool | None


def growth_status(
    breed: models.Breed | None,
    birth_date: date | None,
    latest_weight_grams: int | None,
    latest_weight_date: date | None,
    target_date: date | None,
    target_date_end: date | None = None,
    sex: models.Sex | None = None,
    today: date | None = None,
) -> GrowthStatus:
    today = today or date.today()
    if breed is None:
        return GrowthStatus(None, None, latest_weight_grams, None, None, None, None)

    age_weeks = None
    predicted = None
    deviation_pct = None
    status = None
    if birth_date and latest_weight_date:
        age_weeks = (latest_weight_date - birth_date).days / 7
        predicted = predict_weight_grams(breed, age_weeks, sex)
        if predicted and latest_weight_grams:
            deviation_pct = round((latest_weight_grams - predicted) / predicted * 100, 1)
            if deviation_pct > 8:
                status = "voraus"
            elif deviation_pct < -8:
                status = "hinterher"
            else:
                status = "im_plan"

    peak = peak_window(breed, birth_date, sex)
    target_in_window = None
    if target_date and peak:
        range_end = target_date_end or target_date
        target_in_window = peak.start_date <= target_date and (peak.end_date is None or range_end <= peak.end_date)

    return GrowthStatus(age_weeks, predicted, latest_weight_grams, deviation_pct, status, peak, target_in_window)


def growth_rate_estimate(
    breed: models.Breed,
    birth_date: date | None,
    weight_entries: list["models.WeightEntry"],
    sex: models.Sex | None = None,
) -> str | None:
    """Grobe Einschätzung, ob ein Tier schnell/mittel/langsam zunimmt, im
    Vergleich zur rassetypischen Kurve an den jeweiligen Messtagen. Passt sich
    automatisch an, sobald neue Gewichtseinträge dazukommen."""
    if not birth_date or len(weight_entries) < 2:
        return None
    ratios = []
    for entry in weight_entries:
        age_weeks = (entry.measured_on - birth_date).days / 7
        predicted = predict_weight_grams(breed, age_weeks, sex)
        if predicted and predicted > 0:
            ratios.append(entry.weight_grams / predicted)
    if not ratios:
        return None
    avg_ratio = statistics.mean(ratios)
    if avg_ratio > 1.08:
        return "schnell"
    if avg_ratio < 0.92:
        return "langsam"
    return "mittel"


def own_trend_line(
    weight_entries: list["models.WeightEntry"], birth_date: date | None, weeks_ahead: int = 8
) -> list[tuple[float, float]]:
    """Einfache lineare Extrapolation aus den letzten eigenen Gewichtseinträgen
    — für Tiere, die deutlich vom Rassestandard abweichen (z.B. zu schwer),
    damit eine eigene Trendlinie statt nur einzelner Punkte dargestellt werden
    kann. Kein biologisches Modell, nur eine kurzfristige Fortschreibung."""
    points = sorted(weight_entries, key=lambda e: e.measured_on)
    if len(points) < 2 or not birth_date:
        return []
    recent = points[-5:]
    xs = [(e.measured_on - birth_date).days / 7 for e in recent]
    ys = [float(e.weight_grams) for e in recent]
    n = len(xs)
    mean_x = sum(xs) / n
    mean_y = sum(ys) / n
    denom = sum((x - mean_x) ** 2 for x in xs)
    if denom == 0:
        return []
    slope = sum((x - mean_x) * (y - mean_y) for x, y in zip(xs, ys)) / denom
    intercept = mean_y - slope * mean_x

    last_x = xs[-1]
    return [
        (round(last_x + w, 1), round(max(intercept + slope * (last_x + w), 0), 1)) for w in range(0, weeks_ahead + 1)
    ]


FAMILY_TARGET_WINDOW_WEEKS = 3
FAMILY_TARGET_MIN_SAMPLES = 2
FAMILY_TARGET_DEVIATION_THRESHOLD = 0.10


def suggest_target_weight_grams(
    breed: models.Breed, sex: models.Sex | None, related_animals: list["models.Animal"]
) -> tuple[float | None, str, int]:
    """Schlägt ein Zielgewicht vor: Rassestandard, ausser Eltern/Geschwister
    (mit Gewichtseinträgen nahe am rassetypischen Peak-Alter) weichen im
    Schnitt deutlich (>10%) davon ab — dann wird stattdessen dieser
    Erfahrungswert vorgeschlagen. Gibt (Gewicht, Quelle, Anzahl Datenpunkte)
    zurück; Quelle ist 'breed' oder 'family'."""
    breed_default = _asymptote_grams(breed, sex)
    if not breed_default:
        return None, "breed", 0

    peak = peak_window(breed, date.today(), sex)
    target_weeks = peak.start_weeks if peak else None

    # Nur gleichgeschlechtliche Verwandte einbeziehen, da Rammler und Zibben
    # unterschiedlich schwer werden -- sonst würde der Erfahrungswert verzerrt.
    same_sex_relatives = [a for a in related_animals if not sex or a.sex == sex]

    samples: list[float] = []
    if target_weeks is not None:
        for animal in same_sex_relatives:
            if not animal.birth_date:
                continue
            for entry in animal.weight_entries:
                age_weeks = (entry.measured_on - animal.birth_date).days / 7
                if abs(age_weeks - target_weeks) <= FAMILY_TARGET_WINDOW_WEEKS:
                    samples.append(entry.weight_grams)

    if len(samples) >= FAMILY_TARGET_MIN_SAMPLES:
        family_avg = statistics.mean(samples)
        if abs(family_avg - breed_default) / breed_default > FAMILY_TARGET_DEVIATION_THRESHOLD:
            return round(family_avg), "family", len(samples)

    return round(breed_default), "breed", len(samples)


@dataclass
class DescendantGrowthPoint:
    age_weeks: int
    mean_grams: float
    min_grams: int
    max_grams: int
    sample_count: int


def descendants_growth_curve(descendants: list[models.Animal], bucket_weeks: int = 2) -> list[DescendantGrowthPoint]:
    """Aggregiert Gewichtseinträge aller Nachkommen nach Alters-Bucket (in Wochen)."""
    buckets: dict[int, list[int]] = {}
    for animal in descendants:
        if not animal.birth_date:
            continue
        for entry in animal.weight_entries:
            age_days = (entry.measured_on - animal.birth_date).days
            if age_days < 0:
                continue
            age_weeks = age_days / 7
            bucket = int(age_weeks // bucket_weeks) * bucket_weeks
            buckets.setdefault(bucket, []).append(entry.weight_grams)

    points = []
    for bucket in sorted(buckets):
        weights = buckets[bucket]
        points.append(
            DescendantGrowthPoint(
                age_weeks=bucket,
                mean_grams=round(statistics.mean(weights), 1),
                min_grams=min(weights),
                max_grams=max(weights),
                sample_count=len(weights),
            )
        )
    return points
