import { useRef, useState } from "react";
import { useNavigate, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { useAsync } from "../hooks/useAsync";
import type { ScanResult, ScannedScore } from "../api/types";

export function ScanEvaluationCard() {
  const navigate = useNavigate();
  const [searchParams] = useSearchParams();
  const preselectedAnimalId = searchParams.get("animal") ?? "";
  const fileInputRef = useRef<HTMLInputElement>(null);
  const animals = useAsync(() => api.animals.list(), []);

  const [uploading, setUploading] = useState(false);
  const [uploadError, setUploadError] = useState<string | null>(null);
  const [result, setResult] = useState<ScanResult | null>(null);

  const [animalId, setAnimalId] = useState("");
  const selectedAnimal = useAsync(
    () => (animalId ? api.animals.get(animalId) : Promise.resolve(null)),
    [animalId],
  );
  const [evaluatedOn, setEvaluatedOn] = useState(() => new Date().toISOString().slice(0, 10));
  const [showName, setShowName] = useState("");
  const [exhibitorNumber, setExhibitorNumber] = useState("");
  const [exhibitorName, setExhibitorName] = useState("");
  const [exhibitorAddress, setExhibitorAddress] = useState("");
  const [weightGrams, setWeightGrams] = useState("");
  const [scores, setScores] = useState<ScannedScore[]>([]);
  const [totalScore, setTotalScore] = useState("");
  const [notes, setNotes] = useState("");
  const [saveError, setSaveError] = useState<string | null>(null);
  const [saving, setSaving] = useState(false);

  async function handleFileSelected(e: React.ChangeEvent<HTMLInputElement>) {
    const file = e.target.files?.[0];
    if (!file) return;
    setUploading(true);
    setUploadError(null);
    setResult(null);
    try {
      const res = await api.scan.evaluationCard(file);
      setResult(res);
      setAnimalId(res.matched_animal?.id ?? preselectedAnimalId);
      setShowName(res.show_name ?? "");
      setExhibitorNumber(res.exhibitor_number ?? "");
      setExhibitorName(res.exhibitor_name ?? "");
      setExhibitorAddress(res.exhibitor_address ?? "");
      setWeightGrams(res.weight_grams ? String(res.weight_grams) : "");
      setScores(res.scores);
      setTotalScore(res.total_score != null ? String(res.total_score) : "");
      setNotes(res.notes ?? "");
    } catch (err) {
      setUploadError((err as Error).message);
    } finally {
      setUploading(false);
      if (fileInputRef.current) fileInputRef.current.value = "";
    }
  }

  function updateScore(i: number, field: "category_label" | "points", value: string) {
    setScores((prev) =>
      prev.map((s, idx) =>
        idx === i ? { ...s, [field]: field === "points" ? (value === "" ? null : Number(value)) : value } : s,
      ),
    );
  }

  function addScoreRow() {
    setScores((prev) => [...prev, { category_label: "", points: null }]);
  }

  function removeScoreRow(i: number) {
    setScores((prev) => prev.filter((_, idx) => idx !== i));
  }

  function maxPointsFor(index: number, categoryLabel: string): number {
    const positions = selectedAnimal.data?.breed?.scoring_positions ?? [];
    // Erst per Reihenfolge matchen (Scan liest meist in Kartenreihenfolge
    // ein, wie die Rassen-Bewertungsskala auch hinterlegt ist), sonst per
    // Bezeichnung, sonst Richtwert 10 (statt pauschal falsch 20).
    if (positions[index]) return positions[index].max_points;
    const byLabel = positions.find((p) => p.label.toLowerCase() === categoryLabel.trim().toLowerCase());
    return byLabel?.max_points ?? 10;
  }

  async function handleSave(e: React.FormEvent) {
    e.preventDefault();
    if (!result || !animalId) return;
    setSaving(true);
    setSaveError(null);
    try {
      await api.evaluations.create(animalId, {
        evaluated_on: evaluatedOn,
        show_name: showName.trim() || null,
        exhibitor_number: exhibitorNumber.trim() || null,
        exhibitor_name: exhibitorName.trim() || null,
        exhibitor_address: exhibitorAddress.trim() || null,
        weight_grams: weightGrams ? Number(weightGrams) : null,
        total_score: totalScore ? Number(totalScore) : null,
        notes: notes.trim() || null,
        scores: scores
          .map((s, i) => ({ s, i }))
          .filter(({ s }) => s.category_label.trim())
          .map(({ s, i }) => ({
            position_number: i + 1,
            category_label: s.category_label,
            max_points: maxPointsFor(i, s.category_label),
            points: s.points ?? 0,
          })),
        source: "scan",
      });
      navigate(`/tiere/${animalId}`);
    } catch (err) {
      setSaveError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div>
      <h1>Bewertungskarte scannen</h1>
      <p className="hint" style={{ marginBottom: 16 }}>
        Foto der Bewertungskarte aufnehmen oder hochladen. Claude liest die Felder aus — bitte danach
        prüfen und korrigieren, bevor du speicherst. Nichts wird automatisch übernommen.
      </p>

      <div className="card section">
        <input
          ref={fileInputRef}
          type="file"
          accept="image/jpeg,image/png,image/webp,image/heic"
          capture="environment"
          onChange={handleFileSelected}
          disabled={uploading}
        />
        {uploading && <p style={{ marginTop: 12 }}>Lese Bewertungskarte…</p>}
        {uploadError && <div className="error-banner">{uploadError}</div>}
      </div>

      {result && (
        <form className="card section" onSubmit={handleSave}>
          <div style={{ display: "flex", gap: 16, flexWrap: "wrap" }}>
            <img
              src={result.photo_data_uri}
              alt="Bewertungskarte"
              style={{ maxWidth: 220, borderRadius: 8, border: "1px solid var(--color-border)" }}
            />
            <div style={{ flex: 1, minWidth: 240 }}>
              {saveError && <div className="error-banner">{saveError}</div>}
              <div className="field">
                <label htmlFor="scan-animal">Tier *</label>
                <select id="scan-animal" value={animalId} onChange={(e) => setAnimalId(e.target.value)} required>
                  <option value="">
                    {result.matched_animal ? "– auswählen –" : "Kein Tier automatisch erkannt – bitte wählen"}
                  </option>
                  {animals.data?.map((a) => (
                    <option key={a.id} value={a.id}>
                      {a.chip_number} {a.name ? `· ${a.name}` : ""}
                    </option>
                  ))}
                </select>
                {result.identification_number && !result.matched_animal && result.candidate_animals.length === 0 && (
                  <p className="hint">
                    Erkannte Chip-/Ohrmarken-Nummer "{result.identification_number}" konnte keinem Tier
                    zugeordnet werden.
                  </p>
                )}
                {result.candidate_animals.length > 1 && (
                  <p className="hint">
                    "{result.identification_number}" passt auf die Endziffern von{" "}
                    {result.candidate_animals.length} Tieren — bitte das richtige auswählen:{" "}
                    {result.candidate_animals.map((c) => `${c.chip_number}${c.name ? ` (${c.name})` : ""}`).join(", ")}
                  </p>
                )}
                {result.breed_name && <p className="hint">Erkannte Rasse: {result.breed_name}</p>}
                {result.sex && <p className="hint">Erkanntes Geschlecht: {result.sex}</p>}
              </div>
              <div className="form-grid">
                <div className="field">
                  <label htmlFor="scan-date">Datum</label>
                  <input
                    id="scan-date"
                    type="date"
                    value={evaluatedOn}
                    onChange={(e) => setEvaluatedOn(e.target.value)}
                  />
                </div>
                <div className="field">
                  <label htmlFor="scan-show">Ausstellung</label>
                  <input id="scan-show" type="text" value={showName} onChange={(e) => setShowName(e.target.value)} />
                </div>
                <div className="field">
                  <label htmlFor="scan-weight">Gewicht (g)</label>
                  <input
                    id="scan-weight"
                    type="number"
                    value={weightGrams}
                    onChange={(e) => setWeightGrams(e.target.value)}
                  />
                </div>
                <div className="field">
                  <label htmlFor="scan-total">Gesamtpunktzahl</label>
                  <input
                    id="scan-total"
                    type="number"
                    step="0.5"
                    value={totalScore}
                    onChange={(e) => setTotalScore(e.target.value)}
                  />
                </div>
              </div>
            </div>
          </div>

          <div className="form-grid" style={{ marginTop: 12 }}>
            <div className="field">
              <label htmlFor="scan-exh-nr">Ausstellernummer</label>
              <input
                id="scan-exh-nr"
                type="text"
                value={exhibitorNumber}
                onChange={(e) => setExhibitorNumber(e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="scan-exh-name">Ausstellername</label>
              <input
                id="scan-exh-name"
                type="text"
                value={exhibitorName}
                onChange={(e) => setExhibitorName(e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="scan-exh-addr">Ausstelleradresse</label>
              <input
                id="scan-exh-addr"
                type="text"
                value={exhibitorAddress}
                onChange={(e) => setExhibitorAddress(e.target.value)}
              />
            </div>
          </div>

          <h3 style={{ marginTop: 16 }}>Bewertungspositionen (erkannt)</h3>
          <div className="list">
            {scores.map((s, i) => (
              <div className="toolbar" key={i} style={{ marginBottom: 4 }}>
                <input
                  type="text"
                  value={s.category_label}
                  onChange={(e) => updateScore(i, "category_label", e.target.value)}
                  placeholder="Position"
                  style={{ flex: 2 }}
                />
                <input
                  type="number"
                  step="0.5"
                  value={s.points ?? ""}
                  onChange={(e) => updateScore(i, "points", e.target.value)}
                  placeholder="Punkte"
                  style={{ maxWidth: 100 }}
                />
                <span className="hint" style={{ whiteSpace: "nowrap" }}>
                  / {maxPointsFor(i, s.category_label)}
                </span>
                <button type="button" className="btn secondary small" onClick={() => removeScoreRow(i)}>
                  Entfernen
                </button>
              </div>
            ))}
            <button type="button" className="btn secondary small" onClick={addScoreRow}>
              + Position
            </button>
          </div>

          {result.notes && (
            <div className="field" style={{ marginTop: 12 }}>
              <label htmlFor="scan-notes">Notizen (von Claude erkannt)</label>
              <textarea id="scan-notes" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
            </div>
          )}

          <button className="btn" type="submit" disabled={saving || !animalId} style={{ marginTop: 16 }}>
            Bestätigen & speichern
          </button>
        </form>
      )}
    </div>
  );
}
