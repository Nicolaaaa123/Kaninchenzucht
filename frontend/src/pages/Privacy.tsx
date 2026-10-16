import { Link } from "react-router-dom";

/** Datenschutz-Information. Öffentlich erreichbar (auch ohne Anmeldung), damit sie
 * schon vor dem Login einsehbar ist. */
export function Privacy({ standalone = false }: { standalone?: boolean }) {
  const content = (
    <div>
      <Link className="back-link" to={standalone ? "/" : "/konto"}>
        {standalone ? "← Zur Anmeldung" : "← Zurück zum Konto"}
      </Link>
      <h1>Datenschutz-Information</h1>
      <p className="hint" style={{ marginBottom: 16 }}>
        Stand: Oktober 2026. Diese Seite ist ein privates Hobbyprojekt ohne Gewinnabsicht und ohne Gewähr
        auf Verfügbarkeit.
      </p>

      <div className="card section">
        <h2>Wer ist verantwortlich?</h2>
        <p>
          Betrieben wird diese Seite vom Administrator (dem Betreiber), der dir dein Login mitgeteilt hat.
          Fragen zum Datenschutz richtest du direkt an ihn, auf dem Weg, auf dem du dein Login erhalten hast.
        </p>
      </div>

      <div className="card section">
        <h2>Welche Daten werden gespeichert?</h2>
        <ul>
          <li>
            <strong>Login:</strong> Benutzername, optional ein Anzeigename und dein Passwort — das Passwort
            nur in verschlüsselter Form (Hash), niemand kann es lesen.
          </li>
          <li>
            <strong>Zuchtdaten, die du selbst eingibst:</strong> Tiere (z. B. Name, Chip-Nummer, Geburtsdatum),
            Gewichte, Würfe, Ställe, Futter, Notizen sowie Bewertungskarten mit Punkten, Ausstellung, Experten
            und — soweit du sie erfasst — Namen und Adressen von Ausstellern.
          </li>
          <li>
            <strong>KI-Nutzung:</strong> pro Login der Zeitpunkt sowie die Anzahl der Scans und KI-Anfragen und
            die dabei verbrauchte Datenmenge, damit der Betreiber das Kontingent steuern kann.
          </li>
        </ul>
        <p className="hint">
          Erfasse bitte nur Angaben, die du für die Zuchtverwaltung wirklich brauchst, und bei Dritten (z. B.
          Ausstellern) nur, was auf der Bewertungskarte steht.
        </p>
      </div>

      <div className="card section">
        <h2>Cookies und lokaler Speicher</h2>
        <p>
          Es gibt genau ein Cookie (<code>session_token</code>). Es hält dich angemeldet (bis zu einem Jahr,
          bzw. bis du dich abmeldest) und ist technisch notwendig. Zusätzlich merkt sich dein Browser lokal die
          Darstellung (hell/dunkel) und Filter in der Tierliste. Es gibt kein Tracking, keine Werbung und keine
          Analyse-Dienste.
        </p>
      </div>

      <div className="card section">
        <h2>Wer verarbeitet die Daten?</h2>
        <ul>
          <li>
            <strong>Render</strong> — Betrieb der Anwendung (Server).
          </li>
          <li>
            <strong>Neon</strong> — Datenbank, in der alle Daten gespeichert sind (Region Frankfurt, EU).
          </li>
          <li>
            <strong>GitHub</strong> — Programmcode und die automatische nächtliche Sicherung der Datenbank.
          </li>
          <li>
            <strong>Microsoft OneDrive</strong> — Ablage der Sicherungskopien im privaten Speicher des Betreibers
            (werden nach 30 Tagen automatisch gelöscht). Die Sicherung enthält die Daten aller Logins.
          </li>
          <li>
            <strong>UptimeRobot</strong> — ruft regelmässig nur die öffentliche Adresse der Seite auf, damit sie
            schnell erreichbar bleibt; es werden keine Daten übermittelt.
          </li>
          <li>
            <strong>Anthropic (USA)</strong> — nur wenn du die KI-Funktionen nutzt, siehe unten.
          </li>
        </ul>
        <p>Eine Weitergabe an weitere Dritte findet nicht statt.</p>
      </div>

      <div className="card section">
        <h2>KI-Funktionen (Scan und Zucht-Assistent)</h2>
        <ul>
          <li>
            <strong>Bewertungskarten-Scan:</strong> Das hochgeladene Foto wird zum Auslesen an Anthropic in den
            USA übermittelt. Bei uns wird das Foto nicht gespeichert, dauerhaft bleiben nur die von dir
            bestätigten Zahlen und Texte.
          </li>
          <li>
            <strong>Zucht-Assistent (Chat):</strong> Deine Frage und die zur Antwort nötigen Daten aus deinem
            Bestand (z. B. Tiernamen, Chip-Nummern, Bewertungen) werden an Anthropic übermittelt.
          </li>
        </ul>
        <p>
          Die KI-Funktionen sind freiwillig und nur nutzbar, wenn der Betreiber sie für dein Login freigeschaltet
          hat. Bitte lade keine Fotos hoch, auf denen Personen erkennbar sind, und schreibe keine sensiblen
          persönlichen Angaben in den Chat. Für die Verarbeitung durch Anthropic gelten deren eigene
          Bedingungen und Datenschutzbestimmungen.
        </p>
      </div>

      <div className="card section">
        <h2>Wer sieht deine Daten?</h2>
        <p>
          Jedes Login sieht nur seinen eigenen Bestand (bzw. den gemeinsamen, falls der Betreiber ein Login im
          selben Bestand angelegt hat). Der Betreiber hat technisch Zugriff auf alle Daten, kann Logins anlegen,
          Passwörter zurücksetzen und die KI-Kontingente festlegen.
        </p>
      </div>

      <div className="card section">
        <h2>Aufbewahrung, Löschung und deine Rechte</h2>
        <p>
          Deine Daten bleiben gespeichert, solange dein Login besteht. Du kannst jederzeit beim Betreiber
          Auskunft über deine Daten, deren Berichtigung oder die Löschung deines Logins samt aller Daten
          verlangen. Sicherungskopien werden spätestens nach 30 Tagen automatisch gelöscht.
        </p>
      </div>
    </div>
  );

  if (!standalone) return content;
  return <div style={{ maxWidth: 760, margin: "0 auto", padding: "20px 16px 40px" }}>{content}</div>;
}
