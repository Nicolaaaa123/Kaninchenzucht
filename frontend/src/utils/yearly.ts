import type { YearlyEvaluationStat } from "../api/types";

export interface YearlyPoints {
  year: number;
  points: number;
  maxPoints: number;
}

/** Jahresverlauf der Bewertungspunkte. Erst pro (Jahr, Rasse) die Positionen
 * aufsummieren, danach -- falls in einem Jahr mehrere Rassen vorkommen -- deren
 * Jahrestotale MITTELN statt addieren. Sonst würde ein Jahr mit zwei Rassen
 * fälschlich die doppelte Punktzahl zeigen (z.B. 191 statt ~96). */
export function aggregateYearlyPoints(rows: YearlyEvaluationStat[]): YearlyPoints[] {
  const byYearBreed = new Map<string, { points: number; maxPoints: number }>();
  for (const r of rows) {
    const key = `${r.year}|${r.breed_name}`;
    const entry = byYearBreed.get(key) ?? { points: 0, maxPoints: 0 };
    entry.points += r.avg_points;
    entry.maxPoints += r.max_points;
    byYearBreed.set(key, entry);
  }
  const byYear = new Map<number, { pointsList: number[]; maxPoints: number }>();
  for (const [key, { points, maxPoints }] of byYearBreed) {
    const year = Number(key.split("|")[0]);
    const entry = byYear.get(year) ?? { pointsList: [], maxPoints };
    entry.pointsList.push(points);
    entry.maxPoints = maxPoints;
    byYear.set(year, entry);
  }
  return Array.from(byYear.entries())
    .map(([year, { pointsList, maxPoints }]) => ({
      year,
      points: Math.round((pointsList.reduce((a, b) => a + b, 0) / pointsList.length) * 10) / 10,
      maxPoints,
    }))
    .sort((a, b) => a.year - b.year);
}
