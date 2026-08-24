# Kaninchenzucht-Management

Webbasierte App zur Verwaltung einer Kaninchenzucht (~200 Tiere). Monorepo mit
FastAPI-Backend, React/TypeScript-Frontend und PostgreSQL.

## Struktur

- `backend/` – FastAPI, SQLAlchemy, Alembic
- `frontend/` – React + Vite + TypeScript, mobile-first
- `docker-compose.yml` – lokale PostgreSQL-Instanz

## Voraussetzungen

- Python 3.12, Node.js LTS, Docker Desktop (mit WSL2)

## Setup

### 1. Datenbank starten

```bash
docker compose up -d
```

### 2. Backend

```bash
cd backend
python -m venv venv
venv\Scripts\activate
pip install -r requirements.txt
copy .env.example .env
alembic upgrade head
python -m app.seed_breeds
uvicorn app.main:app --reload
```

Läuft dann auf http://localhost:8000 (Swagger-UI unter `/docs`).

`app.seed_breeds` befüllt die Rassentabelle mit den 42 Rassen aus dem Standard
2015 (Rassekaninchen Schweiz), inkl. Gewichtsvorgaben und offizieller
Bewertungsskala (`backend/app/data/ch_standard_breeds.json`). Bereits
vorhandene Rassen werden übersprungen, das Skript ist also gefahrlos erneut
ausführbar.

### 3. Frontend

```bash
cd frontend
npm install
copy .env.example .env
npm run dev
```

Läuft dann auf http://localhost:5173.

### 4. Bewertungskarten-Scan aktivieren (optional)

