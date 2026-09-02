import { useMemo } from "react";
import { Link } from "react-router-dom";
import { CartesianGrid, Line, LineChart, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import { ClipboardCheckIcon, ScaleIcon } from "../components/Icons";
import { useAsync } from "../hooks/useAsync";

const CATEGORY_LABELS: Record<string, string> = {
  breeding: "Zuchttiere",
  young: "Jungtiere",
  external: "Externe Zuchttiere",
};

type ActivityItem = {
  id: string;
  animalId: string;
  date: string;
  icon: "weight" | "evaluation";
  label: string;
  value: string;
};

export function Dashboard() {
  const { data, loading, error } = useAsync(() => api.dashboard(), []);
  const yearlyEvaluations = useAsync(() => api.stats.yearlyEvaluations(), []);

  const yearlyChartData = useMemo(() => {
    const byYear = new Map<number, number>();
    for (const r of yearlyEvaluations.data ?? []) {
      byYear.set(r.year, (byYear.get(r.year) ?? 0) + r.avg_points);
    }
    return Array.from(byYear.entries())
      .map(([year, points]) => ({ year, points: Math.round(points * 10) / 10 }))
      .sort((a, b) => a.year - b.year);
  }, [yearlyEvaluations.data]);

  const activity = useMemo<ActivityItem[]>(() => {
    if (!data) return [];
    const items: ActivityItem[] = [
      ...data.recent_weight_entries.map((w) => ({
        id: `w-${w.id}`,
        animalId: w.animal_id,
        date: w.measured_on,
        icon: "weight" as const,
        label: "Gewicht erfasst",
        value: `${w.weight_grams} g`,
      })),
      ...data.recent_evaluations.map((e) => ({
        id: `e-${e.id}`,
        animalId: e.animal_id,
        date: e.evaluated_on,
        icon: "evaluation" as const,
        label: e.show_name ? `Bewertung · ${e.show_name}` : "Bewertung",
        value: e.total_score != null ? `${e.total_score} Pkt.` : "–",
      })),
    ];
    return items.sort((a, b) => b.date.localeCompare(a.date)).slice(0, 10);
  }, [data]);

  const categoryTotal = useMemo(() => {
    if (!data) return 0;
    return (["breeding", "young", "external"] as const).reduce((sum, c) => sum + (data.animals_by_category[c] ?? 0), 0);
  }, [data]);

  const maxBreedCount = useMemo(() => Math.max(1, ...(data?.animals_by_breed.map((b) => b.count) ?? [1])), [data]);

  if (loading) return <p>Lade Dashboard…</p>;
  if (error) return <div className="error-banner">Fehler beim Laden: {error}</div>;
  if (!data) return null;

  return (
    <div>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "center", flexWrap: "wrap", gap: 8 }}>
        <h1>Übersicht</h1>
        <div className="toolbar" style={{ marginBottom: 0 }}>
          <Link className="btn" to="/tiere/wurf">
            + Wurf erstellen
          </Link>
        </div>
      </div>

      <div className="stat-grid">
        <div className="stat-card">
          <div className="value">{data.total_animals}</div>
          <div className="label">Aktive Tiere</div>
        </div>
        <div className="stat-card">
          <div className="value">{data.total_boxes}</div>
          <div className="label">Boxen</div>
        </div>
        <div className="stat-card">
          <div className="value">{data.free_box_capacity}</div>
          <div className="label">Freie Kapazität</div>
        </div>
      </div>

      <div className="section">
        <h2>Zuchtbestand</h2>
        <div className="stat-grid" style={{ marginBottom: 10 }}>
          {(["breeding", "young", "external"] as const).map((cat) => (
            <div className={`stat-card accent-${cat}`} key={cat}>
              <div className="value">{data.animals_by_category[cat] ?? 0}</div>
              <div className="label">{CATEGORY_LABELS[cat]}</div>
            </div>
          ))}
        </div>
        {categoryTotal > 0 && (
          <div className="composition-bar">
            {(["breeding", "young", "external"] as const).map((cat) => {
              const count = data.animals_by_category[cat] ?? 0;
              if (count === 0) return null;
              return (
                <div
                  key={cat}
                  className={`composition-bar-segment accent-${cat}`}
                  style={{ width: `${(count / categoryTotal) * 100}%` }}
                  title={`${CATEGORY_LABELS[cat]}: ${count}`}
                />
              );
            })}
          </div>
        )}
      </div>

      <div className="dashboard-grid">
        <div className="section card">
          <h2>Tiere je Rasse</h2>
          <div className="bar-list">
            {data.animals_by_breed.map((b) => (
              <div className="bar-row" key={b.breed_name}>
                <span className="bar-row-label">{b.breed_name}</span>
                <div className="bar-row-track">
                  <div className="bar-row-fill" style={{ width: `${(b.count / maxBreedCount) * 100}%` }} />
                </div>
                <strong>{b.count}</strong>
              </div>
            ))}
            {data.animals_by_breed.length === 0 && <p className="empty-state">Keine Rassenzuordnung vorhanden.</p>}
          </div>
        </div>

        <div className="section card">
          <div style={{ display: "flex", justifyContent: "space-between", alignItems: "baseline" }}>
            <h2>Jahresvergleich</h2>
            <Link className="hint" to="/statistik">
              Alle Jahre &amp; Rassen →
            </Link>
          </div>
          {yearlyChartData.length > 0 ? (
            <div style={{ height: 160 }}>
              <ResponsiveContainer width="100%" height="100%">
                <LineChart data={yearlyChartData}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis dataKey="year" tick={{ fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} width={36} />
                  <Tooltip />
                  <Line type="monotone" dataKey="points" name="Ø Punkte" stroke="#4338ca" strokeWidth={2} dot={{ r: 3 }} />
                </LineChart>
              </ResponsiveContainer>
            </div>
          ) : (
            !yearlyEvaluations.loading && <p className="empty-state">Noch keine Bewertungsdaten.</p>
          )}
        </div>
      </div>

      <div className="section card">
        <h2>Letzte Aktivität</h2>
        <div className="activity-list">
          {activity.map((item) => (
            <Link className="activity-item" to={`/tiere/${item.animalId}`} key={item.id}>
              <span className="activity-icon">
                {item.icon === "weight" ? <ScaleIcon size={16} /> : <ClipboardCheckIcon size={16} />}
              </span>
              <span className="activity-body">
                <span className="activity-label">{item.label}</span>
                <span className="activity-date">{item.date}</span>
              </span>
              <strong>{item.value}</strong>
            </Link>
          ))}
          {activity.length === 0 && <p className="empty-state">Noch keine Gewichte oder Bewertungen erfasst.</p>}
        </div>
      </div>
    </div>
  );
}
