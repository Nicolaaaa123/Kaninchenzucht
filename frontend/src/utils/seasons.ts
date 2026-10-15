import type { SeasonEvaluationStat } from "../api/types";

export interface SeasonPoints {
  season: string;
  seasonStart: number;
  points: number;
  maxPoints: number;
}

/** Saisonverlauf der Bewertungspunkte (Saison 25/26 = 1.9.2025–31.8.2026). Erst
 * pro (Saison, Rasse) die Positionen aufsummieren, danach -- falls in einer
 * Saison mehrere Rassen vorkommen -- deren Totale MITTELN statt addieren.
 * Sonst würde eine Saison mit zwei Rassen fälschlich die doppelte Punktzahl
 * zeigen (z.B. 191 statt ~96). */
export function aggregateSeasonPoints(rows: SeasonEvaluationStat[]): SeasonPoints[] {
  const bySeasonBreed = new Map<string, { seasonStart: number; season: string; points: number; maxPoints: number }>();
  for (const r of rows) {
    const key = `${r.season_start}|${r.breed_name}`;
    const entry = bySeasonBreed.get(key) ?? { seasonStart: r.season_start, season: r.season, points: 0, maxPoints: 0 };
    entry.points += r.avg_points;
    entry.maxPoints += r.max_points;
    bySeasonBreed.set(key, entry);
  }
  const bySeason = new Map<number, { season: string; pointsList: number[]; maxPoints: number }>();
  for (const { seasonStart, season, points, maxPoints } of bySeasonBreed.values()) {
    const entry = bySeason.get(seasonStart) ?? { season, pointsList: [], maxPoints };
    entry.pointsList.push(points);
    entry.maxPoints = maxPoints;
    bySeason.set(seasonStart, entry);
  }
  return Array.from(bySeason.entries())
    .map(([seasonStart, { season, pointsList, maxPoints }]) => ({
      season,
      seasonStart,
      points: Math.round((pointsList.reduce((a, b) => a + b, 0) / pointsList.length) * 10) / 10,
      maxPoints,
    }))
    .sort((a, b) => a.seasonStart - b.seasonStart);
}

/** Aktuelle Saison als Startjahr (ab 1. September beginnt die neue). */
export function currentSeasonStart(today = new Date()): number {
  return today.getMonth() >= 8 ? today.getFullYear() : today.getFullYear() - 1;
}
