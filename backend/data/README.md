# ENABLE word list (Enhanced North American Benchmark Lexicon)

Public-domain word list used for challenge lookups during live Scrabble games.

## Source

- **File:** `enable1.txt` (one word per line, lowercase in source file)
- **Upstream:** [dolph/dictionary](https://github.com/dolph/dictionary/blob/master/enable1.txt) (also mirrored at [norvig.com/ngrams/enable1.txt](https://norvig.com/ngrams/enable1.txt))
- **Words:** ~173,000 entries

ENABLE is distributed in the public domain. See the upstream repository for authorship and research notes.

## Usage in this app

Loaded once at startup into an in-memory `frozenset` (uppercase). Lookups are O(1).
Used only for exact-word challenge checks — not prefix search.

## Replacing the list

Swap `enable1.txt` and restart the server. No API or schema changes required.
