// Wortwerte-Punktetabelle nach Standard 2015 (Rassekaninchen Schweiz),
// Bewertungsbestimmungen: 8 Positionswerte, je nach Positionsgewicht (10/15/20)
// ergeben sich unterschiedliche Punktebänder pro Wortwert.
export interface WortwertBand {
  key: string;
  label: string;
  points: number[]; // discrete allowed point values (0.5 steps) for this band
}

const BANDS_BY_WEIGHT: Record<number, { key: string; label: string; range: [number, number] }[]> = {
  20: [
    { key: "ideal", label: "Ideal", range: [20, 20] },
    { key: "gut_bis_sehr_gut", label: "Gut bis sehr gut", range: [18.5, 19.5] },
    { key: "genuegend", label: "Genügend", range: [18, 18] },
    { key: "ungenuegend", label: "Ungenügend", range: [17, 17.5] },
    { key: "schwach", label: "Schwach", range: [16, 16.5] },
    { key: "sehr_schwach", label: "Sehr schwach", range: [15, 15.5] },
  ],
  15: [
    { key: "ideal", label: "Ideal", range: [15, 15] },
    { key: "gut_bis_sehr_gut", label: "Gut bis sehr gut", range: [14, 14.5] },
    { key: "genuegend", label: "Genügend", range: [13.5, 13.5] },
    { key: "ungenuegend", label: "Ungenügend", range: [13, 13] },
    { key: "schwach", label: "Schwach", range: [12, 12.5] },
    { key: "sehr_schwach", label: "Sehr schwach", range: [11, 11.5] },
  ],
  10: [
    { key: "ideal", label: "Ideal", range: [10, 10] },
    { key: "gut_bis_sehr_gut", label: "Gut bis sehr gut", range: [9.5, 9.5] },
    { key: "genuegend", label: "Genügend", range: [9, 9] },
    { key: "ungenuegend", label: "Ungenügend", range: [8.5, 8.5] },
    { key: "schwach", label: "Schwach", range: [8, 8] },
    { key: "sehr_schwach", label: "Sehr schwach", range: [7, 7.5] },
  ],
};

export function pointOptionsForMaxPoints(maxPoints: number): { value: number; label: string }[] {
  const bands = BANDS_BY_WEIGHT[maxPoints] ?? BANDS_BY_WEIGHT[10];
  const options: { value: number; label: string }[] = [];
  for (const band of bands) {
    const [lo, hi] = band.range;
    for (let v = hi; v >= lo; v -= 0.5) {
      options.push({ value: Math.round(v * 10) / 10, label: `${v} – ${band.label}` });
    }
  }
  return options;
}

export const EXCLUSION_THRESHOLD = 90.0;
