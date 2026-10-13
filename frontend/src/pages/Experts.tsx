import { useMemo, useState } from "react";
import { Link } from "react-router-dom";
import { api } from "../api/client";
import { useAsync } from "../hooks/useAsync";
import { animalLabel } from "../utils/animalLabel";

type SortKey = "count" | "avg";

export function Experts() {
  const overview = useAsync(() => api.stats.experts(), []);
  const [sortKey, setSortKey] = useState<SortKey>("count");

  const experts = useMemo(() => {
    const list = [...(overview.data?.experts ?? [])];
    if (sortKey === "avg") {
      list.sort((a, b) => (b.avg_total_score ?? -1) - (a.avg_total_score ?? -1) || b.evaluation_count - a.evaluation_count);
    }
    return list;
  }, [overview.data, sortKey]);

  return (
    <div>
      <Link className="back-link" to="/">
        ← Zurück zur Übersicht
      </Link>
      <h1>Experten-Auswertung</h1>
      <p className="hint" style={{ marginBottom: 16 }}>
        Zeigt, welcher Experte wie viele deiner Tiere bewertet hat und wie er im Durchschnitt
        bewertet hat — gesamt und je Position. Klicke auf einen Experten für die Details und die
        einzelnen Karten.
      </p>

      <div className="toolbar">
        <select value={sortKey} onChange={(e) => setSortKey(e.target.value as SortKey)}>
          <option value="count">Sortierung: Anzahl Karten</option>
          <option value="avg">Sortierung: Ø Gesamtpunkte</option>
        </select>
      </div>

      {overview.loading && <p>Lade…</p>}
      {overview.error && <div className="error-banner">{overview.error}</div>}

      {overview.data && overview.data.without_expert_count > 0 && (
        <p className="hint" style={{ marginBottom: 12 }}>
          {overview.data.without_expert_count} Bewertung(en) ohne Experten-Angabe sind hier nicht
          enthalten — den Experten kannst du in der jeweiligen Bewertung beim Tier nachtragen.
        </p>
      )}

      {experts.map((x) => (
        <details className="card section expert-card" key={x.expert_name}>
          <summary className="expert-summary">
            <strong>{x.expert_name}</strong>
            <span className="hint">
              {x.evaluation_count} Karte{x.evaluation_count === 1 ? "" : "n"} · {x.animal_count} Tier
              {x.animal_count === 1 ? "" : "e"}
            </span>
            <span className="expert-avg">{x.avg_total_score != null ? `Ø ${x.avg_total_score} Pkt.` : "–"}</span>
          </summary>

          <table style={{ marginTop: 12 }}>
            <tbody>
              {x.positions.map((p) => (
                <tr key={p.position_number}>
                  <th>
                    {p.position_number}. {p.category_label}
                  </th>
                  <td>
                    Ø {p.avg_points} / {p.max_points}
                  </td>
                </tr>
              ))}
            </tbody>
          </table>

          <div className="list" style={{ marginTop: 12 }}>
            {x.evaluations.map((e) => (
              <Link className="list-item" to={`/tiere/${e.animal_id}`} key={e.evaluation_id}>
                <span>
                  {animalLabel({ chip_number: e.animal_chip_number, name: e.animal_name })}
                  <span className="subtitle">
                    {" "}
                    · {e.evaluated_on}
                    {e.show_name ? ` · ${e.show_name}` : ""}
                  </span>
                </span>
                <strong>{e.total_score ?? "–"}</strong>
              </Link>
            ))}
          </div>
        </details>
      ))}

      {overview.data && overview.data.experts.length === 0 && (
        <p className="empty-state">
          Noch keine Experten erfasst. Trage bei einer Bewertung das Feld „Experte“ ein.
        </p>
      )}
    </div>
  );
}
