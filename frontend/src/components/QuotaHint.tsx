import { api } from "../api/client";
import { useAsync } from "../hooks/useAsync";

interface QuotaHintProps {
  kind: "scan" | "chat";
  /** Ändert sich nach jeder Nutzung, damit der Stand neu geladen wird. */
  refreshKey?: number;
}

const LABELS = { scan: "Scans", chat: "KI-Anfragen" } as const;

/** Zeigt dem Login, wie viel vom monatlichen KI-Kontingent schon verbraucht ist.
 * Bei unbegrenztem Kontingent (z.B. Administrator) bleibt es unsichtbar. */
export function QuotaHint({ kind, refreshKey = 0 }: QuotaHintProps) {
  const usage = useAsync(() => api.usage.me(), [refreshKey]);
  if (!usage.data) return null;

  const used = kind === "scan" ? usage.data.scan_used : usage.data.chat_used;
  const limit = kind === "scan" ? usage.data.scan_limit : usage.data.chat_limit;
  if (limit === null) return null;

  if (limit <= 0) {
    return (
      <p className="hint" style={{ marginBottom: 12 }}>
        {LABELS[kind]} sind für dein Login nicht freigeschaltet — bitte beim Administrator nachfragen.
      </p>
    );
  }
  const left = Math.max(limit - used, 0);
  return (
    <p className="hint" style={{ marginBottom: 12 }}>
      Kontingent diesen Monat: {used} von {limit} {LABELS[kind]} genutzt ({left} übrig).
    </p>
  );
}
