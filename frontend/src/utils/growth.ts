import type { DescendantGrowthPoint, GrowthCurvePoint, TrendPoint, WeightEntry } from "../api/types";

export interface WeightChartRow {
  date: string;
  grams?: number;
  predicted?: number;
  ownTrend?: number;
  siblingsActual?: number;
}

function addDays(dateStr: string, days: number): string {
  const d = new Date(dateStr + "T00:00:00");
  d.setDate(d.getDate() + Math.round(days));
  return d.toISOString().slice(0, 10);
}

export function buildWeightChartData(
  entries: WeightEntry[],
  birthDate: string | null,
  curve: GrowthCurvePoint[] | null,
  ownTrend?: TrendPoint[] | null,
  siblingsCurve?: DescendantGrowthPoint[] | null,
): WeightChartRow[] {
  const rows = new Map<string, WeightChartRow>();
  for (const w of entries) {
    rows.set(w.measured_on, { date: w.measured_on, grams: w.weight_grams });
  }
  // Die Gewichtslinie soll von Geburt an (0 g) sichtbar sein, nicht erst ab
  // dem ersten Wiegetermin -- nur wenn dafür noch kein echter Eintrag da ist.
  if (birthDate && entries.length > 0 && !rows.has(birthDate)) {
    rows.set(birthDate, { date: birthDate, grams: 0 });
  }
  if (birthDate && curve) {
    for (const p of curve) {
      const date = addDays(birthDate, p.age_weeks * 7);
      const existing = rows.get(date);
      if (existing) {
        existing.predicted = p.weight_grams;
      } else {
        rows.set(date, { date, predicted: p.weight_grams });
      }
    }
  }
  if (birthDate && ownTrend) {
    for (const p of ownTrend) {
      const date = addDays(birthDate, p.age_weeks * 7);
      const existing = rows.get(date);
      if (existing) {
        existing.ownTrend = p.weight_grams;
      } else {
        rows.set(date, { date, ownTrend: p.weight_grams });
      }
    }
  }
  if (birthDate && siblingsCurve && siblingsCurve.length > 0) {
    // Wie bei der eigenen Gewichtslinie: Start bei Geburt (0 g) ergänzen, damit
    // auch ein einzelner Alters-Punkt als echte Linie gezeichnet wird statt als
    // isolierter Punkt.
    const existingBirthRow = rows.get(birthDate);
    if (existingBirthRow) {
      existingBirthRow.siblingsActual = 0;
    } else {
      rows.set(birthDate, { date: birthDate, siblingsActual: 0 });
    }
    for (const p of siblingsCurve) {
      const date = addDays(birthDate, p.age_weeks * 7);
      const existing = rows.get(date);
      if (existing) {
        existing.siblingsActual = p.mean_grams;
      } else {
        rows.set(date, { date, siblingsActual: p.mean_grams });
      }
    }
  }
  return Array.from(rows.values()).sort((a, b) => a.date.localeCompare(b.date));
}

export const GROWTH_STATUS_LABELS: Record<string, string> = {
  im_plan: "im Plan",
  voraus: "voraus",
  hinterher: "hinterher",
};

export function growthStatusClass(status: string | null): string {
  if (status === "hinterher") return "status-deceased";
  if (status === "voraus") return "status-sold";
  return "";
}

export function descendantsChartData(points: DescendantGrowthPoint[]) {
  return points.map((p) => ({
    age: p.age_weeks,
    mean: p.mean_grams,
    min: p.min_grams,
    max: p.max_grams,
    range: [p.min_grams, p.max_grams],
    n: p.sample_count,
  }));
}
