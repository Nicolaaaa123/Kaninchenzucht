import { useEffect, useMemo, useState } from "react";
import { Link, useNavigate } from "react-router-dom";
import { api } from "../api/client";
import { AnimalCombobox } from "../components/AnimalCombobox";
import { useAsync } from "../hooks/useAsync";

export function LitterNew() {
  const navigate = useNavigate();
  const animals = useAsync(() => api.animals.list(), []);
  const breeds = useAsync(() => api.breeds.list(), []);

  const [motherId, setMotherId] = useState("");
  const [fatherId, setFatherId] = useState("");
  const [matingDate, setMatingDate] = useState("");
  const [birthDate, setBirthDate] = useState(() => new Date().toISOString().slice(0, 10));
  const [breedId, setBreedId] = useState("");
  const [litterName, setLitterName] = useState("");
  const [countMale, setCountMale] = useState(0);
  const [countFemale, setCountFemale] = useState(0);
  const [countUnknown, setCountUnknown] = useState(0);
  const [maleLetter, setMaleLetter] = useState("");
  const [femaleLetter, setFemaleLetter] = useState("");
  const [notes, setNotes] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [error, setError] = useState<string | null>(null);

  const [maleNames, setMaleNames] = useState<(string | null)[]>([]);
  const [femaleNames, setFemaleNames] = useState<(string | null)[]>([]);
  const [namesGenerated, setNamesGenerated] = useState(false);
  const [generatingNames, setGeneratingNames] = useState(false);

  useEffect(() => {
    setNamesGenerated(false);
  }, [countMale, countFemale, maleLetter, femaleLetter, motherId, fatherId]);

  const mothers = animals.data?.filter((a) => a.sex === "female") ?? [];
  const fathers = animals.data?.filter((a) => a.sex === "male") ?? [];

  const selectedMother = animals.data?.find((a) => a.id === motherId);
  const selectedFather = animals.data?.find((a) => a.id === fatherId);

  const effectiveMaleLetter = maleLetter || (selectedFather?.name ? selectedFather.name[0] : "");
  const effectiveFemaleLetter = femaleLetter || (selectedMother?.name ? selectedMother.name[0] : "");

  const effectiveBreedId = breedId || selectedMother?.breed?.id || "";
  const effectiveBreed = breeds.data?.find((b) => b.id === effectiveBreedId);
  const gestationDays = effectiveBreed?.gestation_days ?? 31;

  const gestationWarning = useMemo(() => {
    if (!matingDate || !birthDate) return null;
    const mating = new Date(matingDate);
    const birth = new Date(birthDate);
    const actualDays = Math.round((birth.getTime() - mating.getTime()) / (1000 * 60 * 60 * 24));
    const deviation = actualDays - gestationDays;
    if (Math.abs(deviation) <= 7) return null;
    return `Ungewöhnlich: Zwischen Deckdatum und Wurfdatum liegen ${actualDays} Tage, normal sind ca. ${gestationDays} Tage (±7). Bitte Daten prüfen.`;
  }, [matingDate, birthDate, gestationDays]);

  async function handleGenerateNames() {
    setGeneratingNames(true);
    setError(null);
    try {
      const [maleRes, femaleRes] = await Promise.all([
        countMale > 0
          ? api.animals.nameSuggestions(effectiveMaleLetter || null, countMale, "male")
          : Promise.resolve({ names: [] }),
        countFemale > 0
          ? api.animals.nameSuggestions(effectiveFemaleLetter || null, countFemale, "female", [])
          : Promise.resolve({ names: [] }),
      ]);
      setMaleNames(maleRes.names);
      setFemaleNames(femaleRes.names);
      setNamesGenerated(true);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setGeneratingNames(false);
    }
  }

  async function handleRegenerateName(sex: "male" | "female", index: number) {
    const letter = sex === "male" ? effectiveMaleLetter : effectiveFemaleLetter;
    const currentNames = [...maleNames, ...femaleNames].filter((n): n is string => !!n);
    try {
      const res = await api.animals.nameSuggestions(letter || null, 1, sex, currentNames);
      const newName = res.names[0] ?? null;
      if (sex === "male") {
        setMaleNames((prev) => prev.map((n, i) => (i === index ? newName : n)));
      } else {
        setFemaleNames((prev) => prev.map((n, i) => (i === index ? newName : n)));
      }
    } catch (err) {
      setError((err as Error).message);
    }
  }

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!motherId) {
      setError("Bitte eine Mutter auswählen.");
      return;
    }
    if (!birthDate) return;
    if (countMale + countFemale + countUnknown <= 0) {
      setError("Mindestens ein Jungtier angeben.");
      return;
    }
    setSubmitting(true);
    setError(null);
    try {
      const namesReady = namesGenerated && maleNames.length === countMale && femaleNames.length === countFemale;
      const result = await api.animals.createLitter({
        mother_id: motherId,
        father_id: fatherId || null,
        birth_date: birthDate,
        mating_date: matingDate || null,
        breed_id: breedId || null,
        litter_name: litterName.trim() || null,
        count_male: countMale,
        count_female: countFemale,
        count_unknown: countUnknown,
        male_name_letter: maleLetter || null,
        female_name_letter: femaleLetter || null,
        male_names: namesReady ? maleNames : null,
        female_names: namesReady ? femaleNames : null,
        notes: notes.trim() || null,
      });
      navigate(`/tiere?wurf=${result.count}`);
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  return (
    <div>
      <Link className="back-link" to="/tiere">
        ← Zurück zur Übersicht
      </Link>
      <h1>Wurf erstellen</h1>
      <p className="hint" style={{ marginBottom: 16 }}>
        Legt auf einmal mehrere Jungtiere an, statt jedes einzeln einzutragen. Rammler bekommen
        automatisch einen Namen mit dem Anfangsbuchstaben des Vaters, Zibben mit dem der Mutter
        (überschreibbar unten). Chip-Nummern werden als Platzhalter vergeben — bitte später durch
        die echten Chip-Nummern ersetzen.
      </p>

      <form className="card" onSubmit={handleSubmit}>
        {error && <div className="error-banner">{error}</div>}
        <div className="form-grid">
          <div className="field">
            <label htmlFor="mother">Mutter *</label>
            <AnimalCombobox id="mother" options={mothers} value={motherId} onChange={setMotherId} />
          </div>
          <div className="field">
            <label htmlFor="father">Vater</label>
            <AnimalCombobox
              id="father"
              options={fathers}
              value={fatherId}
              onChange={setFatherId}
              placeholder="– unbekannt –"
            />
          </div>
          <div className="field">
            <label htmlFor="mating-date">Deckdatum</label>
            <input
              id="mating-date"
              type="date"
              value={matingDate}
              onChange={(e) => setMatingDate(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="birth-date">Geburtsdatum (Wurfdatum) *</label>
            <input
              id="birth-date"
              type="date"
              value={birthDate}
              onChange={(e) => setBirthDate(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="breed">Rasse</label>
            <select id="breed" value={breedId} onChange={(e) => setBreedId(e.target.value)}>
              <option value="">– von Mutter übernehmen –</option>
              {breeds.data?.map((b) => (
                <option key={b.id} value={b.id}>
                  {b.name}
                </option>
              ))}
            </select>
          </div>
          <div className="field">
            <label htmlFor="litter-name">Wurfname (optional)</label>
            <input
              id="litter-name"
              type="text"
              placeholder="z.B. Frühjahrswurf 2026"
              value={litterName}
              onChange={(e) => setLitterName(e.target.value)}
            />
          </div>
        </div>
        {gestationWarning && <div className="warning-banner">{gestationWarning}</div>}

        <h3 style={{ marginTop: 16 }}>Anzahl Jungtiere</h3>
        <div className="form-grid">
          <div className="field">
            <label htmlFor="count-male">Rammler</label>
            <input
              id="count-male"
              type="number"
              min={0}
              value={countMale}
              onChange={(e) => setCountMale(Number(e.target.value))}
            />
          </div>
          <div className="field">
            <label htmlFor="count-female">Zibben</label>
            <input
              id="count-female"
              type="number"
              min={0}
              value={countFemale}
              onChange={(e) => setCountFemale(Number(e.target.value))}
            />
          </div>
          <div className="field">
            <label htmlFor="count-unknown">Geschlecht noch unbekannt</label>
            <input
              id="count-unknown"
              type="number"
              min={0}
              value={countUnknown}
              onChange={(e) => setCountUnknown(Number(e.target.value))}
            />
          </div>
        </div>

        <h3 style={{ marginTop: 16 }}>Namensgenerator</h3>
        <div className="form-grid">
          <div className="field">
            <label htmlFor="male-letter">Anfangsbuchstabe Rammler-Namen</label>
            <input
              id="male-letter"
              type="text"
              maxLength={1}
              value={maleLetter}
              onChange={(e) => setMaleLetter(e.target.value)}
              placeholder={selectedFather?.name ? selectedFather.name[0] : "z.B. vom Vater"}
            />
          </div>
          <div className="field">
            <label htmlFor="female-letter">Anfangsbuchstabe Zibben-Namen</label>
            <input
              id="female-letter"
              type="text"
              maxLength={1}
              value={femaleLetter}
              onChange={(e) => setFemaleLetter(e.target.value)}
              placeholder={selectedMother?.name ? selectedMother.name[0] : "z.B. von der Mutter"}
            />
          </div>
        </div>
        <p className="hint">
          Leer lassen, um automatisch den Anfangsbuchstaben von Vater-/Mutternamen zu verwenden
          (falls diese einen Namen haben).
        </p>
        <button
          type="button"
          className="btn secondary"
          onClick={handleGenerateNames}
          disabled={generatingNames || countMale + countFemale === 0}
        >
          {generatingNames ? "Generiere…" : "Namen vorschlagen"}
        </button>

        {namesGenerated && (countMale > 0 || countFemale > 0) && (
          <div style={{ marginTop: 12 }}>
            {countMale > 0 && (
              <>
                <h4 style={{ marginBottom: 6 }}>Rammler-Namen</h4>
                {maleNames.map((n, i) => (
                  <div className="toolbar" key={`m-${i}`} style={{ marginBottom: 4 }}>
                    <input
                      type="text"
                      value={n ?? ""}
                      onChange={(e) =>
                        setMaleNames((prev) => prev.map((x, idx) => (idx === i ? e.target.value : x)))
                      }
                      style={{ flex: 1 }}
                    />
                    <button
                      type="button"
                      className="btn secondary small"
                      onClick={() => handleRegenerateName("male", i)}
                      title="Diesen Namen neu würfeln"
                    >
                      🔄 Neu
                    </button>
                  </div>
                ))}
              </>
            )}
            {countFemale > 0 && (
              <>
                <h4 style={{ marginTop: 10, marginBottom: 6 }}>Zibben-Namen</h4>
                {femaleNames.map((n, i) => (
                  <div className="toolbar" key={`f-${i}`} style={{ marginBottom: 4 }}>
                    <input
                      type="text"
                      value={n ?? ""}
                      onChange={(e) =>
                        setFemaleNames((prev) => prev.map((x, idx) => (idx === i ? e.target.value : x)))
                      }
                      style={{ flex: 1 }}
                    />
                    <button
                      type="button"
                      className="btn secondary small"
                      onClick={() => handleRegenerateName("female", i)}
                      title="Diesen Namen neu würfeln"
                    >
                      🔄 Neu
                    </button>
                  </div>
                ))}
              </>
            )}
          </div>
        )}

        <div className="field" style={{ marginTop: 12 }}>
          <label htmlFor="notes">Notizen</label>
          <textarea id="notes" rows={2} value={notes} onChange={(e) => setNotes(e.target.value)} />
        </div>

        <button className="btn" type="submit" disabled={submitting} style={{ marginTop: 12 }}>
          Wurf anlegen
        </button>
      </form>
    </div>
  );
}
