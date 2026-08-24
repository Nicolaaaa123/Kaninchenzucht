export function coiLabel(coefficient: number): string {
  return `${(coefficient * 100).toFixed(2)}%`;
}

// Richtwerte: < Halbgeschwister-Niveau grün, bis Vollgeschwister/Eltern-Kind gelb, darüber rot.
export function coiRiskClass(coefficient: number): string {
  if (coefficient >= 0.125) return "status-deceased"; // rot
  if (coefficient >= 0.03125) return "status-sold"; // gelb
  return ""; // grün (default badge)
}
