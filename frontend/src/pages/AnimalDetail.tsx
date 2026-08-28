import { useEffect, useState } from "react";
import { Link, useNavigate, useParams } from "react-router-dom";
import {
  Area,
  CartesianGrid,
  Line,
  ComposedChart,
  LineChart,
  PolarAngleAxis,
  PolarGrid,
  PolarRadiusAxis,
  Radar,
  RadarChart,
  ResponsiveContainer,
  Tooltip,
  XAxis,
  YAxis,
} from "recharts";
import { api, BASE_URL } from "../api/client";
import { useAsync } from "../hooks/useAsync";
import type { EvaluationScore, FeedingPhase } from "../api/types";
import { EXCLUSION_THRESHOLD, pointOptionsForMaxPoints } from "../utils/scoring";
import { AnimalCombobox } from "../components/AnimalCombobox";
import { PedigreeTree } from "../components/PedigreeTree";
import { coiLabel, coiRiskClass } from "../utils/inbreeding";
import { buildWeightChartData, descendantsChartData, GROWTH_STATUS_LABELS, growthStatusClass } from "../utils/growth";

const STATUS_LABELS: Record<string, string> = {
  active: "Aktiv",
  sold: "Verkauft",
  deceased: "Verstorben",
  retired: "Aus der Zucht",
  slaughtered: "Geschlachtet",
};

const SEX_LABELS: Record<string, string> = {
  male: "♂ Rammler",
  female: "♀ Zibbe",
  unknown: "unbekannt",
};

const CATEGORY_LABELS: Record<string, string> = {
  breeding: "Zuchttier",
  young: "Jungtier",
  external: "Externes Zuchttier",
};

const GROWTH_RATE_LABELS: Record<string, string> = {
  schnell: "schnell",
  mittel: "mittel",
  langsam: "langsam",
};

const FEEDING_PHASE_LABELS: Record<FeedingPhase, string> = {
  maintenance: "Erhaltung",
  growth: "Wachstum",
  over_ideal: "Über Idealgewicht",
  gestation: "Trächtig",
  lactation: "Säugend",
};

