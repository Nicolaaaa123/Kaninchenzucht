export type Sex = "male" | "female" | "unknown";
export type AnimalStatus = "active" | "sold" | "deceased" | "retired" | "slaughtered";
export type BreedingCategory = "young" | "breeding" | "external";
export type BreedGroup = "dwarf" | "small" | "medium" | "large";
export type FeedingStage = "maintenance" | "growth" | "gestation" | "lactation";

export interface BreedScoringPosition {
  id?: string;
  position_number: number;
  label: string;
  max_points: number;
}

export interface Breed {
  id: string;
  name: string;
  abbreviation: string | null;
  group: BreedGroup | null;
  min_weight_kg: number | null;
  ideal_weight_min_kg: number | null;
  ideal_weight_max_kg: number | null;
  max_weight_kg: number | null;
  gestation_days: number | null;
  lactation_weeks: number | null;
  notes: string | null;
  created_at: string;
  scoring_positions: BreedScoringPosition[];
}

export interface BreedGrowthPoint {
  id?: string;
  age_weeks: number;
  weight_grams: number;
}

export interface GrowthCurvePoint {
  age_weeks: number;
  weight_grams: number;
}

export interface GrowthCurve {
  breed_id: string;
  source: "custom" | "predicted";
  custom_points: BreedGrowthPoint[];
  curve: GrowthCurvePoint[];
}

export interface PeakWindow {
  start_date: string;
  end_date: string | null;
}

export interface TrendPoint {
  age_weeks: number;
  weight_grams: number;
}

export interface GrowthStatus {
  age_weeks: number | null;
  predicted_weight_grams: number | null;
  actual_weight_grams: number | null;
  deviation_pct: number | null;
  status: "im_plan" | "voraus" | "hinterher" | null;
  peak: PeakWindow | null;
  target_date: string | null;
  target_date_end: string | null;
  target_date_in_peak_window: boolean | null;
  growth_rate: "schnell" | "mittel" | "langsam" | null;
  own_trend: TrendPoint[];
  suggested_target_weight_grams: number | null;
  target_weight_source: "manual" | "breed" | "family" | null;
  target_weight_sample_count: number;
}

export interface CategoryComparison {
  category_label: string;
  animal_avg_pct: number;
  breed_avg_pct: number;
  diff_pct: number;
  breed_sample_count: number;
}

export interface StrengthsWeaknesses {
  strengths: CategoryComparison[];
  weaknesses: CategoryComparison[];
}

export interface BreedGrowthCurveActual {
  breed_id: string;
  animal_count: number;
  points: DescendantGrowthPoint[];
}

export interface YearlyWeightStat {
  year: number;
  breed_name: string;
  avg_grams: number;
  min_grams: number;
  max_grams: number;
  sample_count: number;
}

export interface YearlyEvaluationStat {
  year: number;
  breed_name: string;
  category_label: string;
  avg_points: number;
  max_points: number;
  sample_count: number;
}

export interface FeedPlanPoint {
  week: number;
  age_weeks: number;
  predicted_weight_grams: number | null;
  daily_feed_grams: number | null;
}

export interface FeedPlanYear {
  animal_id: string;
  points: FeedPlanPoint[];
}

export interface DescendantGrowthPoint {
  age_weeks: number;
  mean_grams: number;
  min_grams: number;
  max_grams: number;
  sample_count: number;
}

export interface DescendantsGrowth {
  animal_id: string;
  descendant_count: number;
  points: DescendantGrowthPoint[];
}

export interface BreedSummary {
  id: string;
  name: string;
  abbreviation: string | null;
  group: BreedGroup | null;
}

export interface Feed {
  id: string;
  name: string;
  manufacturer: string | null;
  energy_mj_per_kg: number;
  crude_protein_pct: number | null;
  crude_fiber_pct: number | null;
  crude_fat_pct: number | null;
  container_capacity_grams: number | null;
  notes: string | null;
  created_at: string;
}

export interface AnimalListItem {
  id: string;
  chip_number: string;
  name: string | null;
  sex: Sex;
  status: AnimalStatus;
  category: BreedingCategory;
  color_variant: string | null;
  litter_name: string | null;
  birth_date: string | null;
  mother_id: string | null;
  father_id: string | null;
  breed: BreedSummary | null;
  latest_weight_grams: number | null;
  daily_feed_grams: number | null;
  container_fill_pct: number | null;
}

export interface CageBox {
  id: string;
  stall_id: string;
  label: string;
  row_index: number;
  col_index: number;
  capacity: number;
  notes: string | null;
  occupants: AnimalListItem[];
}

export interface StallPage {
  id: string;
  label: string;
  position: number;
  created_at: string;
}

export interface Stall {
  id: string;
  label: string;
  rows: number;
  columns: number;
  position: number;
  page_id: string | null;
  notes: string | null;
  created_at: string;
  boxes: CageBox[];
}

export interface Animal {
  id: string;
  chip_number: string;
  tattoo_number: string | null;
  name: string | null;
  sex: Sex;
  birth_date: string | null;
  status: AnimalStatus;
  color_variant: string | null;
  litter_name: string | null;
  category: BreedingCategory;
  feeding_stage: FeedingStage;
  mating_date: string | null;
  target_weight_grams: number | null;
  target_date: string | null;
  target_date_end: string | null;
  notes: string | null;
  breed_id: string | null;
  cage_box_id: string | null;
  feed_id: string | null;
  mother_id: string | null;
  father_id: string | null;
  created_at: string;
  updated_at: string;
  breed: Breed | null;
  feed: Feed | null;
  cage_box_label: string | null;
  inbreeding_coefficient: number | null;
}

