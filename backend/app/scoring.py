"""Scoring helpers ported from scrabble2."""

from __future__ import annotations

from dataclasses import dataclass, field

# Highest documented single-turn Scrabble score (OSPD-based theoretical max).
MAX_TURN_POINTS = 1786


@dataclass
class PlayerScore:
    player_id: int
    name: str
    rounds: list[float] = field(default_factory=list)
    total_score: float = 0.0
    placement: int = 0
    won: bool = False
    rack_adjustment: float = 0.0


def assign_placements(players: list[PlayerScore]) -> None:
    if not players:
        return
    ordered = sorted(players, key=lambda p: p.total_score, reverse=True)
    max_score = ordered[0].total_score
    rank = 1
    prev_score: float | None = None
    for index, player in enumerate(ordered):
        if prev_score is not None and player.total_score < prev_score:
            rank = index + 1
        player.placement = rank
        player.won = player.total_score == max_score
        prev_score = player.total_score


def score_from_word(word: str) -> float:
    """Simple letter-value scoring for word input mode."""
    values = {
        "a": 1, "b": 3, "c": 3, "d": 2, "e": 1, "f": 4, "g": 2, "h": 4,
        "i": 1, "j": 8, "k": 5, "l": 1, "m": 3, "n": 1, "o": 1, "p": 3,
        "q": 10, "r": 1, "s": 1, "t": 1, "u": 1, "v": 4, "w": 4, "x": 8,
        "y": 4, "z": 10,
    }
    return float(sum(values.get(ch, 0) for ch in word.lower() if ch.isalpha()))


def validate_turn_points(value: float | int | None) -> int:
    """Validate a manual points entry; raises ValueError with a user-facing message."""
    if value is None:
        raise ValueError("Enter a point value for this turn.")
    if isinstance(value, bool):
        raise ValueError("Points must be a positive whole number.")
    try:
        numeric = float(value)
    except (TypeError, ValueError):
        raise ValueError("Points must be a positive whole number.") from None
    if not numeric.is_integer():
        raise ValueError("Points must be a whole number (no decimals).")
    points = int(numeric)
    if points < 1:
        raise ValueError("Points must be at least 1.")
    if points > MAX_TURN_POINTS:
        raise ValueError(
            f"Points cannot exceed {MAX_TURN_POINTS} (theoretical max for one Scrabble turn)."
        )
    return points
