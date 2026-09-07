/** Berechnet eine "saubere" Y-Achse (runde Ticks, kein Ranschmiegen an 0),
 * damit kleine Unterschiede sichtbar werden ohne krumme/fehlerhafte
 * Beschriftungen durch rechts eigene automatische Tick-Berechnung. */
export function niceAxisBounds(min: number, max: number, targetTicks = 5): { domain: [number, number]; ticks: number[] } {
  if (!Number.isFinite(min) || !Number.isFinite(max)) {
    return { domain: [0, 1], ticks: [0, 1] };
  }
  if (min === max) {
    const step = Math.max(Math.abs(min) * 0.1, 1);
    min -= step;
    max += step;
  }

  const rawStep = (max - min) / Math.max(targetTicks - 1, 1);
  const pow10 = Math.pow(10, Math.floor(Math.log10(rawStep)));
  const norm = rawStep / pow10;
  let niceStep: number;
  if (norm <= 1) niceStep = 1 * pow10;
  else if (norm <= 2) niceStep = 2 * pow10;
  else if (norm <= 5) niceStep = 5 * pow10;
  else niceStep = 10 * pow10;

  const lo = Math.floor(min / niceStep) * niceStep;
  const hi = Math.ceil(max / niceStep) * niceStep;

  const ticks: number[] = [];
  const decimals = Math.max(0, -Math.floor(Math.log10(niceStep)) + 2);
  const round = (v: number) => Math.round(v * 10 ** decimals) / 10 ** decimals;
  for (let t = lo; t <= hi + niceStep * 0.001; t += niceStep) {
    ticks.push(round(t));
  }

  return { domain: [round(lo), round(hi)], ticks };
}
