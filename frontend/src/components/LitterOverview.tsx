import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { Area, CartesianGrid, ComposedChart, Line, ResponsiveContainer, Tooltip, XAxis, YAxis } from "recharts";
import { api } from "../api/client";
import { useAsync } from "../hooks/useAsync";
import { descendantsChartData } from "../utils/growth";

const SEX_LABELS: Record<string, string> = {
  male: "♂",
  female: "♀",
  unknown: "?",
};

export function LitterOverview() {
  const litters = useAsync(() => api.litters.list(), []);
  const breeds = useAsync(() => api.breeds.list(), []);
  const [selected, setSelected] = useState<string | null>(null);
  const [expanded, setExpanded] = useState<Set<string>>(new Set());
  const [breedFilter, setBreedFilter] = useState("");
  const [editing, setEditing] = useState<string | null>(null);
  const [editError, setEditError] = useState<string | null>(null);
  const [editSaving, setEditSaving] = useState(false);
  const [editName, setEditName] = useState("");
  const [editBirthDate, setEditBirthDate] = useState("");
  const [editMatingDate, setEditMatingDate] = useState("");
  const [editBreedId, setEditBreedId] = useState("");

  function toggleExpand(litterName: string) {
    setExpanded((prev) => {
      const next = new Set(prev);
      if (next.has(litterName)) next.delete(litterName);
      else next.add(litterName);
      return next;
    });
  }

  function startEdit(l: { litter_name: string; birth_date: string | null }) {
    setEditing(l.litter_name);
    setEditError(null);
    setEditName(l.litter_name);
    setEditBirthDate(l.birth_date ?? "");
    setEditMatingDate("");
    setEditBreedId("");
  }

  async function saveEdit(originalName: string) {
    if (!editName.trim()) {
      setEditError("Wurfname darf nicht leer sein.");
      return;
    }
    setEditSaving(true);
    setEditError(null);
    try {
      await api.litters.update(originalName, {
        new_litter_name: editName.trim() !== originalName ? editName.trim() : undefined,
        birth_date: editBirthDate || undefined,
        mating_date: editMatingDate || undefined,
        breed_id: editBreedId || undefined,
      });
      setEditing(null);
      setSelected(null);
      setExpanded(new Set());
      await litters.reload();
    } catch (err) {
      setEditError((err as Error).message);
    } finally {
      setEditSaving(false);
    }
  }

  const breedOptions = useMemo(() => {
    const names = new Set<string>();
    for (const l of litters.data ?? []) if (l.breed_name) names.add(l.breed_name);
    return Array.from(names).sort();
  }, [litters.data]);

  const filteredLitters = useMemo(
    () => (breedFilter ? (litters.data ?? []).filter((l) => l.breed_name === breedFilter) : litters.data ?? []),
    [litters.data, breedFilter],
  );

  if (litters.loading) return <p>Lade Würfe…</p>;
  if (litters.error) return <div className="error-banner">{litters.error}</div>;
  if (litters.data && litters.data.length === 0) {
    return (
      <p className="empty-state">
        Noch keine benannten Würfe. Vergib beim Erstellen eines Wurfs (oder nachträglich am Tier) einen
        Wurfnamen, damit er hier auftaucht.
      </p>
    );
  }

  return (
    <div>
      {breedOptions.length > 1 && (
        <div className="toolbar">
          <select value={breedFilter} onChange={(e) => setBreedFilter(e.target.value)} style={{ flex: 1 }}>
            <option value="">Alle Rassen</option>
            {breedOptions.map((name) => (
              <option key={name} value={name}>
                {name}
              </option>
            ))}
          </select>
        </div>
      )}
      {filteredLitters.length === 0 && (
        <p className="empty-state">Keine Würfe dieser Rasse.</p>
      )}
      <div className="list">
      {filteredLitters.map((l) => (
        <div className="card" key={l.litter_name} style={{ marginBottom: 10 }}>
          <div
            className="list-item"
            style={{ cursor: "pointer" }}
            onClick={() => setSelected((prev) => (prev === l.litter_name ? null : l.litter_name))}
          >
            <div>
              <div className="title">{l.litter_name}</div>
              <div className="subtitle">
                {l.birth_date ? `Wurfdatum ${l.birth_date} · ` : ""}
                {l.breed_name ? `${l.breed_name} · ` : ""}
                {l.animal_count} Tiere
                {l.mother_chip ? ` · Mutter ${l.mother_chip}` : ""}
                {l.father_chip ? ` · Vater ${l.father_chip}` : ""}
                {l.avg_latest_weight_grams != null ? ` · Ø ${l.avg_latest_weight_grams} g` : ""}
                {l.avg_total_score != null ? ` · Ø ${l.avg_total_score} Pkt.` : ""}
              </div>
            </div>
            <div style={{ display: "flex", gap: 6 }}>
              <button
                type="button"
                className="btn secondary small"
                onClick={(e) => {
                  e.stopPropagation();
                  if (editing === l.litter_name) setEditing(null);
                  else startEdit(l);
                }}
              >
                Wurf bearbeiten
              </button>
              <button
                type="button"
                className="btn secondary small"
                onClick={(e) => {
                  e.stopPropagation();
                  toggleExpand(l.litter_name);
                }}
              >
                {expanded.has(l.litter_name) ? "▾ Tiere" : "▸ Tiere"}
              </button>
            </div>
          </div>

          {editing === l.litter_name && (
            <div
              className="form-grid"
              style={{ marginTop: 8, borderTop: "1px solid var(--color-border)", paddingTop: 12 }}
            >
              {editError && (
                <div className="error-banner" style={{ gridColumn: "1 / -1" }}>
                  {editError}
                </div>
              )}
              <div className="field">
                <label htmlFor={`edit-litter-name-${l.litter_name}`}>Wurfname</label>
                <input
                  id={`edit-litter-name-${l.litter_name}`}
                  type="text"
                  value={editName}
                  onChange={(e) => setEditName(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor={`edit-litter-birth-${l.litter_name}`}>Wurfdatum (für alle Tiere)</label>
                <input
                  id={`edit-litter-birth-${l.litter_name}`}
                  type="date"
                  value={editBirthDate}
                  onChange={(e) => setEditBirthDate(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor={`edit-litter-mating-${l.litter_name}`}>Deckdatum (Mutter)</label>
                <input
                  id={`edit-litter-mating-${l.litter_name}`}
                  type="date"
                  value={editMatingDate}
                  onChange={(e) => setEditMatingDate(e.target.value)}
                />
              </div>
              <div className="field">
                <label htmlFor={`edit-litter-breed-${l.litter_name}`}>Rasse (für alle Tiere)</label>
                <select
                  id={`edit-litter-breed-${l.litter_name}`}
                  value={editBreedId}
                  onChange={(e) => setEditBreedId(e.target.value)}
                >
                  <option value="">– unverändert –</option>
                  {breeds.data?.map((b) => (
                    <option key={b.id} value={b.id}>
                      {b.name}
                    </option>
                  ))}
                </select>
              </div>
              <div style={{ gridColumn: "1 / -1", display: "flex", gap: 8 }}>
                <button
                  type="button"
                  className="btn"
                  onClick={() => saveEdit(l.litter_name)}
                  disabled={editSaving}
                >
                  {editSaving ? "Speichere…" : "Speichern"}
                </button>
                <button
                  type="button"
                  className="btn secondary"
                  onClick={() => setEditing(null)}
                  disabled={editSaving}
                >
                  Abbrechen
                </button>
              </div>
            </div>
          )}

          {expanded.has(l.litter_name) && <LitterAnimalsPanel litterName={l.litter_name} />}
          {selected === l.litter_name && <LitterStatsPanel litterName={l.litter_name} />}
        </div>
      ))}
      </div>
    </div>
  );
}

function LitterAnimalsPanel({ litterName }: { litterName: string }) {
  const animals = useAsync(() => api.litters.animals(litterName), [litterName]);
  return (
    <div className="list" style={{ marginTop: 8 }}>
      {animals.loading && <p className="hint">Lade Tiere…</p>}
      {animals.data?.map((a) => (
        <Link className="list-item" to={`/tiere/${a.id}`} key={a.id}>
          <span>
            {a.chip_number} {a.name ? `· ${a.name}` : ""}
          </span>
          <span className="subtitle">
            {SEX_LABELS[a.sex]}
            {a.latest_weight_grams ? ` · ${a.latest_weight_grams} g` : ""}
          </span>
        </Link>
      ))}
    </div>
  );
}

function LitterStatsPanel({ litterName }: { litterName: string }) {
  const stats = useAsync(() => api.litters.stats(litterName), [litterName]);
  if (stats.loading) return <p className="hint">Lade Statistik…</p>;
  if (!stats.data) return null;

  const chartData = descendantsChartData(stats.data.weight_curve);

  return (
    <div className="section" style={{ marginTop: 12, borderTop: "1px solid var(--color-border)", paddingTop: 12 }}>
      <h3>Gewichtskurve des Wurfes</h3>
      {chartData.length > 1 ? (
        <div style={{ height: 200 }}>
          <ResponsiveContainer width="100%" height="100%">
            <ComposedChart data={chartData}>
              <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
              <XAxis
                dataKey="age"
                tick={{ fontSize: 11 }}
                label={{ value: "Wochen", position: "insideBottom", offset: -2, fontSize: 11 }}
              />
              <YAxis tick={{ fontSize: 11 }} width={50} />
              <Tooltip />
              <Area type="monotone" dataKey="max" stroke="none" fill="#4338ca" fillOpacity={0.1} />
              <Area type="monotone" dataKey="min" stroke="none" fill="#ffffff" fillOpacity={1} />
              <Line type="monotone" dataKey="mean" name="Durchschnitt" stroke="#4338ca" strokeWidth={2} dot={{ r: 2 }} />
            </ComposedChart>
          </ResponsiveContainer>
        </div>
      ) : (
        <p className="empty-state">Noch nicht genug Gewichtsdaten für eine Kurve.</p>
      )}

      <h3 style={{ marginTop: 16 }}>
        Durchschnittsbewertung je Position ({stats.data.evaluation_count} Bewertungen
        {stats.data.avg_total_score != null ? ` · Ø Gesamt ${stats.data.avg_total_score}` : ""})
      </h3>
      {stats.data.score_positions.length > 0 ? (
        <table>
          <thead>
            <tr>
              <th>Position</th>
              <th>Ø Punkte</th>
              <th>Karten</th>
            </tr>
          </thead>
          <tbody>
            {stats.data.score_positions.map((p) => (
              <tr key={p.position_number}>
                <td>
                  {p.position_number}. {p.category_label}
                </td>
                <td>
                  {p.avg_points} / {p.max_points}
                </td>
                <td>{p.sample_count}</td>
              </tr>
            ))}
          </tbody>
        </table>
      ) : (
        <p className="empty-state">Noch keine Bewertungen für Tiere aus diesem Wurf.</p>
      )}
    </div>
  );
}
