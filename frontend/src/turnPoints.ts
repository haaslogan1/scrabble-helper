export const MAX_TURN_POINTS = 1786;

export type TurnPointsValidation =
  | { ok: true; points: number }
  | { ok: false; message: string };

export function validateTurnPointsInput(raw: string): TurnPointsValidation {
  const trimmed = raw.trim();
  if (!trimmed) {
    return { ok: false, message: "Enter a point value for this turn." };
  }
  if (!/^\d+$/.test(trimmed)) {
    return { ok: false, message: "Points must be a positive whole number." };
  }
  const points = Number(trimmed);
  if (points < 1) {
    return { ok: false, message: "Points must be at least 1." };
  }
  if (points > MAX_TURN_POINTS) {
    return {
      ok: false,
      message: `Points cannot exceed ${MAX_TURN_POINTS} (theoretical max for one Scrabble turn).`,
    };
  }
  return { ok: true, points };
}