export interface LitterCreate {
  mother_id: string;
  father_id?: string | null;
  birth_date: string;
  mating_date?: string | null;
  breed_id?: string | null;
  litter_name?: string | null;
  count_male: number;
  count_female: number;
  count_unknown: number;
  male_name_letter?: string | null;
  female_name_letter?: string | null;
  male_names?: (string | null)[] | null;
  female_names?: (string | null)[] | null;
  notes?: string | null;
}

export interface NameSuggestions {
  names: (string | null)[];
}

export interface LitterResult {
  created: AnimalListItem[];
  count: number;
}

export interface WeightEntry {
  id: string;
  animal_id: string;
  measured_on: string;
  weight_grams: number;
  notes: string | null;
  created_at: string;
}

export interface EvaluationScore {
  id?: string;
  position_number: number;
  category_label: string;
  max_points: number;
  points: number;
}

export interface Evaluation {
  id: string;
  animal_id: string;
  evaluated_on: string;
  show_name: string | null;
  exhibitor_number: string | null;
  exhibitor_name: string | null;
  exhibitor_address: string | null;
  total_score: number | null;
  weight_grams: number | null;
  photo_path: string | null;
  source: string;
  confirmed: boolean;
  notes: string | null;
  created_at: string;
  scores: EvaluationScore[];
}

export type FeedingPhase = "growth" | "over_ideal" | "gestation" | "lactation" | "maintenance";

export interface FeedingPlan {
  animal_id: string;
  weight_grams: number | null;
  detected_phase: FeedingPhase;
  feed_id: string | null;
  feed_name: string | null;
  daily_feed_grams: number | null;
  reason: string | null;
  target_weight_grams: number | null;
  target_date: string | null;
  days_remaining: number | null;
  required_daily_gain_grams: number | null;
  litter_size: number | null;
  gestation_week: number | null;
  is_late_gestation: boolean | null;
  phase_error: string | null;
  feedback_hint: string | null;
  container_fill_pct: number | null;
}

export interface PedigreeNode {
  id: string;
  chip_number: string;
  name: string | null;
  sex: Sex;
  breed_name: string | null;
  inbreeding_coefficient: number;
  mother: PedigreeNode | null;
  father: PedigreeNode | null;
}

export interface ChatContentBlock {
  type: string;
  text?: string;
  name?: string;
  input?: Record<string, unknown>;
  [key: string]: unknown;
}

export interface ChatMessage {
  role: "user" | "assistant";
  content: ChatContentBlock[];
}

export interface ScannedScore {
  category_label: string;
  points: number | null;
}

export interface ScanResult {
  photo_data_uri: string;
  exhibitor_number: string | null;
  exhibitor_name: string | null;
  exhibitor_address: string | null;
  show_name: string | null;
  breed_name: string | null;
  identification_number: string | null;
  sex: string | null;
  weight_grams: number | null;
  scores: ScannedScore[];
  total_score: number | null;
  notes: string | null;
  matched_animal: AnimalListItem | null;
  candidate_animals: AnimalListItem[];
}

export interface AnimalLookup {
  identifier: string;
  matched_animal: AnimalListItem | null;
  candidate_animals: AnimalListItem[];
}

export interface PairingCheck {
  mother_id: string;
  father_id: string;
  inbreeding_coefficient: number;
  risk_level: string;
}

export interface Relatedness {
  animal_a: string;
  animal_b: string;
  coefficient: number;
}

export interface OffspringScoreCategory {
  category_label: string;
  average_points: number;
  average_pct: number | null;
  sample_count: number;
}

export interface OffspringScores {
  animal_id: string;
  child_count: number;
  evaluation_count: number;
  categories: OffspringScoreCategory[];
}

export interface MatingSuggestion {
  animal: AnimalListItem;
  total_score: number | null;
  inbreeding_coefficient: number;
  complement_score: number | null;
  focus_score: number | null;
  final_score: number;
  reasons: string[];
}

export interface AttentionItem {
  animal_id: string;
  chip_number: string;
  name: string | null;
  reason: string;
}

export interface User {
  id: string;
  username: string;
  display_name: string | null;
  is_admin: boolean;
  invite_code: string;
  tenant_id: string;
}

export interface LitterSummary {
  litter_name: string;
  birth_date: string | null;
  breed_name: string | null;
  mother_chip: string | null;
  father_chip: string | null;
  animal_count: number;
  avg_latest_weight_grams: number | null;
  avg_total_score: number | null;
}

export interface LitterUpdate {
  new_litter_name?: string | null;
  birth_date?: string | null;
  mating_date?: string | null;
  breed_id?: string | null;
}

export interface LitterScorePosition {
  position_number: number;
  category_label: string;
  avg_points: number;
  max_points: number;
  sample_count: number;
}

export interface LitterStats {
  litter_name: string;
  animal_count: number;
  weight_curve: DescendantGrowthPoint[];
  score_positions: LitterScorePosition[];
  avg_total_score: number | null;
  evaluation_count: number;
}

export interface DashboardData {
  total_animals: number;
  animals_by_status: Record<string, number>;
  animals_by_category: Record<string, number>;
  animals_by_breed: { breed_name: string; count: number }[];
  total_boxes: number;
  free_box_capacity: number;
  recent_weight_entries: WeightEntry[];
  recent_evaluations: Evaluation[];
  attention_items: AttentionItem[];
}
