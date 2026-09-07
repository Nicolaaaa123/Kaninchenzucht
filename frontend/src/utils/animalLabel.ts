/** Anzeigename eines Tieres -- Chip-Nummer ist inzwischen optional (v.a. bei
 * frisch angelegten Würfen), Tiere ohne Chip zeigen dann Namen/Fallback statt
 * "null". */
export function animalLabel(a: { chip_number?: string | null; name?: string | null }): string {
  if (a.chip_number && a.name) return `${a.chip_number} · ${a.name}`;
  if (a.chip_number) return a.chip_number;
  if (a.name) return a.name;
  return "ohne Chip-Nr.";
}
