import { useMemo, useState } from "react";
import { CartesianGrid, Legend, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import { useAsync } from "../hooks/useAsync";
import type { Animal, WeightEntry } from "../api/types";
import { coiLabel, coiRiskClass } from "../utils/inbreeding";

const COLORS = ["#4338ca", "#0d9488", "#d97706", "#dc2626", "#7c3aed", "#0ea5e9"];

const SEX_LABELS: Record<string, string> = { male: "♂", female: "♀", unknown: "?" };
const STATUS_LABELS: Record<string, string> = {
  active: "Aktiv",
  sold: "Verkauft",
  deceased: "Verstorben",
  retired: "Aus der Zucht",
  slaughtered: "Geschlachtet",
};

interface Entry {
  animal: Animal;
  weights: WeightEntry[];
  latestTotalScore: number | null;
  avgTotalScore: number | null;
  evaluationCount: number;
}

export function Compare() {
  const allAnimals = useAsync(() => api.animals.list(), []);
  const [selectedIds, setSelectedIds] = useState<string[]>([]);
  const [addValue, setAddValue] = useState("");

  const details = useAsync<Entry[]>(
    () =>
      Promise.all(
        selectedIds.map(async (id) => {
          const [animal, weights, evaluations] = await Promise.all([
            api.animals.get(id),
            api.weights.list(id),
            api.evaluations.list(id),
          ]);
          const scored = evaluations.filter((e) => e.total_score != null);
          const avgTotalScore = scored.length
            ? Math.round((scored.reduce((sum, e) => sum + (e.total_score ?? 0), 0) / scored.length) * 10) / 10
            : null;
          return {
            animal,
            weights,
            latestTotalScore: evaluations[0]?.total_score ?? null,
            avgTotalScore,
            evaluationCount: scored.length,
          };
        }),
      ),
    [selectedIds.join(",")],
  );

  const relatedness = useAsync(async () => {
    const pairs: { a: string; b: string; coefficient: number }[] = [];
    for (let i = 0; i < selectedIds.length; i++) {
      for (let j = i + 1; j < selectedIds.length; j++) {
        const r = await api.animals.relatedness(selectedIds[i], selectedIds[j]);
        pairs.push({ a: selectedIds[i], b: selectedIds[j], coefficient: r.coefficient });
      }
    }
    return pairs;
  }, [selectedIds.join(",")]);

  const chartData = useMemo(() => {
    if (!details.data) return [];
    const dates = new Set<string>();
    details.data.forEach((e) => e.weights.forEach((w) => dates.add(w.measured_on)));
    return Array.from(dates)
      .sort()
      .map((date) => {
        const row: Record<string, string | number> = { date };
        details.data!.forEach((e) => {
          const entry = e.weights.find((w) => w.measured_on === date);
          if (entry) row[e.animal.chip_number] = entry.weight_grams;
        });
        return row;
      });
  }, [details.data]);

  function addAnimal(id: string) {
    if (!id || selectedIds.includes(id)) return;
    setSelectedIds((prev) => [...prev, id]);
    setAddValue("");
  }

  function removeAnimal(id: string) {
    setSelectedIds((prev) => prev.filter((x) => x !== id));
  }

  return (
    <div>
      <h1>Tiervergleich</h1>

      <div className="card section">
        <div className="toolbar" style={{ marginBottom: 0 }}>
          <select value={addValue} onChange={(e) => addAnimal(e.target.value)} style={{ maxWidth: 320 }}>
            <option value="">Tier hinzufügen…</option>
            {allAnimals.data
              ?.filter((a) => !selectedIds.includes(a.id))
              .map((a) => (
                <option key={a.id} value={a.id}>
                  {a.chip_number} {a.name ? `· ${a.name}` : ""}
                </option>
              ))}
          </select>
        </div>
      </div>

      {details.data && details.data.length > 0 && (
        <>
          <div className="card section" style={{ overflowX: "auto" }}>
            <table>
              <tbody>
                <tr>
                  <th></th>
                  {details.data.map((e, i) => (
                    <td key={e.animal.id}>
                      <strong style={{ color: COLORS[i % COLORS.length] }}>{e.animal.chip_number}</strong>
                      <button className="btn secondary small" style={{ marginLeft: 6 }} onClick={() => removeAnimal(e.animal.id)}>
                        ×
                      </button>
                    </td>
                  ))}
                </tr>
                <tr>
                  <th>Name</th>
                  {details.data.map((e) => (
                    <td key={e.animal.id}>{e.animal.name ?? "–"}</td>
                  ))}
                </tr>
                <tr>
                  <th>Rasse</th>
                  {details.data.map((e) => (
                    <td key={e.animal.id}>{e.animal.breed?.name ?? "–"}</td>
                  ))}
                </tr>
                <tr>
                  <th>Geschlecht</th>
                  {details.data.map((e) => (
                    <td key={e.animal.id}>{SEX_LABELS[e.animal.sex]}</td>
                  ))}
                </tr>
                <tr>
                  <th>Status</th>
                  {details.data.map((e) => (
                    <td key={e.animal.id}>{STATUS_LABELS[e.animal.status]}</td>
                  ))}
                </tr>
                <tr>
                  <th>Geburtsdatum</th>
                  {details.data.map((e) => (
                    <td key={e.animal.id}>{e.animal.birth_date ?? "–"}</td>
                  ))}
                </tr>
                <tr>
                  <th>Letztes Gewicht</th>
                  {details.data.map((e) => (
                    <td key={e.animal.id}>
                      {e.weights.length ? `${e.weights[e.weights.length - 1].weight_grams} g` : "–"}
                    </td>
                  ))}
                </tr>
                <tr>
                  <th>Letzte Gesamtpunktzahl</th>
                  {details.data.map((e) => (
                    <td key={e.animal.id}>{e.latestTotalScore ?? "–"}</td>
                  ))}
                </tr>
                <tr>
                  <th>Ø Gesamtpunktzahl (alle Karten)</th>
                  {details.data.map((e) => (
                    <td key={e.animal.id}>
                      {e.avgTotalScore != null ? (
                        <>
                          {e.avgTotalScore}{" "}
                          <span className="hint">
                            ({e.evaluationCount} Karte{e.evaluationCount === 1 ? "" : "n"}
                            {e.latestTotalScore != null &&
                              `, letzte ${e.latestTotalScore > e.avgTotalScore ? "über" : e.latestTotalScore < e.avgTotalScore ? "unter" : "auf"} Ø`}
                            )
                          </span>
                        </>
                      ) : (
                        "–"
                      )}
                    </td>
                  ))}
                </tr>
                <tr>
                  <th>Eigener Inzuchtkoeffizient</th>
                  {details.data.map((e) => (
                    <td key={e.animal.id}>
                      {e.animal.inbreeding_coefficient != null ? (
                        <span className={`badge ${coiRiskClass(e.animal.inbreeding_coefficient)}`}>
                          {coiLabel(e.animal.inbreeding_coefficient)}
                        </span>
                      ) : (
                        "–"
                      )}
                    </td>
                  ))}
                </tr>
              </tbody>
            </table>
          </div>

          {chartData.length > 0 && (
            <div className="card section">
              <h2>Gewichtsverlauf</h2>
              <div style={{ height: 240 }}>
                <ResponsiveContainer width="100%" height="100%">
                  <LineChart data={chartData}>
                    <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                    <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                    <YAxis tick={{ fontSize: 11 }} width={50} />
                    <Tooltip />
                    <Legend />
                    {details.data.map((e, i) => (
                      <Line
                        key={e.animal.id}
                        type="monotone"
                        dataKey={e.animal.chip_number}
                        stroke={COLORS[i % COLORS.length]}
                        strokeWidth={2}
                        dot={{ r: 2 }}
                        connectNulls
                      />
                    ))}
                  </LineChart>
                </ResponsiveContainer>
              </div>
            </div>
          )}

          {details.data.length > 1 && (
            <div className="card section">
              <h2>Verwandtschaft zueinander</h2>
              <table>
                <tbody>
                  {relatedness.data?.map((r) => {
                    const a = details.data!.find((e) => e.animal.id === r.a)!;
                    const b = details.data!.find((e) => e.animal.id === r.b)!;
                    return (
                      <tr key={`${r.a}-${r.b}`}>
                        <th>
                          {a.animal.chip_number} ↔ {b.animal.chip_number}
                        </th>
                        <td>
                          <span className={`badge ${coiRiskClass(r.coefficient)}`}>{coiLabel(r.coefficient)}</span>
                        </td>
                      </tr>
                    );
                  })}
                </tbody>
              </table>
            </div>
          )}
        </>
      )}

      {selectedIds.length === 0 && (
        <p className="empty-state">Wähle oben mindestens zwei Tiere zum Vergleichen aus.</p>
      )}
    </div>
  );
}
