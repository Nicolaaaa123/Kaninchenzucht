import { useState } from "react";
import { api } from "../api/client";
import type { UserUsage } from "../api/types";

function limitText(limit: number | null): string {
  if (limit === null) return "unbegrenzt";
  if (limit === 0) return "aus";
  return String(limit);
}

function toLimit(value: string): number | null {
  const trimmed = value.trim();
  return trimmed === "" ? null : Number(trimmed);
}

/** Admin: Verbrauch dieses Monats und Monatslimits eines Logins (Scans, KI-Anfragen). */
export function UserLimits({ row, onSaved }: { row: UserUsage; onSaved: () => void }) {
  const [editing, setEditing] = useState(false);
  const [scan, setScan] = useState("");
  const [chat, setChat] = useState("");
  const [saving, setSaving] = useState(false);
  const [error, setError] = useState<string | null>(null);

  function start() {
    setScan(row.scan_limit === null ? "" : String(row.scan_limit));
    setChat(row.chat_limit === null ? "" : String(row.chat_limit));
    setError(null);
    setEditing(true);
  }

  async function save() {
    const scanLimit = toLimit(scan);
    const chatLimit = toLimit(chat);
    for (const v of [scanLimit, chatLimit]) {
      if (v !== null && (!Number.isInteger(v) || v < 0)) {
        setError("Bitte ganze Zahlen ab 0 eintragen (leer = unbegrenzt).");
        return;
      }
    }
    setSaving(true);
    setError(null);
    try {
      await api.usage.setLimits(row.user_id, { scan_limit: scanLimit, chat_limit: chatLimit });
      setEditing(false);
      onSaved();
    } catch (err) {
      setError((err as Error).message);
    } finally {
      setSaving(false);
    }
  }

  return (
    <div style={{ marginTop: 8 }}>
      <div className="hint" style={{ display: "flex", justifyContent: "space-between", gap: 8, flexWrap: "wrap" }}>
        <span>
          Diesen Monat: Scans {row.scan_used} / {limitText(row.scan_limit)} · KI-Anfragen {row.chat_used} /{" "}
          {limitText(row.chat_limit)}
          {row.input_tokens + row.output_tokens > 0 &&
            ` · Tokens ${row.input_tokens.toLocaleString("de-CH")} ein / ${row.output_tokens.toLocaleString("de-CH")} aus`}
        </span>
        <button type="button" className="btn secondary small" onClick={() => (editing ? setEditing(false) : start())}>
          Kontingent ändern
        </button>
      </div>
      {editing && (
        <div style={{ marginTop: 8 }}>
          {error && <div className="error-banner">{error}</div>}
          <div className="form-grid" style={{ alignItems: "end" }}>
            <div className="field">
              <label htmlFor={`lim-scan-${row.user_id}`}>Scans pro Monat</label>
              <input
                id={`lim-scan-${row.user_id}`}
                type="number"
                min={0}
                inputMode="numeric"
                placeholder="unbegrenzt"
                value={scan}
                onChange={(e) => setScan(e.target.value)}
              />
            </div>
            <div className="field">
              <label htmlFor={`lim-chat-${row.user_id}`}>KI-Anfragen pro Monat</label>
              <input
                id={`lim-chat-${row.user_id}`}
                type="number"
                min={0}
                inputMode="numeric"
                placeholder="unbegrenzt"
                value={chat}
                onChange={(e) => setChat(e.target.value)}
              />
            </div>
            <button type="button" className="btn" onClick={save} disabled={saving}>
              {saving ? "Speichere…" : "Speichern"}
            </button>
          </div>
          <span className="hint">Leer = unbegrenzt, 0 = nicht freigeschaltet. Der Verbrauch setzt sich jeden Monatsersten zurück.</span>
        </div>
      )}
    </div>
  );
}
