// Keep in sync with backend/app/scoring.py
export const MIN_RACK_ADJUSTMENT = -70;
export const MAX_RACK_ADJUSTMENT = 0;

export type RackAdjustmentValidation =
  | { ok: true; adjustment: number }
  | { ok: false; message: string };

export function validateRackAdjustmentInput(raw: string): RackAdjustmentValidation {
  const trimmed = raw.trim();
  if (!trimmed) {
    return { ok: true, adjustment: 0 };
  }
  if (!/^-?\d+$/.test(trimmed)) {
    return { ok: false, message: "Rack penalty must be a whole number." };
  }
  const adjustment = Number(trimmed);
  if (adjustment < MIN_RACK_ADJUSTMENT || adjustment > MAX_RACK_ADJUSTMENT) {
    return { ok: false, message: "Rack penalty must be between -70 and 0." };
  }
  return { ok: true, adjustment };
}