export function AnimalDetail() {
  const { id: routeId } = useParams<{ id: string }>();
  const navigate = useNavigate();
  if (!routeId) return null;
  const id: string = routeId;

  const animal = useAsync(() => api.animals.get(id), [id]);
  const weights = useAsync(() => api.weights.list(id), [id]);
  const evaluations = useAsync(() => api.evaluations.list(id), [id]);
  const children = useAsync(() => api.animals.children(id), [id]);
  const feedingPlan = useAsync(
    () => api.animals.feedingPlan(id),
    [
      id,
      animal.data?.feed_id,
      animal.data?.target_weight_grams,
      animal.data?.target_date,
      animal.data?.target_date_end,
      animal.data?.mating_date,
      weights.data?.length,
    ],
  );
  const feeds = useAsync(() => api.feeds.list(), []);
  const breeds = useAsync(() => api.breeds.list(), []);
  const pedigree = useAsync(() => api.animals.pedigree(id, 4), [id]);
  const candidates = useAsync(() => api.animals.list({ status: "active" }), []);
  const growthPlan = useAsync(
    () => api.animals.growthPlan(id),
    [id, animal.data?.birth_date, animal.data?.target_date, animal.data?.target_date_end, weights.data?.length],
  );
  const growthCurve = useAsync(
    () =>
      animal.data?.breed_id ? api.breeds.growthCurve(animal.data.breed_id, animal.data.sex) : Promise.resolve(null),
    [animal.data?.breed_id, animal.data?.sex],
  );
  const siblingsGrowthCurve = useAsync(() => api.animals.siblingsGrowthCurve(id), [id]);
  const [showSiblingsCurve, setShowSiblingsCurve] = useState(true);
  const descendantsGrowth = useAsync(() => api.animals.descendantsGrowth(id), [id]);
  const offspringScores = useAsync(() => api.animals.offspringScores(id), [id]);
  const strengthsWeaknesses = useAsync(
    () => api.animals.strengthsWeaknesses(id),
    [id, evaluations.data?.length],
  );
  const feedPlanYear = useAsync(() => api.animals.feedPlanYear(id), [id, animal.data?.feed_id]);
  const [showFeedPlanYear, setShowFeedPlanYear] = useState(false);

  const [editingStatus, setEditingStatus] = useState(false);
  const [statusValue, setStatusValue] = useState("");
  const [editingCategory, setEditingCategory] = useState(false);
  const [categoryValue, setCategoryValue] = useState("");
  const [deleteError, setDeleteError] = useState<string | null>(null);

  const [editingInfo, setEditingInfo] = useState(false);
  const [infoError, setInfoError] = useState<string | null>(null);
  const [infoSaving, setInfoSaving] = useState(false);
  const [chipNumber, setChipNumber] = useState("");
  const [tattooNumber, setTattooNumber] = useState("");
  const [animalName, setAnimalName] = useState("");
  const [birthDate, setBirthDate] = useState("");
  const [colorVariant, setColorVariant] = useState("");
  const [breedIdEdit, setBreedIdEdit] = useState("");
  const [litterNameEdit, setLitterNameEdit] = useState("");
  const [motherIdEdit, setMotherIdEdit] = useState("");
  const [fatherIdEdit, setFatherIdEdit] = useState("");
  const [notesEdit, setNotesEdit] = useState("");

  const [targetWeight, setTargetWeight] = useState("");
  const [targetDate, setTargetDate] = useState("");
  const [targetDateEnd, setTargetDateEnd] = useState("");
  const [matingDate, setMatingDate] = useState("");

  const [pairingCandidateId, setPairingCandidateId] = useState("");
  const [pairingResult, setPairingResult] = useState<{ inbreeding_coefficient: number; risk_level: string } | null>(
    null,
  );
  const [pairingError, setPairingError] = useState<string | null>(null);

  const [weightDate, setWeightDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [weightGrams, setWeightGrams] = useState("");
  const [weightError, setWeightError] = useState<string | null>(null);

  const [showEvalForm, setShowEvalForm] = useState(false);
  const [evalDate, setEvalDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [showName, setShowName] = useState("");
  const [scores, setScores] = useState<EvaluationScore[]>([]);
  const [evalWeight, setEvalWeight] = useState("");
  const [evalError, setEvalError] = useState<string | null>(null);
  const [selectedEvalId, setSelectedEvalId] = useState<string>("");

  useEffect(() => {
    if (animal.data) {
      setTargetWeight(animal.data.target_weight_grams ? String(animal.data.target_weight_grams) : "");
      setTargetDate(animal.data.target_date ?? "");
      setTargetDateEnd(animal.data.target_date_end ?? "");
      setMatingDate(animal.data.mating_date ?? "");
    }
  }, [animal.data?.target_weight_grams, animal.data?.target_date, animal.data?.target_date_end, animal.data?.mating_date]);

  useEffect(() => {
    if (animal.data?.breed) {
      setScores(
        animal.data.breed.scoring_positions.map((p) => ({
          position_number: p.position_number,
          category_label: p.label,
          max_points: p.max_points,
          points: p.max_points,
        })),
      );
    }
  }, [animal.data?.breed]);

  async function handleDeleteAnimal() {
    if (!confirm("Dieses Tier wirklich löschen? Alle Gewichte und Bewertungen gehen verloren.")) return;
    setDeleteError(null);
    try {
      await api.animals.remove(id);
      navigate("/tiere");
    } catch (err) {
      setDeleteError((err as Error).message);
    }
  }

  async function handleStatusChange(newStatus: string) {
    await api.animals.update(id, { status: newStatus });
    animal.reload();
    setEditingStatus(false);
  }

  async function handleCategoryChange(newCategory: string) {
    await api.animals.update(id, { category: newCategory });
    animal.reload();
    setEditingCategory(false);
  }

  function handleStartEditInfo() {
    setChipNumber(a.chip_number);
    setTattooNumber(a.tattoo_number ?? "");
    setAnimalName(a.name ?? "");
    setBirthDate(a.birth_date ?? "");
    setColorVariant(a.color_variant ?? "");
    setBreedIdEdit(a.breed_id ?? "");
    setLitterNameEdit(a.litter_name ?? "");
    setMotherIdEdit(a.mother_id ?? "");
    setFatherIdEdit(a.father_id ?? "");
    setNotesEdit(a.notes ?? "");
    setInfoError(null);
    setEditingInfo(true);
  }

  async function handleInfoSave() {
    if (!chipNumber.trim()) {
      setInfoError("Chip-Nummer darf nicht leer sein.");
      return;
    }
    setInfoSaving(true);
    setInfoError(null);
    try {
      await api.animals.update(id, {
        chip_number: chipNumber.trim(),
        tattoo_number: tattooNumber.trim() || null,
        name: animalName.trim() || null,
        birth_date: birthDate || null,
        color_variant: colorVariant.trim() || null,
        breed_id: breedIdEdit || null,
        litter_name: litterNameEdit.trim() || null,
        mother_id: motherIdEdit || null,
        father_id: fatherIdEdit || null,
        notes: notesEdit.trim() || null,
      });
      animal.reload();
      setEditingInfo(false);
    } catch (err) {
      setInfoError((err as Error).message);
    } finally {
      setInfoSaving(false);
    }
  }

  async function handleMatingDateSave() {
    await api.animals.update(id, { mating_date: matingDate || null });
    animal.reload();
    feedingPlan.reload();
  }

  async function handleFeedChange(feedId: string) {
    await api.animals.update(id, { feed_id: feedId || null });
    animal.reload();
    feedingPlan.reload();
  }

  async function handleTargetSave() {
    await api.animals.update(id, {
      target_weight_grams: targetWeight ? Number(targetWeight) : null,
      target_date: targetDate || null,
      target_date_end: targetDateEnd || null,
    });
    animal.reload();
    feedingPlan.reload();
    growthPlan.reload();
  }

  async function handlePairingCheck() {
    if (!pairingCandidateId || !a.sex || a.sex === "unknown") return;
    setPairingError(null);
    setPairingResult(null);
    try {
      const motherId = a.sex === "female" ? id : pairingCandidateId;
      const fatherId = a.sex === "male" ? id : pairingCandidateId;
      const result = await api.animals.pairingCheck(motherId, fatherId);
      setPairingResult(result);
    } catch (err) {
      setPairingError((err as Error).message);
    }
  }

  async function handleAddWeight(e: React.FormEvent) {
    e.preventDefault();
    const grams = Number(weightGrams);
    if (!weightDate || !grams) return;
    setWeightError(null);
    try {
      await api.weights.create(id, { measured_on: weightDate, weight_grams: grams });
      setWeightGrams("");
      weights.reload();
      animal.reload();
      feedingPlan.reload();
    } catch (err) {
      setWeightError((err as Error).message);
    }
  }

  async function handleDeleteWeight(entryId: string) {
    await api.weights.remove(id, entryId);
    weights.reload();
  }

  function updateScore(index: number, points: number) {
    setScores((prev) => prev.map((s, i) => (i === index ? { ...s, points } : s)));
  }

  const scoreTotal = scores.reduce((sum, s) => sum + (s.points || 0), 0);

  async function handleAddEvaluation(e: React.FormEvent) {
    e.preventDefault();
    setEvalError(null);
    try {
      await api.evaluations.create(id, {
        evaluated_on: evalDate,
        show_name: showName.trim() || null,
        total_score: scoreTotal,
        weight_grams: evalWeight ? Number(evalWeight) : null,
        scores,
      });
      setShowEvalForm(false);
      setShowName("");
      setEvalWeight("");
      evaluations.reload();
    } catch (err) {
      setEvalError((err as Error).message);
    }
  }

  async function handleDeleteEvaluation(evaluationId: string) {
    await api.evaluations.remove(id, evaluationId);
    evaluations.reload();
  }

  if (animal.loading) return <p>Lade Tier…</p>;
  if (animal.error) return <div className="error-banner">{animal.error}</div>;
  if (!animal.data) return null;
  const a = animal.data;

  const chartData = buildWeightChartData(
    weights.data ?? [],
    a.birth_date,
    growthCurve.data?.curve ?? null,
    growthPlan.data?.own_trend ?? null,
    siblingsGrowthCurve.data && siblingsGrowthCurve.data.sibling_count >= 1 ? siblingsGrowthCurve.data.points : null,
  );

  return (
    <div>
      <Link className="back-link" to="/tiere">
        ← Zurück zur Übersicht
      </Link>

      <div className="card section">
        <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
          <div>
            <h1 style={{ marginBottom: 4 }}>
              {a.chip_number} {a.name ? `· ${a.name}` : ""}
            </h1>
            <div className="subtitle">
              {SEX_LABELS[a.sex]} {a.breed ? `· ${a.breed.name}` : ""} {a.color_variant ? `· ${a.color_variant}` : ""}
            </div>
          </div>
          <div style={{ display: "flex", flexDirection: "column", gap: 4, alignItems: "flex-end" }}>
            <span className={`badge category-${a.category}`}>{CATEGORY_LABELS[a.category]}</span>
            <span className={`badge status-${a.status}`}>{STATUS_LABELS[a.status]}</span>
          </div>
        </div>

        {!editingInfo ? (
          <table style={{ marginTop: 16 }}>
            <tbody>
              <tr>
                <th>Chip-Nummer</th>
                <td>{a.chip_number}</td>
              </tr>
              {a.tattoo_number && (
                <tr>
                  <th>Tätowierung</th>
                  <td>{a.tattoo_number}</td>
                </tr>
              )}
              <tr>
                <th>Geburtsdatum</th>
                <td>{a.birth_date ?? "–"}</td>
              </tr>
              <tr>
                <th>Box</th>
                <td>{a.cage_box_label ?? "–"}</td>
              </tr>
              <tr>
                <th>Inzuchtkoeffizient</th>
                <td>
                  {a.inbreeding_coefficient != null ? (
                    <span className={`badge ${coiRiskClass(a.inbreeding_coefficient)}`}>
                      {coiLabel(a.inbreeding_coefficient)}
                    </span>
                  ) : (
                    "–"
                  )}
                </td>
              </tr>
              <tr>
                <th>Mutter</th>
                <td>
                  {a.mother ? (
                    <Link to={`/tiere/${a.mother.id}`}>
                      {a.mother.chip_number}
                      {a.mother.name ? ` · ${a.mother.name}` : ""}
                    </Link>
                  ) : (
                    "unbekannt"
                  )}
                </td>
              </tr>
              <tr>
                <th>Vater</th>
                <td>
                  {a.father ? (
                    <Link to={`/tiere/${a.father.id}`}>
                      {a.father.chip_number}
                      {a.father.name ? ` · ${a.father.name}` : ""}
                    </Link>
                  ) : (
                    "unbekannt"
                  )}
                </td>
              </tr>
              {a.notes && (
                <tr>
                  <th>Notizen</th>
                  <td>{a.notes}</td>
                </tr>
              )}
            </tbody>
          </table>
        ) : (
          <div className="form-grid" style={{ marginTop: 16 }}>
            {infoError && (
              <div className="error-banner" style={{ gridColumn: "1 / -1" }}>
                {infoError}
              </div>
            )}
            <div className="field">
              <label htmlFor="edit-chip">Chip-Nummer *</label>
              <input id="edit-chip" type="text" value={chipNumber} onChange={(e) => setChipNumber(e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="edit-tattoo">Tätowierung</label>
              <input id="edit-tattoo" type="text" value={tattooNumber} onChange={(e) => setTattooNumber(e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="edit-name">Name</label>
              <input id="edit-name" type="text" value={animalName} onChange={(e) => setAnimalName(e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="edit-birth">Geburtsdatum</label>
              <input id="edit-birth" type="date" value={birthDate} onChange={(e) => setBirthDate(e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="edit-color">Farbenschlag</label>
              <input id="edit-color" type="text" value={colorVariant} onChange={(e) => setColorVariant(e.target.value)} />
            </div>
            <div className="field">
              <label htmlFor="edit-breed">Rasse</label>
              <select id="edit-breed" value={breedIdEdit} onChange={(e) => setBreedIdEdit(e.target.value)}>
                <option value="">– keine –</option>
                {breeds.data?.map((b) => (
                  <option key={b.id} value={b.id}>
                    {b.name}
                  </option>
                ))}
              </select>
            </div>
            <div className="field">
              <label htmlFor="edit-litter-name">Wurfname</label>
              <input
                id="edit-litter-name"
                type="text"
                value={litterNameEdit}
                onChange={(e) => setLitterNameEdit(e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor="edit-mother">Mutter</label>
              <AnimalCombobox
                id="edit-mother"
                options={candidates.data?.filter((c) => c.sex === "female" && c.id !== id) ?? []}
                value={motherIdEdit}
                onChange={setMotherIdEdit}
                placeholder="unbekannt"
              />
            </div>
            <div className="field">
              <label htmlFor="edit-father">Vater</label>
              <AnimalCombobox
                id="edit-father"
                options={candidates.data?.filter((c) => c.sex === "male" && c.id !== id) ?? []}
                value={fatherIdEdit}
                onChange={setFatherIdEdit}
                placeholder="unbekannt"
              />
            </div>
            <div className="field" style={{ gridColumn: "1 / -1" }}>
              <label htmlFor="edit-notes">Notizen</label>
              <textarea id="edit-notes" rows={2} value={notesEdit} onChange={(e) => setNotesEdit(e.target.value)} />
            </div>
            <div style={{ gridColumn: "1 / -1", display: "flex", gap: 8 }}>
              <button className="btn" type="button" onClick={handleInfoSave} disabled={infoSaving}>
                {infoSaving ? "Speichere…" : "Speichern"}
              </button>
              <button className="btn secondary" type="button" onClick={() => setEditingInfo(false)} disabled={infoSaving}>
                Abbrechen
              </button>
            </div>
          </div>
        )}

        <div className="toolbar" style={{ marginTop: 16, marginBottom: 0 }}>
          {!editingInfo && (
            <button className="btn secondary" onClick={handleStartEditInfo}>
              Angaben bearbeiten
            </button>
          )}
          {!editingStatus ? (
            <button className="btn secondary" onClick={() => setEditingStatus(true)}>
              Status ändern
            </button>
          ) : (
            <>
              <select value={statusValue || a.status} onChange={(e) => setStatusValue(e.target.value)}>
                {Object.entries(STATUS_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
              <button className="btn" onClick={() => handleStatusChange(statusValue || a.status)}>
                Speichern
              </button>
              <button className="btn secondary" onClick={() => setEditingStatus(false)}>
                Abbrechen
              </button>
            </>
          )}
          {!editingCategory ? (
            <button className="btn secondary" onClick={() => setEditingCategory(true)}>
              Kategorie ändern
            </button>
          ) : (
            <>
              <select value={categoryValue || a.category} onChange={(e) => setCategoryValue(e.target.value)}>
                {Object.entries(CATEGORY_LABELS).map(([value, label]) => (
                  <option key={value} value={value}>
                    {label}
                  </option>
                ))}
              </select>
              <button className="btn" onClick={() => handleCategoryChange(categoryValue || a.category)}>
                Speichern
              </button>
              <button className="btn secondary" onClick={() => setEditingCategory(false)}>
                Abbrechen
              </button>
            </>
          )}
          <Link className="btn secondary" to={`/tiere/${id}/etikett`}>
            QR-Code / Etikett
          </Link>
          <Link className="btn secondary" to={`/scan?animal=${id}`}>
            Bewertungskarte scannen
          </Link>
          {a.sex !== "unknown" && (
            <Link className="btn secondary" to={`/tiere/${id}/paarung`}>
              Paarungsvorschläge
            </Link>
          )}
          <button className="btn danger" onClick={handleDeleteAnimal}>
            Tier löschen
          </button>
        </div>
        {deleteError && (
          <div className="error-banner" style={{ marginTop: 12 }}>
            {deleteError}
          </div>
        )}
      </div>

      <div className="card section">
        <h2>Fütterung</h2>
        <p className="hint" style={{ marginBottom: 12 }}>
          Die Fütterungsphase wird automatisch aus den Tierdaten erkannt (Gewicht vs. Idealkurve,
          Deckdatum, Wurfdatum) — keine manuelle Auswahl nötig.
        </p>
        <div className="form-grid">
          <div className="field">
            <label htmlFor="feed-select">Futter</label>
            <select id="feed-select" value={a.feed_id ?? ""} onChange={(e) => handleFeedChange(e.target.value)}>
              <option value="">– keines –</option>
              {feeds.data?.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
            </select>
          </div>
          {a.sex === "female" && (
            <div className="field">
              <label htmlFor="mating-date">Deckdatum</label>
              <input
                id="mating-date"
                type="date"
                value={matingDate}
                onChange={(e) => setMatingDate(e.target.value)}
                onBlur={handleMatingDateSave}
              />
            </div>
          )}
          <div className="field">
            <label htmlFor="target-weight">Individuelles Zielgewicht (g, optional)</label>
            <input
              id="target-weight"
              type="number"
              value={targetWeight}
              onChange={(e) => setTargetWeight(e.target.value)}
              onBlur={handleTargetSave}
            />
          </div>
          <div className="field">
            <label htmlFor="target-date">Individuelles Zieldatum (optional)</label>
            <input
              id="target-date"
              type="date"
              value={targetDate}
              onChange={(e) => setTargetDate(e.target.value)}
              onBlur={handleTargetSave}
            />
          </div>
          <div className="field">
            <label htmlFor="target-date-end">Ideal-Zeitfenster bis (optional)</label>
            <input
              id="target-date-end"
              type="date"
              value={targetDateEnd}
              onChange={(e) => setTargetDateEnd(e.target.value)}
              onBlur={handleTargetSave}
            />
          </div>
        </div>
        <p className="hint" style={{ marginBottom: 12 }}>
          Ohne individuelles Zieldatum wird die allgemeine Rassen-Idealkurve (Peak-Fenster) als
          Referenz verwendet — je näher das Tier schon am Zielgewicht ist, desto weniger Zunahme wird
          verlangt, ganz ohne Sonderregel.
        </p>
        {feedingPlan.data?.phase_error && <div className="error-banner">{feedingPlan.data.phase_error}</div>}
        {feedingPlan.data?.daily_feed_grams ? (
          <div>
            <p>
              Berechneter Tagesbedarf: <strong>{feedingPlan.data.daily_feed_grams} g</strong>{" "}
              <span className="hint">
                ({feedingPlan.data.feed_name}, {FEEDING_PHASE_LABELS[feedingPlan.data.detected_phase]})
              </span>
            </p>
            {feedingPlan.data.reason && <p className="hint">{feedingPlan.data.reason}</p>}
            {feedingPlan.data.container_fill_pct != null && (
              <p>
                Behälter-Füllmenge: <strong>{feedingPlan.data.container_fill_pct}%</strong>
              </p>
            )}
            {feedingPlan.data.feedback_hint && (
              <p className="hint" style={{ color: "var(--color-warning)" }}>
                {feedingPlan.data.feedback_hint}
              </p>
            )}
          </div>
        ) : (
          <p className="hint">
            Für eine Berechnung werden ein Futter mit Energiegehalt und mindestens ein Gewichtseintrag benötigt.
          </p>
        )}

        {feedPlanYear.data && feedPlanYear.data.points.length > 0 && (
          <div style={{ marginTop: 12 }}>
            <button className="btn secondary small" onClick={() => setShowFeedPlanYear((s) => !s)}>
              {showFeedPlanYear ? "Jahres-Futterplan ausblenden" : "Jahres-Futterplan anzeigen"}
            </button>
            {showFeedPlanYear && (
              <table style={{ marginTop: 10 }}>
                <thead>
                  <tr>
                    <th>Woche</th>
                    <th>Alter</th>
                    <th>Erw. Gewicht</th>
                    <th>Futter/Tag</th>
                  </tr>
                </thead>
                <tbody>
                  {feedPlanYear.data.points.map((p) => (
                    <tr key={p.week}>
                      <td>+{p.week}</td>
                      <td>{p.age_weeks} Wo.</td>
                      <td>{p.predicted_weight_grams != null ? `${p.predicted_weight_grams} g` : "–"}</td>
                      <td>{p.daily_feed_grams != null ? `${p.daily_feed_grams} g` : "–"}</td>
                    </tr>
                  ))}
                </tbody>
              </table>
            )}
          </div>
        )}
      </div>

      <div className="card section">
        <h2>Stammbaum</h2>
        {pedigree.loading && <p>Lade Stammbaum…</p>}
        {pedigree.data && <PedigreeTree root={pedigree.data} />}

        <h3 style={{ marginTop: 20 }}>Verpaarung prüfen</h3>
        {a.sex === "unknown" ? (
          <p className="hint">Für den Verpaarungs-Check muss das Geschlecht bekannt sein.</p>
        ) : (
          <>
            <div className="toolbar">
              <select value={pairingCandidateId} onChange={(e) => setPairingCandidateId(e.target.value)}>
                <option value="">
                  {a.sex === "female" ? "Rammler wählen…" : "Zibbe wählen…"}
                </option>
                {(candidates.data ?? [])
                  .filter((c) => c.id !== id && c.sex === (a.sex === "female" ? "male" : "female"))
                  .map((c) => (
                    <option key={c.id} value={c.id}>
                      {c.chip_number} {c.name ? `· ${c.name}` : ""}
                    </option>
                  ))}
              </select>
              <button className="btn secondary" onClick={handlePairingCheck} disabled={!pairingCandidateId}>
                Prüfen
              </button>
            </div>
            {pairingError && <div className="error-banner">{pairingError}</div>}
            {pairingResult && (
              <p>
                Inzuchtkoeffizient der Nachkommen:{" "}
                <span className={`badge ${coiRiskClass(pairingResult.inbreeding_coefficient)}`}>
                  {coiLabel(pairingResult.inbreeding_coefficient)}
                </span>{" "}
                <span className="hint">(Risiko: {pairingResult.risk_level})</span>
              </p>
            )}
          </>
        )}
      </div>

      <div className="card section">
        <h2>Gewichtshistorie & Peak-Fenster</h2>
        {siblingsGrowthCurve.data && siblingsGrowthCurve.data.sibling_count >= 1 && (
          <label style={{ display: "flex", alignItems: "center", gap: 6, marginBottom: 8, fontWeight: 400 }}>
            <input
              type="checkbox"
              checked={showSiblingsCurve}
              onChange={(e) => setShowSiblingsCurve(e.target.checked)}
              style={{ width: "auto" }}
            />
            Ø Geschwister anzeigen ({siblingsGrowthCurve.data.sibling_count})
          </label>
        )}
        {chartData.length > 0 && (
          <div style={{ height: 220, marginBottom: 16 }}>
            <ResponsiveContainer width="100%" height="100%">
              <LineChart data={chartData}>
                <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                <XAxis dataKey="date" tick={{ fontSize: 11 }} />
                <YAxis tick={{ fontSize: 11 }} width={50} />
                <Tooltip />
                <Line
                  type="monotone"
                  dataKey="predicted"
                  name="Rassenkurve (erwartet)"
                  stroke="#9ca3af"
                  strokeDasharray="4 3"
                  strokeWidth={1.5}
                  dot={false}
                  connectNulls
                />
                <Line
                  type="monotone"
                  dataKey="grams"
                  name="Gemessen"
                  stroke="#4338ca"
                  strokeWidth={2}
                  dot={{ r: 3 }}
                  connectNulls
                />
                {growthPlan.data?.own_trend && growthPlan.data.own_trend.length > 0 && (
                  <Line
                    type="monotone"
                    dataKey="ownTrend"
                    name="Eigener Trend (Tier weicht ab)"
                    stroke="#d97706"
                    strokeDasharray="2 2"
                    strokeWidth={1.5}
                    dot={false}
                    connectNulls
                  />
                )}
                {showSiblingsCurve && siblingsGrowthCurve.data && siblingsGrowthCurve.data.sibling_count >= 1 && (
                  <Line
                    type="monotone"
                    dataKey="siblingsActual"
                    name={`Ø Geschwister (${siblingsGrowthCurve.data.sibling_count})`}
                    stroke="#0d9488"
                    strokeWidth={1.5}
                    dot={{ r: 3 }}
                    connectNulls
                  />
                )}
              </LineChart>
            </ResponsiveContainer>
          </div>
        )}

        {growthPlan.data && (growthPlan.data.status || growthPlan.data.peak) && (
          <div style={{ marginBottom: 16 }}>
            {growthPlan.data.status && (
              <p>
                Wachstumsstatus:{" "}
                <span className={`badge ${growthStatusClass(growthPlan.data.status)}`}>
                  {GROWTH_STATUS_LABELS[growthPlan.data.status] ?? growthPlan.data.status}
                </span>{" "}
                <span className="hint">
                  ({growthPlan.data.actual_weight_grams} g gemessen vs. {growthPlan.data.predicted_weight_grams} g
                  erwartet bei {growthPlan.data.age_weeks} Wochen, {growthPlan.data.deviation_pct}%)
                </span>
              </p>
            )}
            {growthPlan.data.growth_rate && (
              <p>
                Vermutete Zunahme-Geschwindigkeit: <strong>{GROWTH_RATE_LABELS[growthPlan.data.growth_rate]}</strong>{" "}
                <span className="hint">(passt sich mit weiteren Gewichtseinträgen automatisch an)</span>
              </p>
            )}
            {growthPlan.data.suggested_target_weight_grams != null && (
              <p className="hint">
                Gewichtsvorschlag: {growthPlan.data.suggested_target_weight_grams} g (
                {growthPlan.data.target_weight_source === "family"
                  ? `basierend auf ${growthPlan.data.target_weight_sample_count} Gewichtseinträgen von Eltern/Geschwistern`
                  : "Rassestandard"}
                ){growthPlan.data.target_weight_source === "family" && " — weicht vom Rassestandard ab"}
              </p>
            )}
            {growthPlan.data.peak && (
              <p className="hint">
                Voraussichtliches Idealgewichts-Fenster ab {growthPlan.data.peak.start_date}
                {growthPlan.data.peak.end_date ? ` bis ${growthPlan.data.peak.end_date}` : " (danach weiterhin im Idealbereich)"}
                {growthPlan.data.target_date && (
                  <>
                    {" "}
                    — Zieldatum {growthPlan.data.target_date}:{" "}
                    {growthPlan.data.target_date_in_peak_window ? "liegt im Fenster ✓" : "liegt ausserhalb des Fensters"}
                  </>
                )}
              </p>
            )}
          </div>
        )}

        <form className="form-grid" onSubmit={handleAddWeight} style={{ alignItems: "end", marginBottom: 16 }}>
          {weightError && <div className="error-banner">{weightError}</div>}
          <div className="field">
            <label htmlFor="w-date">Datum</label>
            <input id="w-date" type="date" value={weightDate} onChange={(e) => setWeightDate(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="w-grams">Gewicht (g)</label>
            <input
              id="w-grams"
              type="number"
              inputMode="numeric"
              value={weightGrams}
              onChange={(e) => setWeightGrams(e.target.value)}
            />
          </div>
          <button className="btn" type="submit">
            Eintragen
          </button>
        </form>

        <div className="list">
          {[...(weights.data ?? [])].reverse().map((w) => (
            <div className="list-item" key={w.id}>
              <span>{w.measured_on}</span>
              <span>{w.weight_grams} g</span>
              <button className="btn danger small" onClick={() => handleDeleteWeight(w.id)}>
                Löschen
              </button>
            </div>
          ))}
          {weights.data && weights.data.length === 0 && <p className="empty-state">Noch keine Gewichte erfasst.</p>}
        </div>
      </div>

      <div className="card section">
        <h2>Bewertungen</h2>

        {(strengthsWeaknesses.data?.strengths.length ?? 0) > 0 ||
        (strengthsWeaknesses.data?.weaknesses.length ?? 0) > 0 ? (
          <div style={{ marginBottom: 16 }}>
            <p className="hint" style={{ marginBottom: 6 }}>
              Im Vergleich zum Rassedurchschnitt aller erfassten Bewertungskarten:
            </p>
            <div className="toolbar" style={{ flexWrap: "wrap" }}>
              {strengthsWeaknesses.data?.strengths.map((s) => (
                <span key={s.category_label} className="badge category-breeding" title={`${s.animal_avg_pct}% vs. Ø ${s.breed_avg_pct}%`}>
                  💪 {s.category_label} (+{s.diff_pct.toFixed(0)}%)
                </span>
              ))}
              {strengthsWeaknesses.data?.weaknesses.map((s) => (
                <span key={s.category_label} className="badge status-deceased" title={`${s.animal_avg_pct}% vs. Ø ${s.breed_avg_pct}%`}>
                  ⚠️ {s.category_label} ({s.diff_pct.toFixed(0)}%)
                </span>
              ))}
            </div>
          </div>
        ) : null}

        {evaluations.data && evaluations.data.length > 0 && (
          <p className="hint" style={{ marginBottom: 12 }}>
            Ø Gesamtpunktzahl über {evaluations.data.filter((e) => e.total_score != null).length} Bewertung(en):{" "}
            <strong>
              {(
                evaluations.data.reduce((sum, e) => sum + (e.total_score ?? 0), 0) /
                Math.max(evaluations.data.filter((e) => e.total_score != null).length, 1)
              ).toFixed(1)}
            </strong>
          </p>
        )}

        {!a.breed_id && <p className="hint">Für die standardkonforme Bewertungsskala zuerst eine Rasse zuordnen.</p>}

        {a.breed_id && !showEvalForm && (
          <button className="btn" onClick={() => setShowEvalForm(true)}>
            + Bewertung erfassen
          </button>
        )}

        {showEvalForm && (
          <form className="card" onSubmit={handleAddEvaluation} style={{ marginBottom: 16 }}>
            {evalError && <div className="error-banner">{evalError}</div>}
            <div className="form-grid">
              <div className="field">
                <label htmlFor="e-date">Datum</label>
                <input id="e-date" type="date" value={evalDate} onChange={(e) => setEvalDate(e.target.value)} />
              </div>
              <div className="field">
                <label htmlFor="e-show">Ausstellung</label>
                <input id="e-show" type="text" value={showName} onChange={(e) => setShowName(e.target.value)} />
              </div>
              <div className="field">
                <label htmlFor="e-weight">Gewicht bei Bewertung (g)</label>
                <input
                  id="e-weight"
                  type="number"
                  value={evalWeight}
                  onChange={(e) => setEvalWeight(e.target.value)}
                />
              </div>
            </div>
            <h3>Bewertungsskala (Standard CH)</h3>
            <div className="form-grid">
              {scores.map((s, i) => (
                <div className="field" key={s.position_number}>
                  <label htmlFor={`score-${s.position_number}`}>
                    {s.position_number}. {s.category_label}
                  </label>
                  <select
                    id={`score-${s.position_number}`}
                    value={s.points}
                    onChange={(e) => updateScore(i, Number(e.target.value))}
                  >
                    {pointOptionsForMaxPoints(s.max_points).map((opt) => (
                      <option key={opt.value} value={opt.value}>
                        {opt.label}
                      </option>
                    ))}
                  </select>
                </div>
              ))}
            </div>
            <p style={{ marginTop: 12 }}>
              Gesamtpunktzahl: <strong>{scoreTotal.toFixed(1)}</strong>
              {scoreTotal < EXCLUSION_THRESHOLD && (
                <span className="hint" style={{ color: "var(--color-danger)", marginLeft: 8 }}>
                  unter Ausschlussgrenze ({EXCLUSION_THRESHOLD})
                </span>
              )}
            </p>
            <div className="toolbar" style={{ marginBottom: 0 }}>
              <button className="btn" type="submit">
                Speichern
              </button>
              <button className="btn secondary" type="button" onClick={() => setShowEvalForm(false)}>
                Abbrechen
              </button>
            </div>
          </form>
        )}

        {evaluations.data && evaluations.data.length > 0 && (
          <div style={{ marginTop: 16 }}>
            <div className="field">
              <label htmlFor="eval-picker">Karte auswählen</label>
              <select
                id="eval-picker"
                value={selectedEvalId || evaluations.data[0].id}
                onChange={(e) => setSelectedEvalId(e.target.value)}
              >
                {evaluations.data.map((ev) => (
                  <option key={ev.id} value={ev.id}>
                    {ev.evaluated_on} {ev.show_name ? `· ${ev.show_name}` : "· ohne Titel"}
                  </option>
                ))}
              </select>
            </div>
            {(() => {
              const ev = evaluations.data!.find((e) => e.id === (selectedEvalId || evaluations.data![0].id));
              if (!ev) return null;
              return (
                <div className="card" style={{ marginTop: 10 }}>
                  <div style={{ display: "flex", justifyContent: "space-between", alignItems: "flex-start" }}>
                    <div>
                      <div className="title">
                        {ev.evaluated_on} {ev.show_name ? `· ${ev.show_name}` : ""}
                      </div>
                      {ev.exhibitor_name && <div className="hint">Aussteller: {ev.exhibitor_name}</div>}
                    </div>
                    <strong style={{ fontSize: "1.3rem" }}>{ev.total_score ?? "–"}</strong>
                  </div>
                  {ev.scores.length > 0 && (
                    <table style={{ marginTop: 10 }}>
                      <tbody>
                        {ev.scores.map((s) => (
                          <tr key={s.position_number}>
                            <th>{s.position_number}. {s.category_label}</th>
                            <td>{s.points} / {s.max_points}</td>
                          </tr>
                        ))}
                      </tbody>
                    </table>
                  )}
                  {ev.notes && <p className="hint" style={{ marginTop: 8 }}>{ev.notes}</p>}
                  {ev.photo_path && (
                    <a href={`${BASE_URL}${ev.photo_path}`} target="_blank" rel="noreferrer" className="hint">
                      Original-Foto ansehen
                    </a>
                  )}
                  <div className="toolbar" style={{ marginTop: 12, marginBottom: 0 }}>
                    <button className="btn danger small" onClick={() => handleDeleteEvaluation(ev.id)}>
                      Diese Karte löschen
                    </button>
                  </div>
                </div>
              );
            })()}
          </div>
        )}
        {evaluations.data && evaluations.data.length === 0 && (
          <p className="empty-state">Noch keine Bewertungen erfasst.</p>
        )}
      </div>

      <div className="card section">
        <h2>Nachkommen</h2>

        {offspringScores.data && offspringScores.data.categories.length >= 3 && (
          <div style={{ marginBottom: 20 }}>
            <h3>
              Stärken/Schwächen der Nachkommen ({offspringScores.data.child_count} Kinder,{" "}
              {offspringScores.data.evaluation_count} Bewertungen)
            </h3>
            <div style={{ height: 260 }}>
              <ResponsiveContainer width="100%" height="100%">
                <RadarChart data={offspringScores.data.categories}>
                  <PolarGrid stroke="var(--color-border)" />
                  <PolarAngleAxis dataKey="category_label" tick={{ fontSize: 10 }} />
                  <PolarRadiusAxis domain={[0, 100]} tick={{ fontSize: 9 }} />
                  <Radar
                    name="Ø Prozent vom Höchstwert"
                    dataKey="average_pct"
                    stroke="#4338ca"
                    fill="#4338ca"
                    fillOpacity={0.25}
                  />
                  <Tooltip />
                </RadarChart>
              </ResponsiveContainer>
            </div>
            <p className="hint">
              Durchschnitt je Bewertungsposition über alle Bewertungen der direkten Nachkommen, als
              Prozent vom jeweiligen Höchstwert.
            </p>
          </div>
        )}

        {descendantsGrowth.data && descendantsGrowth.data.points.length > 1 && (
          <div style={{ marginBottom: 20 }}>
            <h3>Wachstumskurve der Linie ({descendantsGrowth.data.descendant_count} Nachkommen)</h3>
            <div style={{ height: 200 }}>
              <ResponsiveContainer width="100%" height="100%">
                <ComposedChart data={descendantsChartData(descendantsGrowth.data.points)}>
                  <CartesianGrid strokeDasharray="3 3" stroke="var(--color-border)" />
                  <XAxis dataKey="age" tick={{ fontSize: 11 }} label={{ value: "Wochen", position: "insideBottom", offset: -2, fontSize: 11 }} />
                  <YAxis tick={{ fontSize: 11 }} width={50} />
                  <Tooltip />
                  <Area type="monotone" dataKey="max" stroke="none" fill="#4338ca" fillOpacity={0.1} />
                  <Area type="monotone" dataKey="min" stroke="none" fill="#ffffff" fillOpacity={1} />
                  <Line type="monotone" dataKey="mean" name="Durchschnitt" stroke="#4338ca" strokeWidth={2} dot={{ r: 2 }} />
                </ComposedChart>
              </ResponsiveContainer>
            </div>
            <p className="hint">Schattierter Bereich = Min–Max-Spanne je Alters-Zeitraum.</p>
          </div>
        )}

        <div className="list">
          {children.data?.map((c) => (
            <Link className="list-item" to={`/tiere/${c.id}`} key={c.id}>
              <span>
                {c.chip_number} {c.name ? `· ${c.name}` : ""}
              </span>
              <span className={`badge status-${c.status}`}>{STATUS_LABELS[c.status]}</span>
            </Link>
          ))}
          {children.data && children.data.length === 0 && <p className="empty-state">Keine Nachkommen erfasst.</p>}
        </div>
      </div>
    </div>
  );
}
