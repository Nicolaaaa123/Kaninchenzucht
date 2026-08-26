import { useMemo, useState } from "react";
import { Link, useSearchParams } from "react-router-dom";
import { api } from "../api/client";
import { LitterOverview } from "../components/LitterOverview";
import { useAsync } from "../hooks/useAsync";
import type { AnimalListItem, AnimalStatus, BreedingCategory } from "../api/types";

const STATUS_LABELS: Record<AnimalStatus, string> = {
  active: "Aktiv",
  sold: "Verkauft",
  deceased: "Verstorben",
  retired: "Aus der Zucht",
  slaughtered: "Geschlachtet",
};

const SEX_LABELS: Record<string, string> = {
  male: "♂ Rammler",
  female: "♀ Zibbe",
  unknown: "unbekannt",
};

const CATEGORY_LABELS: Record<BreedingCategory, string> = {
  breeding: "Zuchttier",
  young: "Jungtier",
  external: "Externes Zuchttier",
};

const CATEGORY_ORDER: BreedingCategory[] = ["breeding", "young", "external"];

type SortKey = "chip" | "year" | "breed";

export function Animals() {
  const [searchParams] = useSearchParams();
  const litterCount = searchParams.get("wurf");
  const [search, setSearch] = useState("");
  const [status, setStatus] = useState<AnimalStatus | "">("active");
  const [sortKey, setSortKey] = useState<SortKey>("chip");
  const [breedIdFilter, setBreedIdFilter] = useState<string>("all");
  const [colorFilter, setColorFilter] = useState<string>("all");
  const [viewMode, setViewMode] = useState<"list" | "litters">(
    searchParams.get("view") === "litters" ? "litters" : "list",
  );
  const { data, loading, error } = useAsync(
    () => api.animals.list({ search: search || undefined, status: status || undefined }),
    [search, status],
  );

  const breedOptions = useMemo(() => {
    const map = new Map<string, { breedId: string; breedName: string }>();
    for (const a of data ?? []) {
      if (!a.breed) continue;
      if (!map.has(a.breed.id)) map.set(a.breed.id, { breedId: a.breed.id, breedName: a.breed.name });
    }
    return Array.from(map.values()).sort((a, b) => a.breedName.localeCompare(b.breedName));
  }, [data]);

  const colorOptions = useMemo(() => {
    const set = new Set<string>();
    for (const a of data ?? []) {
      if (!a.color_variant) continue;
      if (breedIdFilter !== "all" && a.breed?.id !== breedIdFilter) continue;
      set.add(a.color_variant);
    }
    return Array.from(set).sort((a, b) => a.localeCompare(b));
  }, [data, breedIdFilter]);

  function handleBreedFilterChange(value: string) {
    setBreedIdFilter(value);
    setColorFilter("all");
  }

  const filtered = useMemo(() => {
    if (!data) return data;
    return data.filter(
      (a) =>
        (breedIdFilter === "all" || a.breed?.id === breedIdFilter) &&
        (colorFilter === "all" || a.color_variant === colorFilter),
    );
  }, [data, breedIdFilter, colorFilter]);

  const sorted = useMemo(() => {
    if (!filtered) return filtered;
    const copy = [...filtered];
    if (sortKey === "year") {
      copy.sort((a, b) => (b.birth_date ?? "").localeCompare(a.birth_date ?? ""));
    } else if (sortKey === "breed") {
      copy.sort((a, b) => (a.breed?.name ?? "").localeCompare(b.breed?.name ?? ""));
    } else {
      copy.sort((a, b) => a.chip_number.localeCompare(b.chip_number));
    }
    return copy;
  }, [filtered, sortKey]);

  const groupedByCategory = useMemo(() => {
    if (!sorted || (breedIdFilter === "all" && colorFilter === "all")) return null;
    const buckets: Record<BreedingCategory, AnimalListItem[]> = { breeding: [], young: [], external: [] };
    for (const a of sorted) buckets[a.category].push(a);
    return buckets;
  }, [sorted, breedIdFilter, colorFilter]);

  const youngLitters = useMemo(() => {
    if (!groupedByCategory) return null;
    const map = new Map<string, AnimalListItem[]>();
    for (const a of groupedByCategory.young) {
      const key = `${a.mother_id ?? "?"}|${a.father_id ?? "?"}|${a.birth_date ?? "?"}`;
      if (!map.has(key)) map.set(key, []);
      map.get(key)!.push(a);
    }
    return Array.from(map.entries());
  }, [groupedByCategory]);

  function renderAnimalItem(animal: AnimalListItem) {
    return (
      <Link className={`list-item category-${animal.category}`} to={`/tiere/${animal.id}`} key={animal.id}>
        <div>
          <div className="title">
            {animal.chip_number} {animal.name ? `· ${animal.name}` : ""}
          </div>
          <div className="subtitle">
            {SEX_LABELS[animal.sex]}
            {animal.birth_date ? ` · Jg. ${animal.birth_date.slice(0, 4)}` : ""}
            {animal.breed ? ` · ${animal.breed.name}` : ""}
            {animal.color_variant ? ` · ${animal.color_variant}` : ""}
            {animal.latest_weight_grams ? ` · ${animal.latest_weight_grams} g` : ""}
            {animal.daily_feed_grams ? ` · ${animal.daily_feed_grams} g/Tag` : ""}
            {animal.container_fill_pct != null ? ` (${animal.container_fill_pct}% Behälter)` : ""}
          </div>
        </div>
        <div style={{ display: "flex", flexDirection: "column", gap: 4, alignItems: "flex-end" }}>
          <span className={`badge category-${animal.category}`}>{CATEGORY_LABELS[animal.category]}</span>
          <span className={`badge status-${animal.status}`}>{STATUS_LABELS[animal.status]}</span>
        </div>
      </Link>
    );
  }

  return (
    <div>
      <h1>Tiere</h1>
      {litterCount && (
        <div className="card section" style={{ background: "var(--color-success-soft)", color: "var(--color-success)" }}>
          {litterCount} Jungtiere angelegt — Chip-Nummern sind Platzhalter, bitte bei Gelegenheit durch
          die echten ersetzen.
        </div>
      )}

      {breedOptions.length > 0 && (
        <div className="toolbar">
          <select
            value={breedIdFilter}
            onChange={(e) => handleBreedFilterChange(e.target.value)}
            style={{ flex: 1 }}
          >
            <option value="all">Alle Rassen</option>
            {breedOptions.map((opt) => (
              <option key={opt.breedId} value={opt.breedId}>
                {opt.breedName}
              </option>
            ))}
          </select>
          <select
            value={colorFilter}
            onChange={(e) => setColorFilter(e.target.value)}
            disabled={colorOptions.length === 0}
            style={{ flex: 1 }}
          >
            <option value="all">Alle Farbenschläge</option>
            {colorOptions.map((color) => (
              <option key={color} value={color}>
                {color}
              </option>
            ))}
          </select>
        </div>
      )}

      <div className="toolbar">
        <input
          type="search"
          placeholder="Suche nach Chip-Nummer oder Name…"
          value={search}
          onChange={(e) => setSearch(e.target.value)}
          style={{ flex: 2, minWidth: 180 }}
        />
        <select value={status} onChange={(e) => setStatus(e.target.value as AnimalStatus | "")} style={{ flex: 1 }}>
          <option value="">Alle Status</option>
          {Object.entries(STATUS_LABELS).map(([value, label]) => (
            <option key={value} value={value}>
              {label}
            </option>
          ))}
        </select>
        <select value={sortKey} onChange={(e) => setSortKey(e.target.value as SortKey)} style={{ flex: 1 }}>
          <option value="chip">Sortierung: Chip-Nummer</option>
          <option value="year">Sortierung: Jahrgang</option>
          <option value="breed">Sortierung: Rasse</option>
        </select>
      </div>
      <div className="toolbar">
        <Link className="btn secondary" to="/tiere/etiketten">
          Etiketten drucken
        </Link>
        <Link className="btn secondary" to="/tiere/vergleich">
          Vergleichen
        </Link>
        <Link className="btn secondary" to="/chip-scanner">
          Chip-Scanner
        </Link>
        <Link className="btn secondary" to="/tiere/wurf">
          + Wurf erstellen
        </Link>
        <Link className="btn" to="/tiere/neu">
          + Neues Tier
        </Link>
      </div>

      <div className="page-tabs" style={{ marginBottom: 16 }}>
        <button className={`page-tab ${viewMode === "list" ? "active" : ""}`} onClick={() => setViewMode("list")}>
          📋 Liste
        </button>
        <button className={`page-tab ${viewMode === "litters" ? "active" : ""}`} onClick={() => setViewMode("litters")}>
          🐇 Würfe im Überblick
        </button>
      </div>

      {viewMode === "litters" ? (
        <LitterOverview />
      ) : (
        <>
          {loading && <p>Lade Tiere…</p>}
          {error && <div className="error-banner">{error}</div>}

          {groupedByCategory ? (
        <div>
          {CATEGORY_ORDER.map((cat) => {
            if (cat === "young") {
              if (groupedByCategory.young.length === 0) return null;
              return (
                <div className="section" key={cat}>
                  <h2>{CATEGORY_LABELS.young} ({groupedByCategory.young.length})</h2>
                  {youngLitters?.map(([key, animals]) => (
                    <div key={key} style={{ marginBottom: 14 }}>
                      {animals.length > 1 && (
                        <div className="hint" style={{ marginBottom: 4 }}>
                          {animals[0].litter_name ? `"${animals[0].litter_name}"` : "Wurf"}
                          {animals[0].birth_date ? ` vom ${animals[0].birth_date}` : ""} · {animals.length} Tiere
                        </div>
                      )}
                      <div className="list">{animals.map(renderAnimalItem)}</div>
                    </div>
                  ))}
                </div>
              );
            }
            if (groupedByCategory[cat].length === 0) return null;
            return (
              <div className="section" key={cat}>
                <h2>
                  {CATEGORY_LABELS[cat]} ({groupedByCategory[cat].length})
                </h2>
                <div className="list">{groupedByCategory[cat].map(renderAnimalItem)}</div>
              </div>
            );
          })}
          {sorted && sorted.length === 0 && <p className="empty-state">Keine Tiere gefunden.</p>}
        </div>
      ) : (
        <div className="list">
          {sorted?.map(renderAnimalItem)}
          {sorted && sorted.length === 0 && <p className="empty-state">Keine Tiere gefunden.</p>}
        </div>
          )}
        </>
      )}
    </div>
  );
}
