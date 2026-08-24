import { useState } from "react";
import { api } from "../api/client";
import { useAsync } from "../hooks/useAsync";

export function Feeds() {
  const { data, loading, error, reload } = useAsync(() => api.feeds.list(), []);
  const [name, setName] = useState("");
  const [manufacturer, setManufacturer] = useState("");
  const [energy, setEnergy] = useState("");
  const [protein, setProtein] = useState("");
  const [fiber, setFiber] = useState("");
  const [fat, setFat] = useState("");
  const [containerCapacity, setContainerCapacity] = useState("");
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);

  async function handleSubmit(e: React.FormEvent) {
    e.preventDefault();
    if (!name.trim() || !energy) return;
    setSubmitting(true);
    setFormError(null);
    try {
      await api.feeds.create({
        name: name.trim(),
        manufacturer: manufacturer.trim() || null,
        energy_mj_per_kg: Number(energy),
        crude_protein_pct: protein ? Number(protein) : null,
        crude_fiber_pct: fiber ? Number(fiber) : null,
        crude_fat_pct: fat ? Number(fat) : null,
        container_capacity_grams: containerCapacity ? Number(containerCapacity) : null,
      });
      setName("");
      setManufacturer("");
      setEnergy("");
      setProtein("");
      setFiber("");
      setFat("");
      setContainerCapacity("");
      reload();
    } catch (err) {
      setFormError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDelete(id: string) {
    if (!confirm("Dieses Futter wirklich löschen?")) return;
    await api.feeds.remove(id);
    reload();
  }

  return (
    <div>
      <h1>Futter</h1>
      <p className="hint" style={{ marginBottom: 16 }}>
        Nährwerte laut Etikett/Datenblatt des Herstellers. Der Tagesbedarf pro Tier wird daraus im Stallplan
        und in der Tierdetailansicht berechnet (Energiebedarf ÷ Energiegehalt des Futters).
      </p>

      <form className="card section" onSubmit={handleSubmit}>
        <h2>Neues Futter anlegen</h2>
        {formError && <div className="error-banner">{formError}</div>}
        <div className="form-grid">
          <div className="field">
            <label htmlFor="f-name">Name *</label>
            <input id="f-name" type="text" value={name} onChange={(e) => setName(e.target.value)} required />
          </div>
          <div className="field">
            <label htmlFor="f-manufacturer">Hersteller</label>
            <input
              id="f-manufacturer"
              type="text"
              value={manufacturer}
              onChange={(e) => setManufacturer(e.target.value)}
            />
          </div>
          <div className="field">
            <label htmlFor="f-energy">Energie (MJ/kg) *</label>
            <input
              id="f-energy"
              type="number"
              step="0.01"
              value={energy}
              onChange={(e) => setEnergy(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="f-protein">Rohprotein (%)</label>
            <input id="f-protein" type="number" step="0.1" value={protein} onChange={(e) => setProtein(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="f-fiber">Rohfaser (%)</label>
            <input id="f-fiber" type="number" step="0.1" value={fiber} onChange={(e) => setFiber(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="f-fat">Rohfett (%)</label>
            <input id="f-fat" type="number" step="0.1" value={fat} onChange={(e) => setFat(e.target.value)} />
          </div>
          <div className="field">
            <label htmlFor="f-container">Behälter-Fassungsvermögen (g)</label>
            <input
              id="f-container"
              type="number"
              step="1"
              value={containerCapacity}
              onChange={(e) => setContainerCapacity(e.target.value)}
              placeholder="z.B. 2000"
            />
          </div>
        </div>
        <p className="hint" style={{ marginBottom: 12 }}>
          Wenn angegeben, wird im Stallplan und in der Tierdetailansicht berechnet, zu wie viel Prozent
          der Futterbehälter befüllt werden muss, um den Tagesbedarf zu decken.
        </p>
        <button className="btn" type="submit" disabled={submitting}>
          Anlegen
        </button>
      </form>

      {loading && <p>Lade Futter…</p>}
      {error && <div className="error-banner">{error}</div>}

      <div className="list">
        {data?.map((feed) => (
          <div className="list-item" key={feed.id}>
            <div>
              <div className="title">
                {feed.name} {feed.manufacturer ? `· ${feed.manufacturer}` : ""}
              </div>
              <div className="subtitle">
                {feed.energy_mj_per_kg} MJ/kg
                {feed.crude_protein_pct ? ` · Protein ${feed.crude_protein_pct}%` : ""}
                {feed.crude_fiber_pct ? ` · Faser ${feed.crude_fiber_pct}%` : ""}
                {feed.crude_fat_pct ? ` · Fett ${feed.crude_fat_pct}%` : ""}
                {feed.container_capacity_grams ? ` · Behälter ${feed.container_capacity_grams} g` : ""}
              </div>
            </div>
            <button className="btn danger small" onClick={() => handleDelete(feed.id)}>
              Löschen
            </button>
          </div>
        ))}
        {data && data.length === 0 && <p className="empty-state">Noch kein Futter angelegt.</p>}
      </div>
    </div>
  );
}
