import { useState } from "react";
import { LineChart, Line, XAxis, YAxis, CartesianGrid, Tooltip, ResponsiveContainer } from "recharts";
import { api } from "../api/client";
import { useAsync } from "../hooks/useAsync";
import type { Breed, BreedGroup, BreedGrowthPoint } from "../api/types";

const GROUP_LABELS: Record<BreedGroup, string> = {
  dwarf: "Zwergrassen",
  small: "Kleine Rassen",
  medium: "Mittlere Rassen",
  large: "Grosse Rassen",
};

const GROUP_ORDER: BreedGroup[] = ["dwarf", "small", "medium", "large"];

function weightRange(b: Breed): string {
  const parts: string[] = [];
  if (b.min_weight_kg) parts.push(`Mind. ${b.min_weight_kg} kg`);
  if (b.ideal_weight_min_kg && b.ideal_weight_max_kg) {
    parts.push(`Ideal ${b.ideal_weight_min_kg}–${b.ideal_weight_max_kg} kg`);
  }
  if (b.max_weight_kg) parts.push(`Max. ${b.max_weight_kg} kg`);
  return parts.join(" · ");
}

function GrowthCurveSection({ breed }: { breed: Breed }) {
  const growth = useAsync(() => api.breeds.growthCurve(breed.id), [breed.id]);
  const [points, setPoints] = useState<BreedGrowthPoint[]>([]);
  const [editing, setEditing] = useState(false);
  const [saving, setSaving] = useState(false);
  const [saveError, setSaveError] = useState<string | null>(null);

  function startEditing() {
    setPoints(growth.data?.custom_points.length ? growth.data.custom_points : [{ age_weeks: 8, weight_grams: 1000 }]);
    setEditing(true);
  }

  function updatePoint(i: number, field: "age_weeks" | "weight_grams", value: number) {
    setPoints((prev) => prev.map((p, idx) => (idx === i ? { ...p, [field]: value } : p)));
  }

  function addPoint() {
    setPoints((prev) => [...prev, { age_weeks: 0, weight_grams: 0 }]);
  }

  function removePoint(i: number) {
    setPoints((prev) => prev.filter((_, idx) => idx !== i));
  }

  async function save() {
    setSaving(true);
    setSaveError(null);
    try {
      await api.breeds.replaceGrowthCurve(
        breed.id,
        [...points].sort((a, b) => a.age_weeks - b.age_weeks),
      );
      setEditing(false);
      growth.reload();
    } catch (err) {
      setSaveError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  if (growth.loading) return <p className="hint">Lade Wachstumskurve…</p>;
  if (!growth.data) return null;

  return (
    <div style={{ marginTop: 10 }}>
      <div style={{ height: 160 }}>
        <ResponsiveContainer width="100%" height="100%">
          <LineChart data={growth.data.curve}>
            <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
            <XAxis dataKey="age_weeks" tick={{ fontSize: 10 }} />
            <YAxis tick={{ fontSize: 10 }} width={45} />
            <Tooltip />
            <Line type="monotone" dataKey="weight_grams" stroke="#4338ca" strokeWidth={2} dot={false} />
          </LineChart>
        </ResponsiveContainer>
      </div>
      <p className="hint">
        {growth.data.source === "custom"
          ? "Basierend auf eigenen Stützpunkten (unten editierbar)."
          : "Generische Schätzkurve (Gompertz) — noch keine eigenen Stützpunkte hinterlegt."}
      </p>

      {!editing ? (
        <button className="btn secondary small" onClick={startEditing}>
          Stützpunkte bearbeiten
        </button>
      ) : (
        <div>
          {saveError && <div className="error-banner">{saveError}</div>}
          {points.map((p, i) => (
            <div className="toolbar" key={i} style={{ marginBottom: 6 }}>
              <input
                type="number"
                value={p.age_weeks}
                onChange={(e) => updatePoint(i, "age_weeks", Number(e.target.value))}
                placeholder="Wochen"
                style={{ maxWidth: 100 }}
              />
              <input
                type="number"
                value={p.weight_grams}
                onChange={(e) => updatePoint(i, "weight_grams", Number(e.target.value))}
                placeholder="Gramm"
                style={{ maxWidth: 120 }}
              />
              <button className="btn secondary small" onClick={() => removePoint(i)}>
                Entfernen
              </button>
            </div>
          ))}
          <div className="toolbar">
            <button className="btn secondary small" onClick={addPoint}>
              + Stützpunkt
            </button>
            <button className="btn small" onClick={save} disabled={saving}>
              Speichern
            </button>
            <button className="btn secondary small" onClick={() => setEditing(false)}>
              Abbrechen
            </button>
          </div>
        </div>
      )}
    </div>
  );
}

function BreedingSettingsSection({ breed, onSaved }: { breed: Breed; onSaved: () => void }) {
  const [gestationDays, setGestationDays] = useState(breed.gestation_days != null ? String(breed.gestation_days) : "");
  const [lactationWeeks, setLactationWeeks] = useState(
    breed.lactation_weeks != null ? String(breed.lactation_weeks) : "",
  );

  async function save() {
    await api.breeds.update(breed.id, {
      gestation_days: gestationDays ? Number(gestationDays) : null,
      lactation_weeks: lactationWeeks ? Number(lactationWeeks) : null,
    });
    onSaved();
  }

  return (
    <div style={{ marginTop: 10 }}>
      <p className="hint">
        Steuert die automatische Erkennung von Trächtigkeit/Säugezeit bei der Futterberechnung. Ohne
        Angabe gelten Standardwerte (31 Tage Tragzeit, 8 Wochen Säugezeit).
      </p>
      <div className="form-grid">
        <div className="field">
          <label htmlFor={`gestation-${breed.id}`}>Tragzeit (Tage)</label>
          <input
            id={`gestation-${breed.id}`}
            type="number"
            placeholder="31"
            value={gestationDays}
            onChange={(e) => setGestationDays(e.target.value)}
            onBlur={save}
          />
        </div>
        <div className="field">
          <label htmlFor={`lactation-${breed.id}`}>Säugezeit (Wochen)</label>
          <input
            id={`lactation-${breed.id}`}
            type="number"
            placeholder="8"
            value={lactationWeeks}
            onChange={(e) => setLactationWeeks(e.target.value)}
            onBlur={save}
          />
        </div>
      </div>
    </div>
  );
}

function BreedCard({ breed, onSaved }: { breed: Breed; onSaved: () => void }) {
  const [openSection, setOpenSection] = useState<"none" | "scoring" | "growth" | "breeding">("none");
  return (
    <div className="card" style={{ padding: 14 }}>
      <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start", gap: 8 }}>
        <div>
          <div className="title">
            {breed.name} {breed.abbreviation ? <span className="hint">({breed.abbreviation})</span> : null}
          </div>
          <div className="subtitle">{weightRange(breed)}</div>
        </div>
        <div className="toolbar" style={{ marginBottom: 0 }}>
          <button
            className="btn secondary small"
            onClick={() => setOpenSection((s) => (s === "scoring" ? "none" : "scoring"))}
          >
            Bewertungsskala
          </button>
          <button
            className="btn secondary small"
            onClick={() => setOpenSection((s) => (s === "growth" ? "none" : "growth"))}
          >
            Wachstumskurve
          </button>
          <button
            className="btn secondary small"
            onClick={() => setOpenSection((s) => (s === "breeding" ? "none" : "breeding"))}
          >
            Zucht-Einstellungen
          </button>
        </div>
      </div>
      {openSection === "breeding" && <BreedingSettingsSection breed={breed} onSaved={onSaved} />}
      {openSection === "scoring" && (
        <table style={{ marginTop: 10 }}>
          <tbody>
            {breed.scoring_positions.map((p) => (
              <tr key={p.position_number}>
                <th>{p.position_number}. {p.label}</th>
                <td>{p.max_points} Punkte</td>
              </tr>
            ))}
            <tr>
              <th>Total</th>
              <td>
                <strong>{breed.scoring_positions.reduce((s, p) => s + p.max_points, 0)} Punkte</strong>
              </td>
            </tr>
          </tbody>
        </table>
      )}
      {openSection === "growth" && <GrowthCurveSection breed={breed} />}
    </div>
  );
}

export function Breeds() {
  const { data, loading, error, reload } = useAsync(() => api.breeds.list(), []);
  const [name, setName] = useState("");
  const [abbreviation, setAbbreviation] = useState("");
  const [group, setGroup] = useState<BreedGroup>("medium");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [showForm, setShowForm] = useState(false);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim()) return;
    setSubmitting(true);
    setFormError(null);
    try {
      await api.breeds.create({ name: name.trim(), abbreviation: abbreviation.trim() || null, group });
      setName("");
      setAbbreviation("");
      setShowForm(false);
      reload();
    } catch (err) {
      setFormError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  const grouped = GROUP_ORDER.map((g) => ({
    group: g,
    breeds: (data ?? []).filter((b) => b.group === g),
  })).filter((g) => g.breeds.length > 0);
  const ungrouped = (data ?? []).filter((b) => !b.group);

  return (
    <div>
      <h1>Rassen</h1>
      <p className="hint" style={{ marginBottom: 16 }}>
        Nach Standard 2015 (Rassekaninchen Schweiz) — 42 Rassen mit offiziellem Gewicht und
        Bewertungsskala sind bereits hinterlegt. Die Wachstumskurve ist ohne eigene Angaben eine
        generische Schätzung und kann pro Rasse mit echten Stützpunkten überschrieben werden.
      </p>

      <div className="toolbar">
        <button className="btn secondary" onClick={() => setShowForm((s) => !s)}>
          {showForm ? "Abbrechen" : "+ Weitere Rasse anlegen"}
        </button>
      </div>

      {showForm && (
        <form className="card section" onSubmit={handleSubmit}>
          {formError && <div className="error-banner">{formError}</div>}
          <div className="form-grid">
            <div className="field">
              <label htmlFor="breed-name">Name</label>
              <input id="breed-name" type="text" value={name} onChange={(e) => setName(e.target.value)} required />
            </div>
            <div className="field">
              <label htmlFor="breed-abbr">Kürzel</label>
              <input
                id="breed-abbr"
                type="text"
                value={abbreviation}
                onChange={(e) => setAbbreviation(e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="breed-group">Gruppe</label>
              <select id="breed-group" value={group} onChange={(e) => setGroup(e.target.value as BreedGroup)}>
                {GROUP_ORDER.map((g) => (
                  <option key={g} value={g}>
                    {GROUP_LABELS[g]}
                  </option>
                ))}
              </select>
            </div>
          </div>
          <button className="btn" type="submit" disabled={submitting}>
            Anlegen
          </button>
        </form>
      )}

      {loading && <p>Lade Rassen…</p>}
      {error && <div className="error-banner">{error}</div>}

      {grouped.map(({ group: g, breeds }) => (
        <div className="section" key={g}>
          <h3>{GROUP_LABELS[g]}</h3>
          <div className="list">
            {breeds.map((b) => (
              <BreedCard breed={b} onSaved={reload} key={b.id} />
            ))}
          </div>
        </div>
      ))}
      {ungrouped.length > 0 && (
        <div className="section">
          <h3>Ohne Gruppe</h3>
          <div className="list">
            {ungrouped.map((b) => (
              <BreedCard breed={b} onSaved={reload} key={b.id} />
            ))}
          </div>
        </div>
      )}
    </div>
  );
}
