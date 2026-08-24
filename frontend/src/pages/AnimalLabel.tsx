import { Link, useParams } from "react-router-dom";
import { QRCodeSVG } from "qrcode.react";
import { api } from "../api/client";
import { useAsync } from "../hooks/useAsync";

export function AnimalLabel() {
  const { id: routeId } = useParams<{ id: string }>();
  if (!routeId) return null;
  const id: string = routeId;

  const animal = useAsync(() => api.animals.get(id), [id]);
  const url = `${window.location.origin}/tiere/${id}`;

  if (animal.loading) return <p>Lade…</p>;
  if (!animal.data) return null;
  const a = animal.data;

  return (
    <div>
      <Link className="back-link no-print" to={`/tiere/${id}`}>
        ← Zurück zum Tier
      </Link>
      <div className="toolbar no-print">
        <button className="btn" onClick={() => window.print()}>
          Drucken
        </button>
      </div>

      <div className="label-card" style={{ maxWidth: 320 }}>
        <QRCodeSVG value={url} size={110} />
        <div className="label-text">
          <div className="chip">{a.chip_number}</div>
          {a.name && <div className="meta">{a.name}</div>}
          {a.breed && <div className="meta">{a.breed.name}</div>}
          {a.cage_box_label && <div className="meta">{a.cage_box_label}</div>}
        </div>
      </div>
    </div>
  );
}
