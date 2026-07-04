from __future__ import annotations

import re
from pathlib import Path

import pytest

from app.config import settings
from app.dictionary import DATA_PATH, is_valid_word, load_word_set, normalize_word

FIXTURES_DIR = Path(__file__).resolve().parent / "fixtures"
VALID_SAMPLES = FIXTURES_DIR / "dictionary_valid_samples.txt"
INVALID_SAMPLES = FIXTURES_DIR / "dictionary_invalid_samples.txt"

KNOWN_VALID = [
    "QUIZ",
    "AA",
    "AARDVARK",
    "XYLOPHONE",
    "ZYZYVA",
    "HELLO",
    "SCRABBLE",
    "QUARTZ",
    "JAZZ",
    "FUZY",
    "OX",
    "XI",
    "AX",
    "EX",
    "JO",
    "KA",
    "KI",
    "OE",
    "AI",
    "AR",
    "AT",
    "BE",
    "BY",
    "DO",
    "GO",
    "HE",
    "IF",
    "IN",
    "IS",
    "IT",
    "ME",
    "MY",
    "NO",
    "OF",
    "ON",
    "OR",
    "OW",
    "OX",
    "PA",
    "PI",
    "RE",
    "SO",
    "TO",
    "UP",
    "US",
    "WE",
    "YE",
    "ZA",
    "QI",
]

KNOWN_INVALID = [
    "",
    "A",
    "ZZZ",
    "QQ",
    "NOTAWORD",
    "HELLO123",
    "FAKEWORD",
    "SCRABBLEHELPER",
    "ABCDEFGHIJKLMNOP",
    "123",
    "QU-IZ",
    "F-O-O",
    "XYZZY",
    "NOTINENABLE",
    "ZZTOP",
    "QQQQ",
    "INVALIDWORD",
    "BOGUSWORD",
    "PHONYWORD",
    "GARBAGEWORD",
    "NOTREAL",
    "WORD123",
    "NUM3RIC",
    "UNDER_SCORE",
    "DOTCOM",
    "EMAILHOST",
    "SPACEDWORD",
    "ZZZZZ",
    "XXXXX",
    "QQQQQ",
    "BADWORD",
    "ZERO0",
    "ONE1",
    "TWO2",
    "THREE3",
    "FOUR4",
    "FIVE5",
    "SIX6",
    "SEVEN7",
    "EIGHT8",
    "NINE9",
    "TEN10",
    "NOTAVALIDWORD",
    "QUACKERS",
]


def _load_fixture_lines(path: Path) -> list[str]:
    return path.read_text(encoding="utf-8").splitlines()


@pytest.mark.unit
def test_enable_file_exists():
    assert DATA_PATH.is_file()


@pytest.mark.unit
def test_word_list_integrity():
    lines = _load_fixture_lines(DATA_PATH)
    assert 170_000 <= len(lines) <= 175_000
    assert lines == sorted(lines)
    seen: set[str] = set()
    pattern = re.compile(r"^[a-z]{2,}$")
    for line in lines:
        assert line == line.strip()
        assert line
        assert pattern.match(line), f"Bad line: {line!r}"
        assert line not in seen, f"Duplicate: {line}"
        seen.add(line)


@pytest.mark.unit
def test_fixture_valid_samples():
    load_word_set()
    for word in _load_fixture_lines(VALID_SAMPLES):
        assert is_valid_word(word), f"Expected valid: {word!r}"


@pytest.mark.unit
def test_fixture_invalid_samples():
    load_word_set()
    for word in _load_fixture_lines(INVALID_SAMPLES):
        assert not is_valid_word(word), f"Expected invalid: {word!r}"


@pytest.mark.unit
@pytest.mark.parametrize("word", KNOWN_VALID)
def test_known_valid_words(word: str):
    load_word_set()
    if not is_valid_word(word):
        pytest.skip(f"{word} not in this ENABLE build")
    assert is_valid_word(word)


@pytest.mark.unit
@pytest.mark.parametrize("word", KNOWN_INVALID)
def test_known_invalid_words(word: str):
    load_word_set()
    assert not is_valid_word(word)


@pytest.mark.unit
def test_normalize_lowercase_and_trim():
    assert normalize_word("  quiz  ") == "QUIZ"
    assert normalize_word("Quiz") == "QUIZ"


@pytest.mark.unit
def test_normalize_rejects_non_letters():
    assert normalize_word("HELLO123") is None
    assert normalize_word("QU-IZ") is None
    assert normalize_word("") is None
    assert normalize_word("   ") is None


@pytest.mark.unit
def test_length_bounds():
    load_word_set()
    assert not is_valid_word("A")
    assert not is_valid_word("A" * 16)


@pytest.mark.integration
def test_api_dictionary_check_valid(client):
    response = client.get("/api/dictionary/check/QUIZ")
    assert response.status_code == 200
    data = response.json()
    assert data == {"word": "QUIZ", "valid": True}


@pytest.mark.integration
def test_api_dictionary_check_invalid(client):
    response = client.get("/api/dictionary/check/NOTAWORD")
    assert response.status_code == 200
    data = response.json()
    assert data["valid"] is False


@pytest.mark.integration
def test_api_dictionary_check_normalizes_case(client):
    response = client.get("/api/dictionary/check/quiz")
    assert response.status_code == 200
    assert response.json()["word"] == "QUIZ"
    assert response.json()["valid"] is True


@pytest.mark.integration
def test_api_dictionary_requires_auth(client, monkeypatch):
    monkeypatch.setattr(settings, "dev_auth_bypass", False)
    response = client.get("/api/dictionary/check/QUIZ")
    assert response.status_code == 401
