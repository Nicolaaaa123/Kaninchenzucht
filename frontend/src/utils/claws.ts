export const CLAWS_INTERVAL_MONTHS = 3;

export interface ClawsStatus {
  nextDue: string | null; // ISO-Datum (YYYY-MM-DD)
  daysUntilDue: number | null; // negativ = überfällig
}

function toIso(d: Date): string {
  const m = String(d.getMonth() + 1).padStart(2, "0");
  const day = String(d.getDate()).padStart(2, "0");
  return `${d.getFullYear()}-${m}-${day}`;
}

/** Nächster Krallenschnitt: letzter Schnitt + 3 Kalendermonate (am Monatsende
 * auf den letzten Tag des Zielmonats begrenzt, z.B. 30.11. -> 28.2.). */
export function clawsStatus(lastTrimmed: string | null, today = new Date()): ClawsStatus {
  if (!lastTrimmed) return { nextDue: null, daysUntilDue: null };
  const [y, m, d] = lastTrimmed.split("-").map(Number);
  const target = new Date(y, m - 1 + CLAWS_INTERVAL_MONTHS, 1);
  const lastDay = new Date(target.getFullYear(), target.getMonth() + 1, 0).getDate();
  target.setDate(Math.min(d, lastDay));
  const startOfToday = new Date(today.getFullYear(), today.getMonth(), today.getDate());
  const days = Math.round((target.getTime() - startOfToday.getTime()) / 86_400_000);
  return { nextDue: toIso(target), daysUntilDue: days };
}

export function todayIso(): string {
  return toIso(new Date());
}

/** YYYY-MM-DD -> TT.MM.JJJJ */
export function formatDate(iso: string): string {
  const [y, m, d] = iso.split("-");
  return `${d}.${m}.${y}`;
}
