import { Link } from "react-router-dom";
import { QRCodeSVG } from "qrcode.react";
import { api } from "../api/client";
import { useAsync } from "../hooks/useAsync";

export function StallLabels() {
  const stalls = useAsync(() => api.stalls.list(), []);

  return (
    <div>
      <Link className="back-link no-print" to="/stallplan">
        ← Zurück zum Stallplan
      </Link>
      <div className="toolbar no-print">
        <button className="btn" onClick={() => window.print()}>
          Alle drucken
        </button>
      </div>
      <p className="hint no-print" style={{ marginBottom: 12 }}>
        QR-Etiketten in der Anordnung der Ställe — zum Ausschneiden und direkt an der jeweiligen Box
        anbringen. Jede Box behält ihre Position wie im Stallplan.
      </p>

      {stalls.loading && <p className="no-print">Lade…</p>}

      {stalls.data?.map((stall) => (
        <div key={stall.id} className="stall-label-section">
          <h2>
            {stall.label} <span className="hint">({stall.rows}×{stall.columns})</span>
          </h2>
          <div
            className="stall-label-grid"
            style={{
              gridTemplateColumns: `repeat(${stall.columns}, 150px)`,
              gridTemplateRows: `repeat(${stall.rows}, auto)`,
            }}
          >
            {stall.boxes.map((box) => {
              const occupant = box.occupants[0];
              return (
                <div
                  className={`label-card stall-label-card ${occupant ? "" : "empty"}`}
                  key={box.id}
                  style={{ gridRow: box.row_index + 1, gridColumn: box.col_index + 1 }}
                >
                  {occupant ? (
                    <>
                      <QRCodeSVG value={`${window.location.origin}/tiere/${occupant.id}`} size={64} />
                      <div className="label-text">
                        <div className="chip">{occupant.chip_number}</div>
                        {occupant.name && <div className="meta">{occupant.name}</div>}
                        <div className="meta">Box {box.label}</div>
                      </div>
                    </>
                  ) : (
                    <div className="label-text">
                      <div className="meta">Box {box.label}</div>
                      <div className="meta">frei</div>
                    </div>
                  )}
                </div>
              );
            })}
          </div>
        </div>
      ))}
      {stalls.data && stalls.data.length === 0 && <p className="empty-state">Noch keine Ställe angelegt.</p>}
    </div>
  );
}