Für Phase 5 (Foto-Scan der Bewertungskarte) einen API-Key von
[console.anthropic.com](https://console.anthropic.com) in `backend/.env` als
`ANTHROPIC_API_KEY=...` eintragen und das Backend neu starten. Jeder Scan
verursacht Kosten auf diesem Key (Claude Opus 5 Vision, grob wenige Cent pro
Scan). Ohne Key zeigt die Scan-Seite einen klaren Hinweis statt eines Fehlers.

## Stand des Projekts

**Fertig:**
- Datenmodell & CRUD: Rassen, Stallreihen/Boxen, Tiere, Gewichtshistorie,
  Bewertungen, Futter
- **Schweizer Standard 2015** (Rassekaninchen Schweiz): alle 42 Rassen mit
  offiziellem Mindest-/Ideal-/Höchstgewicht und rassespezifischer
  Bewertungsskala (8 Positionen, 100 Punkte, Wortwerte-Punktetabelle)
- Identifikation über **Chip-Nummer** (Ohrmarke optional als Zusatzfeld)
- **Stallplan als visuelles Raster**: Ställe mit frei wählbarer Höhe × Breite
  (z.B. 3 Kästen hoch, 2 breit), Reihen/Spalten nachträglich erweiterbar,
  Tierzuordnung direkt in der Box
- **Futterplan**: Futter mit Nährwerten anlegen, Tagesbedarf pro Tier wird aus
  Körpergewicht und Fütterungsstatus berechnet — mit Zielgewicht + Zieldatum
  wird die dafür nötige tägliche Zunahme berücksichtigt, sonst ein
  pauschaler Richtwert je Status (Erhaltung/Wachstum/Trächtigkeit/Säugezeit)
- **Phase 2 – Zuchtbuch**: Stammbaum-Ansicht (mehrere Generationen) und
  automatische Berechnung des Inzuchtkoeffizienten nach Wright (rekursive
  Kinship-Methode), inkl. Verpaarungs-Check mit Risiko-Einstufung
- **Phase 3 – Wachstumskurven & Peak**: rassespezifische Idealgewichtskurve
  (generisches Gompertz-Wachstumsmodell als Startpunkt, pro Rasse mit echten
  Stützpunkten überschreibbar), Ist/Soll-Vergleich je Tier, automatisch
  berechnetes Idealgewichts-Zeitfenster (Peak) inkl. Abgleich mit einem
  manuell gesetzten Zieldatum, sowie eine aggregierte Wachstumskurve
  (Mittelwert + Min/Max-Spanne) über alle Nachkommen eines Zuchttiers
- Responsives Dashboard, modern-minimales Design
- **Phase 4 – QR-Codes**: pro Tier automatisch generiert (verlinkt direkt auf
  die Tierseite), einzeln als Etikett druckbar oder gesammelt für alle
  aktiven Tiere auf einen Bogen
- **Phase 5 – Bewertungskarten-Scan**: Foto hochladen/aufnehmen, Claude Opus 5
  (Vision) liest Ausstellernummer, Rasse, Chip-/Ohrmarken-Nummer, Geschlecht,
  Bewertungspositionen und Gesamtpunktzahl aus; automatischer Abgleich mit
  vorhandenen Tieren per Chip-/Ohrmarken-Nummer — Karten tragen oft nur die
  **letzten paar Stellen**, daher wird bei eindeutigem Treffer automatisch
  zugeordnet und bei Mehrdeutigkeit eine Auswahl der passenden Tiere
  angezeigt, statt zu raten. Alle Werte erscheinen nur als editierbarer
  Vorschlag — nichts wird ungeprüft übernommen. Das Originalfoto wird zum
  Tier archiviert. Benötigt einen eigenen `ANTHROPIC_API_KEY`
  (siehe Setup-Schritt 4).
- **Phase 6 – Tiervergleich & Stärken/Schwächen**: beliebig viele Tiere
  nebeneinander vergleichen (Stammdaten, Gewichtsverlauf überlagert,
  Verwandtschaft zueinander), plus ein Spinnendiagramm pro Zuchttier, das
  zeigt, in welchen Bewertungspositionen die direkten Nachkommen im
  Durchschnitt gut bzw. schwach abschneiden
- **Phase 7 – Paarungsvorschläge**: Rangliste möglicher Partner für ein Tier,
  mit Begründung (Gesamtpunktzahl, Inzuchtkoeffizient der Nachkommen,
  ergänzende Stärken/Schwächen gegenüber den eigenen Bewertungen, plus frei
  wählbare **Fokus-Positionen** — einzelne Bewertungspositionen der Rasse wie
  z.B. nur "Farbe und Glanz", auf die die Rangliste gezielt Wert legt) und
  frei einstellbarer Gewichtung aller vier Kriterien — eine transparente
  Faustregel-Rangliste als Diskussionsgrundlage, kein genetisches
  Zuchtwertmodell
- **Phase 8 – KI-Chat-Assistent**: Chat-Seite, angebunden an Claude Opus 5 mit
  Function Calling auf die eigene Datenbank (Tiere durchsuchen, Tierdetails,
  Geschwister finden, Tiere mit schwacher Bewertung in einer Position finden,
  Rassenliste) — für allgemeine Zuchtfragen antwortet er direkt aus seinem
  Wissen. Benötigt denselben `ANTHROPIC_API_KEY` wie der Bewertungskarten-Scan
  (siehe Setup-Schritt 4).
- **Phase 9 – Bluetooth-Chip-Scanner**: Seite zum Koppeln eines BLE-Lesegeräts
  über die Web-Bluetooth-API (Chrome/Edge, nicht Safari/iOS) — erkannte
  Chip-Nummer wird per Endstellen-Abgleich einem Tier zugeordnet und springt
  automatisch zur Tierseite. Da es kein einheitliches BLE-Protokoll für
  Tierchip-Leser gibt, ist die Service-/Characteristic-UUID direkt auf der
  Seite konfigurierbar (im Browser gespeichert) — inkl. eingebautem
  Diagnose-Modus, der bei einem gekoppelten Gerät die verfügbaren
  Services/Characteristics auflistet, falls die UUID noch unbekannt ist.

Alle 9 Phasen aus dem ursprünglichen Plan sind damit umgesetzt.
