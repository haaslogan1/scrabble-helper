"""Scrabble word validation using the ENABLE word list."""

from __future__ import annotations

from functools import lru_cache
from pathlib import Path

DATA_PATH = Path(__file__).resolve().parents[1] / "data" / "enable1.txt"


@lru_cache(maxsize=1)
def load_word_set() -> frozenset[str]:
    if not DATA_PATH.is_file():
        raise FileNotFoundError(f"Word list not found: {DATA_PATH}")
    words: set[str] = set()
    for line in DATA_PATH.read_text(encoding="utf-8").splitlines():
        word = line.strip().upper()
        if word:
            words.add(word)
    return frozenset(words)


def normalize_word(word: str) -> str | None:
    cleaned = word.strip().upper()
    if not cleaned or not cleaned.isalpha():
        return None
    return cleaned


def is_valid_word(word: str) -> bool:
    normalized = normalize_word(word)
    if normalized is None or len(normalized) < 2 or len(normalized) > 15:
        return False
    return normalized in load_word_set()
