# Scrabble Helper

A personal Scrabble assistant built around the **CSW21** (Collins Scrabble Words 2021) dictionary — the standard for international and British competitive Scrabble.

Available as both a **web app** and a **command-line tool**.  All four features share the same backend, so results are identical whichever interface you use.

---

## Features

### Validate a Word
Check whether any word is legal in CSW21 and get a direct link to its Collins Dictionary page.  If the exact form isn't found, the tool suggests likely base forms (e.g. EWTS → EWT, RUNNING → RUN).

```
python scrabble.py validate ZOEAE
python scrabble.py v EWTS
```

### Suggest Words from Rack
Enter up to seven tiles and get every playable CSW21 word, ranked by face-value score.  Bingo plays (using all seven rack tiles) are highlighted.

**Blank tiles** — use `?` for a blank; it scores 0 and acts as any letter.

**Board tiles** — letters already on the board go in *Starts with / Ends with / Contains*.  They are free (you don't need them in your rack) and the tool still requires you to contribute at least one tile of your own.

**OR alternatives** — use `|` to list options: `contains=Y|L` finds words that pass through a board Y *or* L.

**Pattern mask** — pin specific positions.  Literal letters in the mask are board tiles; `_` is a rack tile you supply.

```
python scrabble.py suggest RSTLNEI
python scrabble.py s STLNEI --starts-with QU          # QU already on board
python scrabble.py s STLNEI --contains "Y|L"          # board Y or L
python scrabble.py s XVRWEO --pattern "_A__R"         # A and R on board
python scrabble.py s RST?NEI --ends-with ING --top 5
```

### Pattern Search
Find all CSW21 words matching a shape — no rack needed.  Useful for finding words that fit a gap on the board.

| Symbol | Meaning |
|--------|---------|
| `_`    | exactly one letter |
| `*`    | zero or more letters |
| `A-Z`  | literal letter at that position |

```
python scrabble.py pattern "_T_W_"    # 5-letter: T at pos 2, W at pos 4
python scrabble.py p "*ING"           # any word ending in ING
python scrabble.py p "Q__"           # 3-letter words starting with Q
```

### Phrase Builder
Given a pool of letters, find every combination of valid words that uses **all** letters exactly once — great for anagramming someone's name or a phrase into its component words.

```
python scrabble.py phrase YOUIEVOL    # → I + LOVE + YOU
python scrabble.py ph EARTHLINGS --min-len 3 --max-words 3
```

Combinations where every word is a common everyday English word are flagged as **phrases** in the web UI and `[phrase]` in the CLI.

---

## Web Interface

```bash
python serve.py          # opens at http://localhost:8080
```

To share with others over the internet (requires a free [ngrok](https://ngrok.com) account):

```bash
python serve.py --add-token YOUR_NGROK_TOKEN   # one-time setup
python serve.py                                 # prints a random public URL
```

The URL changes each session — copy it from the terminal and share it with whoever you're playing with.  See [docs/SETUP.md](docs/SETUP.md) for full ngrok setup instructions and troubleshooting.

See [docs/SETUP.md](docs/SETUP.md) for full installation instructions.

---

## Why CSW21?

CSW21 contains **279,077 words** and is the definitive word list for international Scrabble tournaments (WESPA), UK/Ireland club play, and Collins-rules games.  It is more permissive than the North American TWL/OSPD lists and accepts many words from British, Australian, and South African English.

---

## Quick Reference

| Task | CLI | Web tab |
|------|-----|---------|
| Is STEW valid? | `scrabble.py v STEW` | Validate Word |
| Best plays for RSTLNEI | `scrabble.py s RSTLNEI` | Suggest from Rack |
| Words ending in -TION | `scrabble.py p "*TION"` | Pattern Search |
| Anagram ILYAZLOTNIK | `scrabble.py ph ILYAZLOTNIK` | Phrase Builder |
| Shuffle tiles | `scrabble.py sc RSTLNEI` | shuffle button (⇄) |

Full CLI help: `python scrabble.py --help` or `python scrabble.py <command> --help`
