import { QRCodeSVG } from "qrcode.react";
import { api } from "../api/client";
import { useAsync } from "../hooks/useAsync";

export function AnimalLabels() {
  const animals = useAsync(() => api.animals.list({ status: "active" }), []);

  return (
    <div>
      <div className="toolbar no-print">
        <button className="btn" onClick={() => window.print()}>
          Alle drucken
        </button>
      </div>
      <p className="hint no-print" style={{ marginBottom: 12 }}>
        {animals.data?.length ?? 0} Etiketten (aktive Tiere) — zum Ausschneiden und am Stallkäfig
        anbringen. Scannen mit der Handy-Kamera führt direkt zur Tierseite.
      </p>

      <div className="label-sheet">
        {animals.data?.map((a) => (
          <div className="label-card" key={a.id}>
            <QRCodeSVG value={`${window.location.origin}/tiere/${a.id}`} size={80} />
            <div className="label-text">
              <div className="chip">{a.chip_number}</div>
              {a.name && <div className="meta">{a.name}</div>}
              {a.breed && <div className="meta">{a.breed.name}</div>}
            </div>
          </div>
        ))}
      </div>
      {animals.data && animals.data.length === 0 && <p className="empty-state">Keine aktiven Tiere.</p>}
    </div>
  );
}
