import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import { BreedColorFilter } from "../components/BreedColorFilter";
import { useAsync } from "../hooks/useAsync";
import { niceAxisBounds } from "../utils/chartAxis";
import { aggregateSeasonPoints } from "../utils/seasons";

const ALL_POSITIONS = "__all__";
const ALL_SEASONS = "__all__";

export function YearlyStats() {
  const breeds = useAsync(() => api.stats.evaluatedBreeds(), []);
  const [breedId, setBreedId] = useState("");
  const [colorVariant, setColorVariant] = useState("");
  const [position, setPosition] = useState(ALL_POSITIONS);
  const [selectedSeason, setSelectedSeason] = useState(ALL_SEASONS);

  const evaluations = useAsync(
    () => api.stats.seasonEvaluations(breedId || undefined, colorVariant || undefined),
    [breedId, colorVariant],
  );

  const positionOptions = useMemo(() => {
    const labels = new Set<string>();
    for (const row of evaluations.data ?? []) labels.add(row.category_label);
    return Array.from(labels).sort();
  }, [evaluations.data]);

  const chartData = useMemo(() => {
    if (!evaluations.data) return [];
    const rows = position === ALL_POSITIONS ? evaluations.data : evaluations.data.filter((r) => r.category_label === position);
    return aggregateSeasonPoints(rows);
  }, [evaluations.data, position]);

  const chartMax = useMemo(() => {
    const max = Math.max(0, ...chartData.map((d) => d.maxPoints));
    return max > 0 ? max : undefined;
  }, [chartData]);

  // Statt immer bei 0 zu starten -- sonst wirken Unterschiede zwischen z.B.
  // 92 und 96 Punkten auf einer 0-100-Skala kaum sichtbar.
  const { domain: yDomain, ticks: yTicks } = useMemo(() => {
    if (chartData.length === 0) return niceAxisBounds(0, 100);
    const values = chartData.map((d) => d.points);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const padding = Math.max((max - min) * 0.1, 0.3);
    return niceAxisBounds(Math.max(0, min - padding), max + padding);
  }, [chartData]);

  const seasonOptions = useMemo(() => {
    const map = new Map<number, string>();
    for (const row of evaluations.data ?? []) map.set(row.season_start, row.season);
    return Array.from(map.entries()).sort((a, b) => b[0] - a[0]);
  }, [evaluations.data]);

  const evaluationsBySeason = useMemo(() => {
    const map = new Map<number, { season: string; rows: NonNullable<typeof evaluations.data> }>();
    for (const row of evaluations.data ?? []) {
      if (selectedSeason !== ALL_SEASONS && String(row.season_start) !== selectedSeason) continue;
      if (!map.has(row.season_start)) map.set(row.season_start, { season: row.season, rows: [] });
      map.get(row.season_start)!.rows.push(row);
    }
    return Array.from(map.entries()).sort((a, b) => b[0] - a[0]);
  }, [evaluations.data, selectedSeason]);

  // Gewählte Saison ist nach Filterwechsel evtl. nicht mehr vorhanden.
  const seasonStillValid = selectedSeason === ALL_SEASONS || seasonOptions.some(([s]) => String(s) === selectedSeason);
  const effectiveSeason = seasonStillValid ? selectedSeason : ALL_SEASONS;

  return (
    <div>
      <Link className="back-link" to="/">
        ← Zurück zur Übersicht
      </Link>
      <h1>Saisonvergleich</h1>
      <p className="hint" style={{ marginBottom: 16 }}>
        Eine Saison dauert vom 1. September bis 31. August (Saison 25/26 = 1.9.2025–31.8.2026).
        Zeigt, ob sich eine einzelne Bewertungsposition (z.B. Fell, Farbe) oder alle Positionen
        zusammen von Saison zu Saison verbessert oder verschlechtert haben — in Punkten, wie auf der
        Bewertungskarte. Zur Auswahl stehen nur Rassen mit eingetragenen Bewertungskarten.
      </p>

      <div className="toolbar">
        <BreedColorFilter
          breeds={breeds.data ?? []}
          breedId={breedId}
          colorVariant={colorVariant}
          onBreedChange={setBreedId}
          onColorVariantChange={setColorVariant}
        />
        <select value={position} onChange={(e) => setPosition(e.target.value)} style={{ flex: 1 }}>
          <option value={ALL_POSITIONS}>Alle Positionen zusammen</option>
          {positionOptions.map((p) => (
            <option key={p} value={p}>
              {p}
            </option>
          ))}
        </select>
      </div>

      <div className="card section">
        <h2>{position === ALL_POSITIONS ? "Alle Positionen" : position} je Saison</h2>
        {evaluations.loading && <p>Lade…</p>}
        {chartData.length > 0 ? (
          <div style={{ height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis dataKey="season" tick={{ fontSize: 12 }} />
                <YAxis domain={yDomain} ticks={yTicks} tick={{ fontSize: 12 }} width={40} />
                <Tooltip
                  labelFormatter={(label: unknown) => `Saison ${String(label)}`}
                  formatter={(value: unknown) => [
                    chartMax ? `${String(value)} / ${chartMax}` : String(value),
                    "Ø Punkte",
                  ]}
                />
                <Line type="monotone" dataKey="points" name="Ø Punkte" stroke="#4338ca" strokeWidth={2} dot={{ r: 4 }} />
              </LineChart>
            </ResponsiveContainer>
          </div>
        ) : (
          !evaluations.loading && <p className="empty-state">Noch keine Bewertungsdaten für diese Auswahl.</p>
        )}
      </div>

      <div className="card section">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
          <h2>Saisonübersicht</h2>
          <select value={effectiveSeason} onChange={(e) => setSelectedSeason(e.target.value)}>
            <option value={ALL_SEASONS}>Alle Saisons</option>
            {seasonOptions.map(([start, label]) => (
              <option key={start} value={String(start)}>
                Saison {label}
              </option>
            ))}
          </select>
        </div>
        {evaluationsBySeason.map(([start, { season, rows }]) => (
          <div key={start} style={{ marginBottom: 16 }}>
            <h3>
              Saison {season}{" "}
              <span className="hint">
                (1.9.{start} – 31.8.{start + 1})
              </span>
            </h3>
            <table>
              <thead>
                <tr>
                  <th>Rasse</th>
                  <th>Position</th>
                  <th>Ø Punkte</th>
                  <th>Karten</th>
                </tr>
              </thead>
              <tbody>
                {rows
                  .slice()
                  .filter((r) => position === ALL_POSITIONS || r.category_label === position)
                  .sort((a, b) => b.avg_points / b.max_points - a.avg_points / a.max_points)
                  .map((r) => (
                    <tr key={`${r.breed_name}-${r.category_label}`}>
                      <td>{r.breed_name}</td>
                      <td>{r.category_label}</td>
                      <td>
                        {r.avg_points} / {r.max_points}
                      </td>
                      <td>{r.sample_count}</td>
                    </tr>
                  ))}
              </tbody>
            </table>
          </div>
        ))}
        {evaluations.data && evaluations.data.length === 0 && (
          <p className="empty-state">Noch keine Bewertungsdaten.</p>
        )}
      </div>
    </div>
  );
}
