import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import { useAsync } from "../hooks/useAsync";
import { niceAxisBounds } from "../utils/chartAxis";

const ALL_POSITIONS = "__all__";

export function YearlyStats() {
  const breeds = useAsync(() => api.breeds.list(), []);
  const [breedId, setBreedId] = useState("");
  const [position, setPosition] = useState(ALL_POSITIONS);

  const evaluations = useAsync(() => api.stats.yearlyEvaluations(breedId || undefined), [breedId]);

  const positionOptions = useMemo(() => {
    const labels = new Set<string>();
    for (const row of evaluations.data ?? []) labels.add(row.category_label);
    return Array.from(labels).sort();
  }, [evaluations.data]);

  const chartData = useMemo(() => {
    if (!evaluations.data) return [];
    const rows = position === ALL_POSITIONS ? evaluations.data : evaluations.data.filter((r) => r.category_label === position);
    const byYear = new Map<number, { points: number; maxPoints: number }>();
    for (const r of rows) {
      const entry = byYear.get(r.year) ?? { points: 0, maxPoints: 0 };
      entry.points += r.avg_points;
      entry.maxPoints += r.max_points;
      byYear.set(r.year, entry);
    }
    return Array.from(byYear.entries())
      .map(([year, { points, maxPoints }]) => ({
        year,
        points: Math.round(points * 10) / 10,
        maxPoints,
      }))
      .sort((a, b) => a.year - b.year);
  }, [evaluations.data, position]);

  const chartMax = useMemo(() => {
    const max = Math.max(0, ...chartData.map((d) => d.maxPoints));
    return max > 0 ? max : undefined;
  }, [chartData]);

  // Statt immer bei 0 zu starten -- sonst wirken Unterschiede zwischen z.B.
  // 92 und 96 Punkten auf einer 0-100-Skala kaum sichtbar. Runde, saubere
  // Achsenwerte statt rechts eigener (teils fehlerhafter) Tick-Berechnung.
  const { domain: yDomain, ticks: yTicks } = useMemo(() => {
    if (chartData.length === 0) return niceAxisBounds(0, 100);
    const values = chartData.map((d) => d.points);
    const min = Math.min(...values);
    const max = Math.max(...values);
    const padding = Math.max((max - min) * 0.1, 0.3);
    return niceAxisBounds(Math.max(0, min - padding), max + padding);
  }, [chartData]);

  const evaluationsByYear = useMemo(() => {
    const map = new Map<number, typeof evaluations.data>();
    for (const row of evaluations.data ?? []) {
      if (!map.has(row.year)) map.set(row.year, []);
      map.get(row.year)!.push(row);
    }
    return Array.from(map.entries()).sort((a, b) => b[0] - a[0]);
  }, [evaluations.data]);

  return (
    <div>
      <Link className="back-link" to="/">
        ← Zurück zur Übersicht
      </Link>
      <h1>Jahresvergleich</h1>
      <p className="hint" style={{ marginBottom: 16 }}>
        Zeigt, ob sich eine einzelne Bewertungsposition (z.B. Fell, Farbe) oder alle Positionen
        zusammen über die Jahre verbessert oder verschlechtert haben — in Punkten, wie auf der
        Bewertungskarte.
      </p>

      <div className="toolbar">
        <select value={breedId} onChange={(e) => setBreedId(e.target.value)} style={{ flex: 1 }}>
          <option value="">Alle Rassen</option>
          {breeds.data?.map((b) => (
            <option key={b.id} value={b.id}>
              {b.name}
            </option>
          ))}
        </select>
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
        <h2>{position === ALL_POSITIONS ? "Alle Positionen" : position} über die Jahre</h2>
        {evaluations.loading && <p>Lade…</p>}
        {chartData.length > 0 ? (
          <div style={{ height: 260 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis dataKey="year" tick={{ fontSize: 12 }} />
                <YAxis domain={yDomain} ticks={yTicks} tick={{ fontSize: 12 }} width={40} />
                <Tooltip
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
        <h2>Details je Jahr</h2>
        {evaluationsByYear.map(([year, rows]) => (
          <div key={year} style={{ marginBottom: 16 }}>
            <h3>{year}</h3>
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
                  ?.slice()
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
