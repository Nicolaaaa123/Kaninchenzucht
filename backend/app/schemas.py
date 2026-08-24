import uuid
from datetime import date, datetime

from pydantic import BaseModel, ConfigDict

from app.models import AnimalStatus, BreedGroup, BreedingCategory, FeedingStage, Sex


# ---- Auth ----
class LoginRequest(BaseModel):
    username: str
    password: str


class UserOut(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    username: str
    display_name: str | None
    is_admin: bool
    invite_code: str
    tenant_id: uuid.UUID


class CreateUserRequest(BaseModel):
    username: str
    password: str
    display_name: str | None = None
    is_admin: bool = False


class MergeRequest(BaseModel):
    code: str


# ---- Breed scoring positions ----
class BreedScoringPositionBase(BaseModel):
    position_number: int
    label: str
    max_points: int


class BreedScoringPositionCreate(BreedScoringPositionBase):
    pass


class BreedScoringPositionOut(BreedScoringPositionBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


# ---- Breed growth curve ----
class BreedGrowthPointBase(BaseModel):
    age_weeks: int
    weight_grams: int


class BreedGrowthPointCreate(BreedGrowthPointBase):
    pass


class BreedGrowthPointOut(BreedGrowthPointBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class GrowthCurvePointOut(BaseModel):
    age_weeks: float
    weight_grams: float


class GrowthCurveOut(BaseModel):
    breed_id: uuid.UUID
    source: str  # "custom" | "predicted"
    custom_points: list[BreedGrowthPointOut]
    curve: list[GrowthCurvePointOut]


# ---- Breed ----
class BreedBase(BaseModel):
    name: str
    abbreviation: str | None = None
    group: BreedGroup | None = None
    min_weight_kg: float | None = None
    ideal_weight_min_kg: float | None = None
    ideal_weight_max_kg: float | None = None
    max_weight_kg: float | None = None
    gestation_days: int | None = None
    lactation_weeks: int | None = None
    notes: str | None = None


class BreedCreate(BreedBase):
    scoring_positions: list[BreedScoringPositionCreate] = []


class BreedUpdate(BaseModel):
    name: str | None = None
    abbreviation: str | None = None
    group: BreedGroup | None = None
    min_weight_kg: float | None = None
    ideal_weight_min_kg: float | None = None
    ideal_weight_max_kg: float | None = None
    max_weight_kg: float | None = None
    gestation_days: int | None = None
    lactation_weeks: int | None = None
    notes: str | None = None


class BreedOut(BreedBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    scoring_positions: list[BreedScoringPositionOut] = []


class BreedSummary(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    name: str
    abbreviation: str | None = None
    group: BreedGroup | None = None


# ---- Feed ----
class FeedBase(BaseModel):
    name: str
    manufacturer: str | None = None
    energy_mj_per_kg: float
    crude_protein_pct: float | None = None
    crude_fiber_pct: float | None = None
    crude_fat_pct: float | None = None
    container_capacity_grams: float | None = None
    notes: str | None = None


class FeedCreate(FeedBase):
    pass


class FeedUpdate(BaseModel):
    name: str | None = None
    manufacturer: str | None = None
    energy_mj_per_kg: float | None = None
    crude_protein_pct: float | None = None
    crude_fiber_pct: float | None = None
    crude_fat_pct: float | None = None
    container_capacity_grams: float | None = None
    notes: str | None = None


class FeedOut(FeedBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime


# ---- StallPage ----
class StallPageBase(BaseModel):
    label: str
    position: int = 0


class StallPageCreate(StallPageBase):
    pass


class StallPageUpdate(BaseModel):
    label: str | None = None
    position: int | None = None


class StallPageOut(StallPageBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime


# ---- StallRow / CageBox ----
class CageBoxBase(BaseModel):
    label: str
    row_index: int = 0
    col_index: int = 0
    capacity: int = 1
    notes: str | None = None


class CageBoxCreate(CageBoxBase):
    pass


class CageBoxUpdate(BaseModel):
    label: str | None = None
    row_index: int | None = None
    col_index: int | None = None
    capacity: int | None = None
    notes: str | None = None


class CageBoxOut(CageBoxBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    stall_id: uuid.UUID
    occupants: list["AnimalListItem"] = []


class StallBase(BaseModel):
    label: str
    rows: int = 1
    columns: int = 1
    position: int = 0
    page_id: uuid.UUID | None = None
    notes: str | None = None


class StallCreate(StallBase):
    pass


class StallUpdate(BaseModel):
    label: str | None = None
    position: int | None = None
    page_id: uuid.UUID | None = None
    notes: str | None = None


class StallOut(StallBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    boxes: list[CageBoxOut] = []


# ---- Animal ----
class AnimalBase(BaseModel):
    chip_number: str
    tattoo_number: str | None = None
    name: str | None = None
    sex: Sex = Sex.UNKNOWN
    birth_date: date | None = None
    status: AnimalStatus = AnimalStatus.ACTIVE
    color_variant: str | None = None
    litter_name: str | None = None
    category: BreedingCategory = BreedingCategory.YOUNG
    feeding_stage: FeedingStage = FeedingStage.MAINTENANCE
    mating_date: date | None = None
    target_weight_grams: int | None = None
    target_date: date | None = None
    target_date_end: date | None = None
    notes: str | None = None
    breed_id: uuid.UUID | None = None
    cage_box_id: uuid.UUID | None = None
    feed_id: uuid.UUID | None = None
    mother_id: uuid.UUID | None = None
    father_id: uuid.UUID | None = None


class AnimalCreate(AnimalBase):
    pass


class AnimalUpdate(BaseModel):
    chip_number: str | None = None
    tattoo_number: str | None = None
    name: str | None = None
    sex: Sex | None = None
    birth_date: date | None = None
    status: AnimalStatus | None = None
    color_variant: str | None = None
    litter_name: str | None = None
    category: BreedingCategory | None = None
    feeding_stage: FeedingStage | None = None
    mating_date: date | None = None
    target_weight_grams: int | None = None
    target_date: date | None = None
    target_date_end: date | None = None
    notes: str | None = None
    breed_id: uuid.UUID | None = None
    cage_box_id: uuid.UUID | None = None
    feed_id: uuid.UUID | None = None
    mother_id: uuid.UUID | None = None
    father_id: uuid.UUID | None = None


class AnimalOut(AnimalBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    created_at: datetime
    updated_at: datetime
    breed: BreedOut | None = None
    feed: FeedOut | None = None
    cage_box_label: str | None = None
    inbreeding_coefficient: float | None = None


class AnimalListItem(BaseModel):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    chip_number: str
    name: str | None
    sex: Sex
    status: AnimalStatus
    category: BreedingCategory
    color_variant: str | None = None
    litter_name: str | None = None
    birth_date: date | None = None
    mother_id: uuid.UUID | None = None
    father_id: uuid.UUID | None = None
    breed: BreedSummary | None = None
    latest_weight_grams: int | None = None
    daily_feed_grams: float | None = None
    container_fill_pct: float | None = None


CageBoxOut.model_rebuild()


# ---- Wurf (Bulk-Anlage von Jungtieren) ----
class LitterCreate(BaseModel):
    mother_id: uuid.UUID
    father_id: uuid.UUID | None = None
    birth_date: date
    mating_date: date | None = None
    breed_id: uuid.UUID | None = None
    litter_name: str | None = None
    count_male: int = 0
    count_female: int = 0
    count_unknown: int = 0
    male_name_letter: str | None = None
    female_name_letter: str | None = None
    male_names: list[str | None] | None = None
    female_names: list[str | None] | None = None
    notes: str | None = None


class LitterResultOut(BaseModel):
    created: list[AnimalListItem]
    count: int


class NameSuggestionsOut(BaseModel):
    names: list[str | None]


# ---- WeightEntry ----
class WeightEntryBase(BaseModel):
    measured_on: date
    weight_grams: int
    notes: str | None = None


class WeightEntryCreate(WeightEntryBase):
    pass


class WeightEntryOut(WeightEntryBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    animal_id: uuid.UUID
    created_at: datetime


# ---- Evaluation ----
class EvaluationScoreBase(BaseModel):
    position_number: int = 0
    category_label: str
    max_points: int = 10
    points: float


class EvaluationScoreCreate(EvaluationScoreBase):
    pass


class EvaluationScoreOut(EvaluationScoreBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID


class EvaluationBase(BaseModel):
    evaluated_on: date
    show_name: str | None = None
    exhibitor_number: str | None = None
    exhibitor_name: str | None = None
    exhibitor_address: str | None = None
    total_score: float | None = None
    weight_grams: int | None = None
    notes: str | None = None


class EvaluationCreate(EvaluationBase):
    scores: list[EvaluationScoreCreate] = []
    source: str = "manual"
    photo_path: str | None = None


class EvaluationOut(EvaluationBase):
    model_config = ConfigDict(from_attributes=True)
    id: uuid.UUID
    animal_id: uuid.UUID
    photo_path: str | None = None
    source: str
    confirmed: bool
    created_at: datetime
    scores: list[EvaluationScoreOut] = []


# ---- Feeding plan ----
class FeedingPlanOut(BaseModel):
    animal_id: uuid.UUID
    weight_grams: int | None
    detected_phase: str
    feed_id: uuid.UUID | None
    feed_name: str | None
    daily_feed_grams: float | None
    reason: str | None = None
    target_weight_grams: float | None = None
    target_date: date | None = None
    days_remaining: int | None = None
    required_daily_gain_grams: float | None = None
    litter_size: int | None = None
    gestation_week: int | None = None
    is_late_gestation: bool | None = None
    phase_error: str | None = None
    feedback_hint: str | None = None
    container_fill_pct: float | None = None


# ---- Wachstum / Peak ----
class PeakWindowOut(BaseModel):
    start_date: date
    end_date: date | None


class TrendPointOut(BaseModel):
    age_weeks: float
    weight_grams: float


class GrowthStatusOut(BaseModel):
    age_weeks: float | None
    predicted_weight_grams: float | None
    actual_weight_grams: int | None
    deviation_pct: float | None
    status: str | None
    peak: PeakWindowOut | None
    target_date: date | None
    target_date_end: date | None
    target_date_in_peak_window: bool | None
    growth_rate: str | None = None
    own_trend: list[TrendPointOut] = []
    suggested_target_weight_grams: float | None = None
    target_weight_source: str | None = None
    target_weight_sample_count: int = 0


class CategoryComparisonOut(BaseModel):
    category_label: str
    animal_avg_pct: float
    breed_avg_pct: float
    diff_pct: float
    breed_sample_count: int


class StrengthsWeaknessesOut(BaseModel):
    strengths: list[CategoryComparisonOut]
    weaknesses: list[CategoryComparisonOut]


class DescendantGrowthPointOut(BaseModel):
    age_weeks: int
    mean_grams: float
    min_grams: int
    max_grams: int
    sample_count: int


class DescendantsGrowthOut(BaseModel):
    animal_id: uuid.UUID
    descendant_count: int
    points: list[DescendantGrowthPointOut]


class BreedGrowthCurveActualOut(BaseModel):
    breed_id: uuid.UUID
    animal_count: int
    points: list[DescendantGrowthPointOut]


class YearlyWeightStatOut(BaseModel):
    year: int
    breed_name: str
    avg_grams: float
    min_grams: int
    max_grams: int
    sample_count: int


class YearlyEvaluationStatOut(BaseModel):
    year: int
    breed_name: str
    category_label: str
    avg_points: float
    max_points: int
    sample_count: int


class FeedPlanPointOut(BaseModel):
    week: int
    age_weeks: float
    predicted_weight_grams: float | None
    daily_feed_grams: float | None


class FeedPlanYearOut(BaseModel):
    animal_id: uuid.UUID
    points: list[FeedPlanPointOut]


# ---- KI-Chat-Assistent ----
class ChatRequest(BaseModel):
    messages: list[dict]


class ChatResponse(BaseModel):
    messages: list[dict]


# ---- Bewertungskarten-Scan ----
class ScannedScoreOut(BaseModel):
    category_label: str
    points: float | None = None


class AnimalLookupOut(BaseModel):
    identifier: str
    matched_animal: AnimalListItem | None = None
    candidate_animals: list[AnimalListItem] = []


class ScanResultOut(BaseModel):
    photo_data_uri: str
    exhibitor_number: str | None = None
    exhibitor_name: str | None = None
    exhibitor_address: str | None = None
    show_name: str | None = None
    breed_name: str | None = None
    identification_number: str | None = None
    sex: str | None = None
    weight_grams: int | None = None
    scores: list[ScannedScoreOut] = []
    total_score: float | None = None
    notes: str | None = None
    matched_animal: AnimalListItem | None = None
    candidate_animals: list[AnimalListItem] = []


# ---- Stärken/Schwächen der Nachkommen ----
class OffspringScoreCategory(BaseModel):
    category_label: str
    average_points: float
    average_pct: float | None
    sample_count: int


class OffspringScoresOut(BaseModel):
    animal_id: uuid.UUID
    child_count: int
    evaluation_count: int
    categories: list[OffspringScoreCategory]


# ---- Würfe (Litter-Übersicht) ----
class LitterUpdate(BaseModel):
    new_litter_name: str | None = None
    birth_date: date | None = None
    mating_date: date | None = None
    breed_id: uuid.UUID | None = None


class LitterSummaryOut(BaseModel):
    litter_name: str
    birth_date: date | None
    breed_name: str | None
    mother_chip: str | None
    father_chip: str | None
    animal_count: int
    avg_latest_weight_grams: float | None
    avg_total_score: float | None


class LitterScorePositionOut(BaseModel):
    position_number: int
    category_label: str
    avg_points: float
    max_points: int
    sample_count: int


class LitterStatsOut(BaseModel):
    litter_name: str
    animal_count: int
    weight_curve: list[DescendantGrowthPointOut]
    score_positions: list[LitterScorePositionOut]
    avg_total_score: float | None
    evaluation_count: int


# ---- Pedigree / Inzucht ----
class PedigreeNode(BaseModel):
    id: str
    chip_number: str
    name: str | None
    sex: Sex
    breed_name: str | None
    inbreeding_coefficient: float
    mother: "PedigreeNode | None" = None
    father: "PedigreeNode | None" = None


PedigreeNode.model_rebuild()


class PairingCheckOut(BaseModel):
    mother_id: uuid.UUID
    father_id: uuid.UUID
    inbreeding_coefficient: float
    risk_level: str


class RelatednessOut(BaseModel):
    animal_a: uuid.UUID
    animal_b: uuid.UUID
    coefficient: float


# ---- Paarungsvorschläge ----
class MatingWeights(BaseModel):
    total_score: float = 1.0
    inbreeding: float = 1.0
    complement: float = 1.0


class MatingSuggestionOut(BaseModel):
    animal: AnimalListItem
    total_score: float | None
    inbreeding_coefficient: float
    complement_score: float | None
    focus_score: float | None
    final_score: float
    reasons: list[str]


# ---- Dashboard ----
class BreedCount(BaseModel):
    breed_name: str
    count: int


class AttentionItemOut(BaseModel):
    animal_id: uuid.UUID
    chip_number: str
    name: str | None
    reason: str


class DashboardOut(BaseModel):
    total_animals: int
    animals_by_status: dict[str, int]
    animals_by_category: dict[str, int]
    animals_by_breed: list[BreedCount]
    total_boxes: int
    free_box_capacity: int
    recent_weight_entries: list[WeightEntryOut]
    recent_evaluations: list[EvaluationOut]
    attention_items: list[AttentionItemOut]
