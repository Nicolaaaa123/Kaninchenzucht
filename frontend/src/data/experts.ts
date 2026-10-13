/** Experten (Preisrichter) laut Expertenliste Stand März 2026 -- nur Name und
 * Ort, bewusst ohne Kontaktdaten. Dient als Vorschlagsliste im Bewertungs-
 * formular; andere Namen (z.B. frühere Experten) lassen sich frei eintippen. */
export interface SwissExpert {
  name: string;
  place: string;
}

export const SWISS_EXPERTS: SwissExpert[] = [
  { name: "Armin Ackermann", place: "Gossau SG" },
  { name: "Marcel Affolter", place: "Grossaffoltern" },
  { name: "Marc Bärtschi", place: "Brenzikofen" },
  { name: "Flavien Beuchat", place: "Porrentruy" },
  { name: "Klaus Blättler", place: "Wigoltingen" },
  { name: "Daniel Bodenmann", place: "Hüttikon" },
  { name: "Lars Bösch", place: "Ennetbühl" },
  { name: "Michael Braun", place: "Utzigen" },
  { name: "Beat Brudermann", place: "Rumisberg" },
  { name: "Philipp Bucher", place: "Buttisholz" },
  { name: "Markus Durrer", place: "Ebikon" },
  { name: "Marco Eberle", place: "Berg SG" },
  { name: "Marc Eggen", place: "St. Stephan" },
  { name: "Jean-Claude Eicher", place: "Courfaivre" },
  { name: "Markus Eyholzer", place: "Brig-Glis" },
  { name: "Bruno Ferreira", place: "Couvet" },
  { name: "Simon Foser", place: "Balzers" },
  { name: "Monika Furrer", place: "Läufelfingen" },
  { name: "Michel Gruaz", place: "Vufflens-la-Ville" },
  { name: "Jana Hamann", place: "Röschenz" },
  { name: "Urban Hamann", place: "Laufen" },
  { name: "Fabian Herren", place: "Wimmis" },
  { name: "Sandra Heuberger", place: "Bözen" },
  { name: "Franz Käser", place: "Köllikon" },
  { name: "Roland Lüthi", place: "Benzenschwil" },
  { name: "Walter Mäder", place: "Villmergen" },
  { name: "Jean-Luc Maillard", place: "Porsel" },
  { name: "Jean-Louis Meyer", place: "Engollon" },
  { name: "Luc Page", place: "Avry-sur-Matran" },
  { name: "Markus Pfiffner", place: "Mels" },
  { name: "Stefan Röthlisberger", place: "Bleiken" },
  { name: "Beat Schweizer", place: "Müllheim Dorf" },
  { name: "Mirko Solari", place: "Faido" },
  { name: "Martin Urech", place: "Meisterschwanden" },
];
