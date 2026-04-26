# Architecture & Design Notes

An overview of the technical decisions behind Scrabble Helper and how they fit the use cases.

---

## High-level structure

```
scrabble-helper/
├── app/                  Python package — all business logic
│   ├── dictionary.py     CSW21 loader (runs at import time)
│   ├── word_finder.py    Rack-to-words engine + scoring + bingo detection
│   ├── pattern.py        Pattern/mask matching against the full dictionary
│   ├── phrase_finder.py  Multi-word anagram solver
│   ├── links.py          Collins Dictionary URL builder + morphology guesser
│   ├── logging_config.py Rotating file + console logging setup
│   └── main.py           FastAPI routes (web interface)
├── templates/            Jinja2 HTML (base.html + index.html)
├── static/               CSS + vanilla JS
├── scripts/
│   └── download_dict.py  One-time CSW21 dictionary fetcher
├── scrabble.py           CLI entry point (argparse, four subcommands)
├── serve.py              Server launcher (uvicorn + optional ngrok)
└── docs/                 This documentation
```

---

## Key decisions

### Dictionary loading at startup

`app/dictionary.py` builds two in-memory structures when the module is first imported:

- **`WORD_SET`** — a Python `set` of all 279,077 CSW21 words (uppercase).  Used for O(1) membership tests in validation and the inner loop of word finding.
- **`ANAGRAM_INDEX`** — a `dict[sorted_letters → [words]]`.  Reserved for future anagram lookup; not yet used in the main search path.

Loading takes ~0.3 s on a typical machine and happens once per process.  The startup cost is negligible for a web server and acceptable for CLI invocations.

### Rack search: Counter-based multiset arithmetic

Word finding iterates the entire 279k-word set and checks each word against the rack using Python's `Counter` (a multiset).  No pre-indexing by rack letters is done because:

- 279k iterations with Counter arithmetic takes ~100 ms per query on a single thread — well within interactive response time.
- Pre-indexing would require a complex index over subsets of letters, complicating the blank-tile (`?`) and board-tile logic.

Blank tiles are handled as a "wildcard deficit": after subtracting known rack letters from what the word needs, any remaining shortage is covered by blanks.

### Board tiles and the `_can_form` contract

The `starts_with`, `ends_with`, and `contains` fields (and literal letters in the pattern mask) represent **letters already on the board**.  The player does not need them in their rack.

`_can_form(word, rack_counter, blanks, board)` implements this in one place:

1. Subtract the board counter from the word's letter needs.
2. If the subtraction leaves the needs counter empty, the board covers the whole word — this is an illegal play (no rack tile used), so return `False`.
3. Check the remaining needs against the rack, using blanks for any shortage.

This single function is reused for all filter combinations.

### OR alternatives (`|` syntax)

When a filter field contains `|`, the engine tries every combination of matching alternatives (one from starts_with, one from ends_with, one from contains) and includes the word if **any** combination is feasible.  This lets the player express "my word passes through board square Y **or** square L" without running two separate queries.

### Pattern literals as board tiles

A pattern like `_A__R` specifies an A at position 2 and an R at position 5.  Because those positions are already occupied on the board, the player does not supply them.  The engine extracts all A–Z characters from the pattern into a board counter and adds it to any board tiles from the other filter fields before calling `_can_form`.

### Bingo detection

A bingo (the +50 point bonus for using all tiles) requires:

1. `rack_tiles_used == rack_size` — all tiles in the rack were played.
2. `rack_size >= 7` — avoids false bingos when a player enters fewer tiles (e.g. testing with two tiles).

`rack_tiles_used` is computed per word as `len(word) − board_letters_used`, where `board_letters_used` counts how many of the word's letters are provided by board tiles.  The engine tracks the **maximum** `rack_tiles_used` across all valid OR alternatives, since the player can choose which board square to play through to maximise their tile usage.

### Phrase builder: DFS with deduplication

The multi-word anagram solver (`phrase_finder.py`) uses depth-first search:

- **Pre-filtering** — only words formable from the full letter pool are considered candidates.  This prunes the search tree significantly.
- **Sorted ordering** — words are sorted alphabetically and the DFS only extends with words ≥ the last word chosen.  This eliminates permutation duplicates (I + LOVE + YOU and YOU + I + LOVE are the same combination).
- **Timeout (web only)** — for large letter pools the search space explodes.  The web route enforces an 8-second timeout (configurable via `PHRASE_WEB_TIMEOUT_SEC` in `app/main.py`); the CLI runs without a limit.
- **Single-letter words** — "A" and "I" are valid English words but are below CSW21's 2-letter minimum.  They are added to the vocabulary for phrase finding only.

### Web/CLI parity

All business logic lives in `app/`.  Both the FastAPI routes (`app/main.py`) and the CLI (`scrabble.py`) call the same functions and produce structurally identical output.  This was a deliberate constraint: any bug fix or feature added to the backend automatically benefits both interfaces.

### No frontend framework

The UI is plain HTML rendered by Jinja2 templates, with a small CSS file and ~25 lines of vanilla JavaScript (form submission on Enter, rack shuffle).  There is no build step, no Node.js dependency, and no client-side routing.  This keeps the project runnable with a single `pip install`.

### ngrok as an optional layer

`serve.py` is a thin launcher script, not part of the application.  It starts uvicorn (the actual server), then *optionally* starts ngrok for public tunnelling.  If ngrok is absent or fails, the server continues running locally — nothing in `app/` knows or cares about ngrok.

---

## Use cases

| Use case | Feature | Notes |
|----------|---------|-------|
| Check if a word is valid before challenging | Validate | Returns Collins link for reference |
| Find the best play for a given rack | Suggest from Rack | Ranked by face-value score; bingo highlighted |
| Find plays that cross a specific board tile | Suggest + board tile filters | Board tile is free; rack supplies the rest |
| Fill a gap on the board | Pattern Search | No rack needed; wildcard `_` and `*` |
| Anagram a name into a phrase | Phrase Builder | Common-word filter surfaces natural phrases |
| Share the tool with a friend mid-game | serve.py + ngrok | Temporary public URL, no deployment needed |

---

## Planned (Phase 2)

The `app/board/` package is scaffolded but empty.  The intended Phase 2 feature is a board reader: the player uploads a screenshot of their game, Pillow parses the 15×15 grid, and the solver suggests the best legal move including word multipliers and cross-word scores.
