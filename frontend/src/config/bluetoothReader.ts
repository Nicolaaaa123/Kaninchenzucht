// Konfiguration für das Bluetooth-Chip-Lesegerät.
//
// Das BLE-Protokoll (Service-/Characteristic-UUID, Datenformat) ist von
// Hersteller zu Hersteller unterschiedlich — es gibt keinen Standard-GATT-
// Service für Tierchip-Leser (anders als z.B. bei Herzfrequenzmessern), daher
// lässt sich das nicht "einfach so" für jedes Gerät vorkonfigurieren.
//
// Die tatsächlich genutzte Konfiguration wird zur Laufzeit aus localStorage
// gelesen (über die Chip-Scanner-Seite direkt im Browser einstellbar, kein
// Code-Update nötig) und fällt auf die Werte hier zurück, falls noch nichts
// gespeichert wurde. Die UUIDs findest du im Datenblatt/SDK des Herstellers,
// oder über den Diagnose-Modus auf der Chip-Scanner-Seite.
export interface BluetoothReaderConfig {
  serviceUUID: string | null;
  characteristicUUID: string | null;
  namePrefix: string | null;
}

export const DEFAULT_BLUETOOTH_READER_CONFIG: BluetoothReaderConfig = {
  serviceUUID: null,
  characteristicUUID: null,
  namePrefix: null,
};

// Häufig in günstigen BLE-Modulen (UART-Bridges) verwendete Service-UUIDs —
// werden im Diagnose-Modus vorsorglich mit angefragt, damit sie beim
// Koppeln sichtbar werden, falls der Leser eines davon nutzt.
export const COMMON_BLE_SERVICE_UUIDS = [
  "6e400001-b5a3-f393-e0a9-e50e24dcca9e", // Nordic UART Service
  "0000ffe0-0000-1000-8000-00805f9b34fb", // HM-10 / CC41 UART-Modul
  "0000ff00-0000-1000-8000-00805f9b34fb", // weit verbreitetes generisches Custom-Profil
  "device_information",
  "battery_service",
];

const STORAGE_KEY = "kaninchenzucht.bluetoothReader";

export function loadBluetoothReaderConfig(): BluetoothReaderConfig {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    if (raw) return { ...DEFAULT_BLUETOOTH_READER_CONFIG, ...JSON.parse(raw) };
  } catch {
    // ignore malformed storage
  }
  return DEFAULT_BLUETOOTH_READER_CONFIG;
}

export function saveBluetoothReaderConfig(config: BluetoothReaderConfig) {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(config));
}

export function isBluetoothReaderConfigured(config: BluetoothReaderConfig): boolean {
  return !!(config.serviceUUID && config.characteristicUUID);
}
