import { useState } from "react";
import { useNavigate } from "react-router-dom";
import { api } from "../api/client";
import {
  COMMON_BLE_SERVICE_UUIDS,
  isBluetoothReaderConfigured,
  loadBluetoothReaderConfig,
  saveBluetoothReaderConfig,
  type BluetoothReaderConfig,
} from "../config/bluetoothReader";

interface DiscoveredService {
  uuid: string;
  characteristics: { uuid: string; properties: string[] }[];
}

function decodeValue(value: DataView): string {
  const bytes = new Uint8Array(value.buffer, value.byteOffset, value.byteLength);
  const text = new TextDecoder("utf-8")
    .decode(bytes)
    .replace(/[^\x20-\x7e]/g, "")
    .trim();
  if (text) return text;
  return Array.from(bytes)
    .map((b) => b.toString(16).padStart(2, "0"))
    .join("");
}

export function BluetoothScan() {
  const navigate = useNavigate();
  const supported = typeof navigator !== "undefined" && "bluetooth" in navigator;

  const [config, setConfig] = useState<BluetoothReaderConfig>(loadBluetoothReaderConfig());
  const [customUUID, setCustomUUID] = useState("");
  const [status, setStatus] = useState<string>("Nicht verbunden.");
  const [error, setError] = useState<string | null>(null);
  const [discovered, setDiscovered] = useState<DiscoveredService[]>([]);
  const [lastReading, setLastReading] = useState<string | null>(null);
  const [lookupResult, setLookupResult] = useState<string | null>(null);

  function saveConfig() {
    saveBluetoothReaderConfig(config);
    setStatus("Konfiguration gespeichert.");
  }

  async function handleLookup(identifier: string) {
    setLastReading(identifier);
    setLookupResult(null);
    try {
      const res = await api.animals.lookup(identifier);
      if (res.matched_animal) {
        setLookupResult(`Gefunden: ${res.matched_animal.chip_number} — springe zur Tierseite…`);
        setTimeout(() => navigate(`/tiere/${res.matched_animal!.id}`), 800);
      } else if (res.candidate_animals.length > 1) {
        setLookupResult(
          `Mehrdeutig — passt auf ${res.candidate_animals.length} Tiere: ${res.candidate_animals
            .map((a) => a.chip_number)
            .join(", ")}`,
        );
      } else {
        setLookupResult(`Kein Tier zu "${identifier}" gefunden.`);
      }
    } catch (err) {
      setLookupResult(`Fehler bei der Zuordnung: ${(err as Error).message}`);
    }
  }

  async function connectConfigured() {
    setError(null);
    if (!isBluetoothReaderConfigured(config)) {
      setError("Bitte zuerst Service- und Characteristic-UUID eintragen (oder per Diagnose ermitteln).");
      return;
    }
    try {
      setStatus("Warte auf Geräteauswahl…");
      const filters = config.namePrefix ? [{ namePrefix: config.namePrefix }] : [{ services: [config.serviceUUID!] }];
      const device = await navigator.bluetooth.requestDevice({
        filters,
        optionalServices: [config.serviceUUID!],
      });
      setStatus(`Verbinde mit ${device.name ?? "Gerät"}…`);
      const server = await device.gatt!.connect();
      const service = await server.getPrimaryService(config.serviceUUID!);
      const characteristic = await service.getCharacteristic(config.characteristicUUID!);
      await characteristic.startNotifications();
      characteristic.addEventListener("characteristicvaluechanged", (e) => {
        const value = (e.target as BluetoothRemoteGATTCharacteristic).value;
        if (value) {
          const identifier = decodeValue(value);
          handleLookup(identifier);
        }
      });
      setStatus(`Verbunden mit ${device.name ?? "Gerät"} — bereit zum Scannen.`);
    } catch (err) {
      setError((err as Error).message);
      setStatus("Nicht verbunden.");
    }
  }

  async function diagnosticConnect() {
    setError(null);
    setDiscovered([]);
    try {
      setStatus("Warte auf Geräteauswahl (Diagnose)…");
      const optionalServices = [...COMMON_BLE_SERVICE_UUIDS];
      if (customUUID.trim()) optionalServices.push(customUUID.trim());
      const device = await navigator.bluetooth.requestDevice({
        acceptAllDevices: true,
        optionalServices,
      });
      setStatus(`Verbinde mit ${device.name ?? "Gerät"}…`);
      const server = await device.gatt!.connect();
      const services = await server.getPrimaryServices();
      const result: DiscoveredService[] = [];
      for (const service of services) {
        const chars = await service.getCharacteristics();
        result.push({
          uuid: service.uuid,
          characteristics: chars.map((c) => ({
            uuid: c.uuid,
            properties: Object.entries(c.properties)
              .filter(([, v]) => v)
              .map(([k]) => k),
          })),
        });
      }
      setDiscovered(result);
      setStatus(
        `Verbunden mit ${device.name ?? "Gerät"} — ${result.length} Service(s) gefunden. Nur bekannte/erlaubte ` +
          "Services werden angezeigt (Web-Bluetooth-Einschränkung); unbekannte proprietäre Services ggf. oben als " +
          "UUID eintragen und erneut koppeln.",
      );
    } catch (err) {
      setError((err as Error).message);
      setStatus("Nicht verbunden.");
    }
  }

  async function testCharacteristicNotify(serviceUUID: string, charUUID: string) {
    try {
      const filters = [{ services: [serviceUUID] }];
      const device = await navigator.bluetooth.requestDevice({ filters, optionalServices: [serviceUUID] });
      const server = await device.gatt!.connect();
      const service = await server.getPrimaryService(serviceUUID);
      const characteristic = await service.getCharacteristic(charUUID);
      await characteristic.startNotifications();
      characteristic.addEventListener("characteristicvaluechanged", (e) => {
        const value = (e.target as BluetoothRemoteGATTCharacteristic).value;
        if (value) setLastReading(decodeValue(value));
      });
      setStatus(`Höre auf ${serviceUUID} / ${charUUID} — jetzt am Lesegerät einen Chip scannen.`);
    } catch (err) {
      setError((err as Error).message);
    }
  }

  return (
    <div>
      <h1>Bluetooth-Chip-Scanner</h1>
      <p className="hint" style={{ marginBottom: 16 }}>
        Funktioniert nur in Chrome/Edge (Android oder Desktop) — Web Bluetooth wird von Safari auf
        iPhone/iPad nicht unterstützt.
      </p>

      {!supported && (
        <div className="error-banner">
          Dieser Browser unterstützt Web Bluetooth nicht. Bitte Chrome oder Edge verwenden.
        </div>
      )}

      {supported && (
        <>
          <div className="card section">
            <h2>Lesegerät-Konfiguration</h2>
            <p className="hint" style={{ marginBottom: 12 }}>
              Service- und Characteristic-UUID stehen im Datenblatt deines Lesegeräts, oder lassen
              sich unten per Diagnose-Modus ermitteln.
            </p>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="bt-service">Service-UUID</label>
                <input
                  id="bt-service"
                  type="text"
                  value={config.serviceUUID ?? ""}
                  onChange={(e) => setConfig({ ...config, serviceUUID: e.target.value || null })}
                  placeholder="z.B. 6e400001-b5a3-f393-e0a9-e50e24dcca9e"
                />
              </div>
              <div className="field">
                <label htmlFor="bt-char">Characteristic-UUID</label>
                <input
                  id="bt-char"
                  type="text"
                  value={config.characteristicUUID ?? ""}
                  onChange={(e) => setConfig({ ...config, characteristicUUID: e.target.value || null })}
                  placeholder="z.B. 6e400003-b5a3-f393-e0a9-e50e24dcca9e"
                />
              </div>
              <div className="field">
                <label htmlFor="bt-name">Name-Präfix (optional)</label>
                <input
                  id="bt-name"
                  type="text"
                  value={config.namePrefix ?? ""}
                  onChange={(e) => setConfig({ ...config, namePrefix: e.target.value || null })}
                  placeholder="z.B. RFID-"
                />
              </div>
            </div>
            <button className="btn secondary" onClick={saveConfig}>
              Konfiguration speichern
            </button>
          </div>

          <div className="card section">
            <h2>Verbinden</h2>
            <p className="hint" style={{ marginBottom: 12 }}>
              Status: {status}
            </p>
            {error && <div className="error-banner">{error}</div>}
            <div className="toolbar">
              <button className="btn" onClick={connectConfigured} disabled={!isBluetoothReaderConfigured(config)}>
                Gerät koppeln &amp; auf Scans warten
              </button>
            </div>
            {lastReading && (
              <p>
                Letzte gelesene Nummer: <strong>{lastReading}</strong>
              </p>
            )}
            {lookupResult && <p className="hint">{lookupResult}</p>}
          </div>

          <div className="card section">
            <h2>Diagnose-Modus</h2>
            <p className="hint" style={{ marginBottom: 12 }}>
              Falls die UUIDs deines Lesegeräts unbekannt sind: Gerät hier koppeln, verfügbare
              Services/Characteristics auflisten lassen und testweise auf eine davon hören, während
              du am Lesegerät einen Chip scannst.
            </p>
            <div className="form-grid">
              <div className="field">
                <label htmlFor="bt-custom">Bekannte Service-UUID zusätzlich anfragen (optional)</label>
                <input
                  id="bt-custom"
                  type="text"
                  value={customUUID}
                  onChange={(e) => setCustomUUID(e.target.value)}
                />
              </div>
            </div>
            <button className="btn secondary" onClick={diagnosticConnect}>
              Gerät koppeln (Diagnose)
            </button>

            {discovered.length > 0 && (
              <div className="list" style={{ marginTop: 16 }}>
                {discovered.map((s) => (
                  <div className="card" key={s.uuid}>
                    <div className="title">Service {s.uuid}</div>
                    {s.characteristics.map((c) => (
                      <div className="list-item" key={c.uuid} style={{ marginTop: 6 }}>
                        <span className="hint">
                          {c.uuid} ({c.properties.join(", ")})
                        </span>
                        {c.properties.includes("notify") && (
                          <button
                            className="btn secondary small"
                            onClick={() => testCharacteristicNotify(s.uuid, c.uuid)}
                          >
                            Testen
                          </button>
                        )}
                      </div>
                    ))}
                  </div>
                ))}
              </div>
            )}
          </div>
        </>
      )}
    </div>
  );
}
