import { useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { useAsync } from "../hooks/useAsync";
import type { Stall } from "../api/types";

export function StallPlan() {
  const pages = useAsync(() => api.stallPages.list(), []);
  const stalls = useAsync(() => api.stalls.list(), []);
  const unassigned = useAsync(() => api.animals.list({ status: "active" }), []);

  const [activePageId, setActivePageId] = useState<string | "all" | "none">("all");
  const [newPageLabel, setNewPageLabel] = useState("");
  const [showPageForm, setShowPageForm] = useState(false);

  const [label, setLabel] = useState("");
  const [rows, setRows] = useState(3);
  const [columns, setColumns] = useState(2);
  const [submitting, setSubmitting] = useState(false);
  const [formError, setFormError] = useState<string | null>(null);
  const [deleteError, setDeleteError] = useState<string | null>(null);

  async function handleCreatePage(e: React.FormEvent) {
    e.preventDefault();
    if (!newPageLabel.trim()) return;
    const page = await api.stallPages.create({ label: newPageLabel.trim(), position: pages.data?.length ?? 0 });
    setNewPageLabel("");
    setShowPageForm(false);
    await pages.reload();
    setActivePageId(page.id);
  }

  async function handleDeletePage(pageId: string) {
    if (!confirm("Diese Seite löschen? Die Ställe darauf bleiben erhalten, werden aber keiner Seite mehr zugeordnet.")) return;
    await api.stallPages.remove(pageId);
    setActivePageId("all");
    pages.reload();
    stalls.reload();
  }

  async function handleCreateStall(e: React.FormEvent) {
    e.preventDefault();
    if (!label.trim() || rows < 1 || columns < 1) return;
    setSubmitting(true);
    setFormError(null);
    try {
      await api.stalls.create({
        label: label.trim(),
        rows,
        columns,
        position: stalls.data?.length ?? 0,
        page_id: activePageId === "all" || activePageId === "none" ? null : activePageId,
      });
      setLabel("");
      setRows(3);
      setColumns(2);
      stalls.reload();
    } catch (err) {
      setFormError((err as Error).message);
    } finally {
      setSubmitting(false);
    }
  }

  async function handleDeleteStall(stallId: string) {
    if (!confirm("Diesen Stall inkl. aller Boxen wirklich löschen?")) return;
    setDeleteError(null);
    try {
      await api.stalls.remove(stallId);
      stalls.reload();
    } catch (err) {
      setDeleteError((err as Error).message);
    }
  }

  async function handleAddRow(stall: Stall) {
    await api.stalls.addRow(stall.id);
    stalls.reload();
  }

  async function handleAddColumn(stall: Stall) {
    await api.stalls.addColumn(stall.id);
    stalls.reload();
  }

  async function handleAssign(boxId: string, animalId: string) {
    if (!animalId) return;
    await api.animals.update(animalId, { cage_box_id: boxId });
    stalls.reload();
    unassigned.reload();
  }

  async function handleUnassign(animalId: string) {
    await api.animals.update(animalId, { cage_box_id: null });
    stalls.reload();
    unassigned.reload();
  }

  const freeAnimals = unassigned.data ?? [];
  const visibleStalls = (stalls.data ?? []).filter((s) => {
    if (activePageId === "all") return true;
    if (activePageId === "none") return !s.page_id;
    return s.page_id === activePageId;
  });

  return (
    <div>
      <div className="toolbar" style={{ justifyContent: "space-between" }}>
        <h1 style={{ margin: 0 }}>Stallplan</h1>
        <Link className="btn secondary" to="/stallplan/etiketten">
          QR-Etiketten nach Stall drucken
        </Link>
      </div>

      <div className="page-tabs">
        <button className={`page-tab ${activePageId === "all" ? "active" : ""}`} onClick={() => setActivePageId("all")}>
          Alle
        </button>
        {pages.data?.map((p) => (
          <button
            key={p.id}
            className={`page-tab ${activePageId === p.id ? "active" : ""}`}
            onClick={() => setActivePageId(p.id)}
          >
            {p.label}
          </button>
        ))}
        <button className={`page-tab ${activePageId === "none" ? "active" : ""}`} onClick={() => setActivePageId("none")}>
          Ohne Seite
        </button>
        <button className="btn secondary small" onClick={() => setShowPageForm((s) => !s)}>
          + Seite
        </button>
        {activePageId !== "all" && activePageId !== "none" && (
          <button className="btn danger small" onClick={() => handleDeletePage(activePageId)}>
            Seite löschen
          </button>
        )}
      </div>

      {showPageForm && (
        <form className="card section" onSubmit={handleCreatePage}>
          <div className="toolbar" style={{ marginBottom: 0 }}>
            <input
              type="text"
              placeholder="z.B. Scheune, Aussenstall…"
              value={newPageLabel}
              onChange={(e) => setNewPageLabel(e.target.value)}
              style={{ flex: 1 }}
            />
            <button className="btn" type="submit">
              Anlegen
            </button>
          </div>
        </form>
      )}

      <form className="card section" onSubmit={handleCreateStall}>
        <h2>Neuen Stall anlegen</h2>
        <p className="hint" style={{ marginBottom: 12 }}>
          Gib an, wie viele Boxen der Stall hoch und breit ist — z.B. 3 Kästen hoch, 2 breit. Mehrere
          Ställe lassen sich so nebeneinander anlegen; weitere Reihen/Spalten kannst du danach
          jederzeit ergänzen. Der Stall wird auf der aktuell gewählten Seite angelegt.
        </p>
        {formError && <div className="error-banner">{formError}</div>}
        <div className="form-grid">
          <div className="field">
            <label htmlFor="stall-label">Bezeichnung</label>
            <input
              id="stall-label"
              type="text"
              placeholder="z.B. Sechserstall Nord"
              value={label}
              onChange={(e) => setLabel(e.target.value)}
              required
            />
          </div>
          <div className="field">
            <label htmlFor="stall-rows">Kästen hoch (Reihen)</label>
            <input
              id="stall-rows"
              type="number"
              min={1}
              max={12}
              value={rows}
              onChange={(e) => setRows(Number(e.target.value))}
            />
          </div>
          <div className="field">
            <label htmlFor="stall-columns">Kästen breit (Spalten)</label>
            <input
              id="stall-columns"
              type="number"
              min={1}
              max={12}
              value={columns}
              onChange={(e) => setColumns(Number(e.target.value))}
            />
          </div>
        </div>
        <button className="btn" type="submit" disabled={submitting}>
          Stall anlegen
        </button>
      </form>

      {stalls.loading && <p>Lade Stallplan…</p>}
      {stalls.error && <div className="error-banner">{stalls.error}</div>}
      {deleteError && <div className="error-banner">{deleteError}</div>}

      <div className="stalls-container">
        {visibleStalls.map((stall) => (
          <div className="stall-row" key={stall.id}>
            <div className="stall-row-header">
              <h2>
                {stall.label} <span className="hint">({stall.rows}×{stall.columns})</span>
              </h2>
            </div>
            <div className="toolbar" style={{ marginBottom: 8 }}>
              <button className="btn secondary small" onClick={() => handleAddRow(stall)}>
                + Reihe
              </button>
              <button className="btn secondary small" onClick={() => handleAddColumn(stall)}>
                + Spalte
              </button>
              <button className="btn danger small" onClick={() => handleDeleteStall(stall.id)}>
                Löschen
              </button>
            </div>
            <div
              className="stall-grid"
              style={{
                gridTemplateColumns: `repeat(${stall.columns}, 130px)`,
                gridTemplateRows: `repeat(${stall.rows}, auto)`,
                gridAutoFlow: "row",
              }}
            >
              {stall.boxes.map((box) => {
                const occupant = box.occupants[0];
                return (
                  <div
                    className={`cage-box ${occupant ? "occupied" : ""}`}
                    key={box.id}
                    style={{ gridRow: box.row_index + 1, gridColumn: box.col_index + 1 }}
                  >
                    <div>
                      <div className="box-label">Box {box.label}</div>
                      {occupant ? (
                        <>
                          <Link to={`/tiere/${occupant.id}`} className="occupant">
                            {occupant.chip_number} {occupant.name ? `· ${occupant.name}` : ""}
                          </Link>
                          <div className="occupant-meta">{occupant.breed?.name ?? ""}</div>
                          {occupant.daily_feed_grams && (
                            <div className="feed-hint">
                              {occupant.daily_feed_grams} g/Tag
                              {occupant.container_fill_pct != null && ` · ${occupant.container_fill_pct}% Behälter`}
                            </div>
                          )}
                        </>
                      ) : (
                        <div className="occupant-meta">frei</div>
                      )}
                    </div>
                    {occupant ? (
                      <button className="btn secondary small" onClick={() => handleUnassign(occupant.id)}>
                        Entfernen
                      </button>
                    ) : (
                      <select
                        value=""
                        onChange={(e) => handleAssign(box.id, e.target.value)}
                        style={{ fontSize: "0.78rem", padding: "5px 6px" }}
                      >
                        <option value="">Tier zuordnen…</option>
                        {freeAnimals.map((a) => (
                          <option key={a.id} value={a.id}>
                            {a.chip_number} {a.name ? `· ${a.name}` : ""}
                          </option>
                        ))}
                      </select>
                    )}
                  </div>
                );
              })}
            </div>
          </div>
        ))}
      </div>
      {stalls.data && visibleStalls.length === 0 && <p className="empty-state">Noch keine Ställe auf dieser Seite.</p>}
    </div>
  );
}
