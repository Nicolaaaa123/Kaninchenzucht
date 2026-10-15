import type { EvaluatedBreed } from "../api/types";

interface Props {
  breeds: EvaluatedBreed[];
  breedId: string;
  colorVariant: string;
  onBreedChange: (breedId: string) => void;
  onColorVariantChange: (colorVariant: string) => void;
}

/** Rassen-Auswahl (nur Rassen mit Bewertungskarten) plus Farbenschlag-Auswahl
 * für die gewählte Rasse. */
export function BreedColorFilter({ breeds, breedId, colorVariant, onBreedChange, onColorVariantChange }: Props) {
  const variants = breeds.find((b) => b.breed_id === breedId)?.color_variants ?? [];
  return (
    <>
      <select
        value={breedId}
        onChange={(e) => {
          onBreedChange(e.target.value);
          onColorVariantChange("");
        }}
        style={{ flex: 1 }}
      >
        <option value="">Alle Rassen</option>
        {breeds.map((b) => (
          <option key={b.breed_id} value={b.breed_id}>
            {b.breed_name}
          </option>
        ))}
      </select>
      {breedId && variants.length > 0 && (
        <select value={colorVariant} onChange={(e) => onColorVariantChange(e.target.value)} style={{ flex: 1 }}>
          <option value="">Alle Farbenschläge</option>
          {variants.map((v) => (
            <option key={v} value={v}>
              {v}
            </option>
          ))}
        </select>
      )}
    </>
  );
}
