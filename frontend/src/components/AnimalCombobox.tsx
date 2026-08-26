import { useEffect, useRef, useState } from "react";

export interface AnimalComboboxOption {
  id: string;
  chip_number: string;
  name?: string | null;
}

function labelFor(a: AnimalComboboxOption) {
  return `${a.chip_number}${a.name ? ` · ${a.name}` : ""}`;
}

interface AnimalComboboxProps {
  id?: string;
  options: AnimalComboboxOption[];
  value: string;
  onChange: (id: string) => void;
  placeholder?: string;
  emptyLabel?: string;
}

/** Text-Eingabe mit Live-Suche (Chip-Nummer oder Name) statt einer langen
 * Dropdown-Liste -- Auswahl-Verhalten wie ein <select>, aber durchsuchbar. */
export function AnimalCombobox({
  id,
  options,
  value,
  onChange,
  placeholder = "– wählen –",
  emptyLabel,
}: AnimalComboboxProps) {
  const selected = options.find((o) => o.id === value) ?? null;
  const [query, setQuery] = useState(selected ? labelFor(selected) : "");
  const [open, setOpen] = useState(false);
  const containerRef = useRef<HTMLDivElement>(null);

  useEffect(() => {
    const current = options.find((o) => o.id === value) ?? null;
    setQuery(current ? labelFor(current) : "");
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [value]);

  useEffect(() => {
    if (!open) return;
    function handleClickOutside(e: MouseEvent) {
      if (containerRef.current && !containerRef.current.contains(e.target as Node)) {
        setOpen(false);
        const current = options.find((o) => o.id === value) ?? null;
        setQuery(current ? labelFor(current) : "");
      }
    }
    document.addEventListener("mousedown", handleClickOutside);
    return () => document.removeEventListener("mousedown", handleClickOutside);
    // eslint-disable-next-line react-hooks/exhaustive-deps
  }, [open, value]);

  const isShowingSelection = selected && labelFor(selected) === query;
  const filtered =
    query.trim() === "" || isShowingSelection
      ? options
      : options.filter((o) => labelFor(o).toLowerCase().includes(query.trim().toLowerCase()));

  function pick(o: AnimalComboboxOption | null) {
    onChange(o?.id ?? "");
    setQuery(o ? labelFor(o) : "");
    setOpen(false);
  }

  return (
    <div ref={containerRef} style={{ position: "relative" }}>
      <input
        id={id}
        type="text"
        autoComplete="off"
        value={query}
        placeholder={placeholder}
        onChange={(e) => {
          setQuery(e.target.value);
          setOpen(true);
          if (value) onChange("");
        }}
        onFocus={() => setOpen(true)}
      />
      {open && (
        <div className="combobox-list">
          <div className="combobox-option combobox-option-empty" onMouseDown={() => pick(null)}>
            {emptyLabel ?? placeholder}
          </div>
          {filtered.length === 0 ? (
            <div className="combobox-empty">Keine Treffer</div>
          ) : (
            filtered.map((o) => (
              <div key={o.id} className="combobox-option" onMouseDown={() => pick(o)}>
                {labelFor(o)}
              </div>
            ))
          )}
        </div>
      )}
    </div>
  );
}
