import { useState } from "react";
import { Link, useParams } from "react-router-dom";
import { api } from "../api/client";
import { useAsync } from "../hooks/useAsync";
import { coiLabel, coiRiskClass } from "../utils/inbreeding";

export function MatingSuggestions() {
  const { id: routeId } = useParams<{ id: string }>();
  if (!routeId) return null;
  const id: string = routeId;

  const animal = useAsync(() => api.animals.get(id), [id]);

  const [weightTotal, setWeightTotal] = useState(1);
  const [weightInbreeding, setWeightInbreeding] = useState(1);
  const [weightComplement, setWeightComplement] = useState(1);
  const [weightFocus, setWeightFocus] = useState(1);
  const [focusCategories, setFocusCategories] = useState<string[]>([]);

  const suggestions = useAsync(
    () =>
      api.animals.matingSuggestions(
        id,
        { total: weightTotal, inbreeding: weightInbreeding, complement: weightComplement, focus: weightFocus },
        focusCategories,
      ),
    [id, weightTotal, weightInbreeding, weightComplement, weightFocus, focusCategories.join(",")],
  );

  const availablePositions = animal.data?.breed?.scoring_positions ?? [];

  function toggleFocus(label: string) {
    setFocusCategories((prev) => (prev.includes(label) ? prev.filter((c) => c !== label) : [...prev, label]));
  }

  return (
    <div>
      <Link className="back-link" to={`/tiere/${id}`}>
        ← Zurück zum Tier
      </Link>
      <h1>Paarungsvorschläge{animal.data ? ` für ${animal.data.chip_number}` : ""}</h1>
      <p className="hint" style={{ marginBottom: 16 }}>
        Heuristische Rangliste aus letzter Bewertung, Inzuchtkoeffizient der Nachkommen, ergänzenden
        Stärken/Schwächen und optional gezielt gewählten Bewertungspositionen — kein genetisches
        Zuchtwertmodell, sondern eine Diskussionsgrundlage. Gewichtung nach Belieben anpassen.
      </p>

      <div className="card section">
        <div className="form-grid">
          <div className="field">
            <label htmlFor="w-total">Gewicht: Gesamtpunktzahl ({weightTotal})</label>
            <input
              id="w-total"
              type="range"
              min={0}
              max={3}
              step={0.5}
              value={weightTotal}
              onChange={(e) => setWeightTotal(Number(e.target.value))}
            />
          </div>
          <div className="field">
            <label htmlFor="w-inbreeding">Gewicht: Geringer Inzuchtkoeffizient ({weightInbreeding})</label>
            <input
              id="w-inbreeding"
              type="range"
              min={0}
              max={3}
              step={0.5}
              value={weightInbreeding}
              onChange={(e) => setWeightInbreeding(Number(e.target.value))}
            />
          </div>
          <div className="field">
            <label htmlFor="w-complement">Gewicht: Ergänzende Stärken ({weightComplement})</label>
            <input
              id="w-complement"
              type="range"
              min={0}
              max={3}
              step={0.5}
              value={weightComplement}
              onChange={(e) => setWeightComplement(Number(e.target.value))}
            />
          </div>
          <div className="field">
            <label htmlFor="w-focus">Gewicht: Fokus-Positionen ({weightFocus})</label>
            <input
              id="w-focus"
              type="range"
              min={0}
              max={3}
              step={0.5}
              value={weightFocus}
              onChange={(e) => setWeightFocus(Number(e.target.value))}
              disabled={focusCategories.length === 0}
            />
          </div>
        </div>

        <h3 style={{ marginTop: 16 }}>Fokus-Positionen (optional)</h3>
        <p className="hint" style={{ marginBottom: 8 }}>
          Einzelne Bewertungspositionen der Rasse auswählen, auf die die Rangliste besonders Wert
          legen soll (z.B. nur Farbe und Glanz) — unabhängig davon, wie dein Tier dort selbst steht.
        </p>
        {availablePositions.length === 0 ? (
          <p className="hint">Dem Tier ist keine Rasse mit Bewertungsskala zugeordnet.</p>
        ) : (
          <div className="toolbar" style={{ flexWrap: "wrap" }}>
            {availablePositions.map((p) => (
              <label
                key={p.position_number}
                className="badge"
                style={{
                  cursor: "pointer",
                  background: focusCategories.includes(p.label) ? "var(--color-primary)" : undefined,
                  color: focusCategories.includes(p.label) ? "white" : undefined,
                }}
              >
                <input
                  type="checkbox"
                  checked={focusCategories.includes(p.label)}
                  onChange={() => toggleFocus(p.label)}
                  style={{ display: "none" }}
                />
                {p.label}
              </label>
            ))}
          </div>
        )}
      </div>

      {suggestions.loading && <p>Berechne Vorschläge…</p>}
      {suggestions.error && <div className="error-banner">{suggestions.error}</div>}

      <div className="list">
        {suggestions.data?.map((s, i) => (
          <div className="card" key={s.animal.id}>
            <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
              <div>
                <div className="title">
                  #{i + 1} · <Link to={`/tiere/${s.animal.id}`}>{s.animal.chip_number}</Link>{" "}
                  {s.animal.name ? `· ${s.animal.name}` : ""}
                </div>
                <div className="subtitle">{s.animal.breed?.name ?? ""}</div>
                <ul style={{ margin: "8px 0 0", paddingLeft: 18, fontSize: "0.85rem" }}>
                  {s.reasons.map((r, ri) => (
                    <li key={ri}>{r}</li>
                  ))}
                </ul>
              </div>
              <div style={{ textAlign: "right" }}>
                <span className={`badge ${coiRiskClass(s.inbreeding_coefficient)}`}>
                  {coiLabel(s.inbreeding_coefficient)}
                </span>
                <div className="hint" style={{ marginTop: 4 }}>
                  Score {(s.final_score * 100).toFixed(0)}
                </div>
              </div>
            </div>
          </div>
        ))}
        {suggestions.data && suggestions.data.length === 0 && (
          <p className="empty-state">Keine passenden aktiven Tiere mit anderem Geschlecht gefunden.</p>
        )}
      </div>
    </div>
  );
}
