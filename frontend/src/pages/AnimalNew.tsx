import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { useAsync } from "../hooks/useAsync";
import type { Sex } from "../api/types";

export function AnimalNew() {
  const navigate = useNavigate();
  const { data: breeds } = useAsync(() => api.breeds.list(), []);
  const { data: stalls } = useAsync(() => api.stalls.list(), []);
  const { data: feeds } = useAsync(() => api.feeds.list(), []);
  const { data: animals } = useAsync(() => api.animals.list(), []);

  const [chipNumber, setChipNumber] = useState("");
  const [tattooNumber, setTattooNumber] = useState("");
  const [name, setName] = useState("");
  const [sex, setSex] = useState<Sex>("unknown");
  const [birthDate, setBirthDate] = useState("");
  const [breedId, setBreedId] = useState("");
  const [colorVariant, setColorVariant] = useState("");
  const [cageBoxId, setCageBoxId] = useState("");
  const [feedId, setFeedId] = useState("");
  const [targetWeight, setTargetWeight] = useState("");
  const [targetDate, setTargetDate] = useState("");
  const [motherId, setMotherId] = useState("");
  const [fatherId, setFatherId] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const mothers = animals?.filter((a) => a.sex === "female") ?? [];
  const fathers = animals?.filter((a) => a.sex === "male") ?? [];

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!chipNumber.trim()) return;
    if (!birthDate) {
      const proceed = confirm(
        "Kein Geburtsdatum angegeben — ohne das funktionieren Wachstumskurve, Peak-Fenster und " +
          "Futterberechnung nicht. Du kannst es jederzeit auf der Tierseite nachtragen. Trotzdem jetzt anlegen?",
      );
      if (!proceed) return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const animal = await api.animals.create({
        chip_number: chipNumber.trim(),
        tattoo_number: tattooNumber.trim() || null,
        name: name.trim() || null,
        sex,
        birth_date: birthDate || null,
        breed_id: breedId || null,
        color_variant: colorVariant.trim() || null,
        cage_box_id: cageBoxId || null,
        feed_id: feedId || null,
        target_weight_grams: targetWeight ? Number(targetWeight) : null,
        target_date: targetDate || null,
        mother_id: motherId || null,
        father_id: fatherId || null,
        notes: notes.trim() || null,
      });
      navigate(`/tiere/${animal.id}`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <h1>Neues Tier anlegen</h1>
      <form className="card" onSubmit={handleSubmit}>
        {error && <div className="error-banner">{error}</div>}
        <div className="form-grid">
          <div className="field">
            <label htmlFor="chip-number">Chip-Nummer *</label>
            <input
              id="chip-number"
              type="text"
              value={chipNumber}
              onChange={(e) => setChipNumber(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="tattoo-number">Ohrmarke (optional)</label>
            <input
              id="tattoo-number"
              type="text"
              value={tattooNumber}
              onChange={(e) => setTattooNumber(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="name">Name</label>
            <input id="name" type="text" value={name} onChange={(e) => setName(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="sex">Geschlecht</label>
            <select id="sex" value={sex} onChange={(e) => setSex(e.target.value as Sex)}>
              <option value="unknown">unbekannt</option>
              <option value="male">♂ Rammler</option>
              <option value="female">♀ Zibbe</option>
            </select>
          </div>
          <div className="field">
            <label htmlFor="birth-date">Geburtsdatum</label>
            <input id="birth-date" type="date" value={birthDate} onChange={(e) => setBirthDate(e.target.value)} />
            <span className="hint">Wichtig für Wachstumskurve, Peak-Fenster und Futterberechnung</span>
          </div>
          <div className="field">
            <label htmlFor="breed">Rasse</label>
            <select id="breed" value={breedId} onChange={(e) => setBreedId(e.target.value)}>
              <option value="">– keine –</option>
              {breeds?.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="color-variant">Farbenschlag</label>
            <input
              id="color-variant"
              type="text"
              value={colorVariant}
              onChange={(e) => setColorVariant(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="cage-box">Box</label>
            <select id="cage-box" value={cageBoxId} onChange={(e) => setCageBoxId(e.target.value)}>
              <option value="">– keine –</option>
              {stalls?.map((stall) => (
                <optgroup label={stall.label} key={stall.id}>
                  {stall.boxes.map((box) => (
                    <option key={box.id} value={box.id} disabled={box.occupants.length > 0}>
                      Box {box.label} {box.occupants.length > 0 ? "(belegt)" : ""}
                    </option>
                  ))}
                </optgroup>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="feed">Futter</label>
            <select id="feed" value={feedId} onChange={(e) => setFeedId(e.target.value)}>
              <option value="">– keines –</option>
              {feeds?.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="target-weight">Zielgewicht (g)</label>
            <input
              id="target-weight"
              type="number"
              value={targetWeight}
              onChange={(e) => setTargetWeight(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="target-date">Zieldatum</label>
            <input id="target-date" type="date" value={targetDate} onChange={(e) => setTargetDate(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="mother">Mutter</label>
            <select id="mother" value={motherId} onChange={(e) => setMotherId(e.target.value)}>
              <option value="">– unbekannt –</option>
              {mothers.map((m) => (
                <option key={m.id} value={m.id}>
                  {m.chip_number} {m.name ? `· ${m.name}` : ""}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="father">Vater</label>
            <select id="father" value={fatherId} onChange={(e) => setFatherId(e.target.value)}>
              <option value="">– unbekannt –</option>
              {fathers.map((f) => (
                <option key={f.id} value={f.id}>
                  {f.chip_number} {f.name ? `· ${f.name}` : ""}
                </option>
              ))}
            </select>
          </div>
        </div>
        <div className="field">
          <label htmlFor="notes">Notizen</label>
          <textarea id="notes" rows={3} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>
        <button className="btn" type="submit" disabled={submitting}>
          Tier anlegen
        </button>
      </form>
    </div>
  );
}
