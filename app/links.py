"""
Shared dictionary link builder and word-form guesser.
Used identically by the web routes (app/main.py) and the CLI (scrabble.py).

Collins URL format that works: /dictionary/english/{word}
The /scrabble/checker/ path returns 404 for many valid CSW words.
"""
from __future__ import annotations
import logging
from app.dictionary import WORD_SET

logger = logging.getLogger(__name__)

COLLINS_ROOT = "https://www.collinsdictionary.com/dictionary/english"


def collins_url(word: str) -> str:
    return f"{COLLINS_ROOT}/{word.lower()}"


def _candidates(word: str) -> list[str]:
    """
    Generate candidate base/root forms for `word` using English morphology rules.
    Returns candidates in priority order; does NOT filter by the dictionary.
    """
    w = word.upper()
    seen: set[str] = {w, ""}
    out: list[str] = []

    def add(c: str) -> None:
        if c and c not in seen and c.isalpha():
            seen.add(c)
            out.append(c)

    # -IES → -Y  (FLIES → FLY, BERRIES → BERRY)
    if w.endswith("IES") and len(w) > 4:
        add(w[:-3] + "Y")

    # -IED → -Y  (TRIED → TRY)
    if w.endswith("IED") and len(w) > 4:
        add(w[:-3] + "Y")

    # -VES → -F  (ELVES → ELF, LEAVES → LEAF)
    if w.endswith("VES") and len(w) > 4:
        add(w[:-3] + "F")
        add(w[:-3] + "FE")

    # -ING forms (gerund / present participle)
    if w.endswith("ING") and len(w) > 5:
        base = w[:-3]
        add(base)                                      # JUMPING → JUMP
        add(base + "E")                                # RACING  → RACE
        if len(base) >= 2 and base[-1] == base[-2]:   # RUNNING → RUN
            add(base[:-1])

    # -ED forms (past tense / past participle) — skip if already matched -IED
    if w.endswith("ED") and not w.endswith("IED") and len(w) > 4:
        base = w[:-2]
        add(base)                                      # JUMPED  → JUMP
        add(base + "E")                                # RACED   → RACE
        if len(base) >= 2 and base[-1] == base[-2]:   # STOPPED → STOP
            add(base[:-1])

    # -ES → base  (BOXES → BOX, SHOES → SHOE)
    if w.endswith("ES") and len(w) > 3:
        add(w[:-2])    # BOX
        add(w[:-1])    # SHOE  (also handles AXES → AXE)

    # -S → base   (CATS → CAT, EWTS → EWT)
    if w.endswith("S") and len(w) > 2:
        add(w[:-1])

    # -ER / -EST comparatives
    if w.endswith("EST") and len(w) > 5:
        add(w[:-3])          # FASTEST → FAST
        add(w[:-3] + "E")    # NICEST  → NICE
        if len(w) > 6 and w[-4] == w[-5]:   # BIGGEST → BIG
            add(w[:-4])
    elif w.endswith("ER") and len(w) > 4:
        add(w[:-2])          # FASTER  → FAST
        add(w[:-2] + "E")    # NICER   → NICE
        if len(w) > 5 and w[-3] == w[-4]:   # BIGGER  → BIG
            add(w[:-3])

    return out


def get_word_info(word: str) -> dict:
    """
    Build the full lookup payload for `word`.
    Returned dict is used identically by the web template and the CLI printer.

    Schema
    ------
    {
      "word":        str,           # uppercased input
      "collins_url": str,           # primary Collins dictionary link
      "base_forms":  [              # only forms that exist in CSW21
          {"word": str, "url": str},
          ...
      ],
      "all_candidates": [str],      # every guessed form (for the "tried" note)
    }
    """
    word_upper = word.upper()
    all_candidates = _candidates(word_upper)
    valid_bases = [c for c in all_candidates if c in WORD_SET]

    logger.debug(
        "get_word_info(%r): candidates=%r  valid_bases=%r",
        word_upper, all_candidates, valid_bases,
    )

    return {
        "word": word_upper,
        "collins_url": collins_url(word_upper),
        "base_forms": [{"word": b, "url": collins_url(b)} for b in valid_bases],
        "all_candidates": all_candidates,
    }


def format_word_info_text(info: dict, indent: str = "  ") -> str:
    """
    Render `get_word_info()` output as plain text for the CLI.
    Shared so UI and CLI produce structurally identical information.
    """
    lines: list[str] = []
    lines.append(f"{indent}Collins: {info['collins_url']}")

    if info["base_forms"]:
        for b in info["base_forms"]:
            lines.append(f"{indent}If not found, try base form [{b['word']}]: {b['url']}")
    elif info["all_candidates"]:
        tried = ", ".join(info["all_candidates"][:6])
        lines.append(
            f"{indent}Note: Collins may not list this word. "
            f"Tried base forms ({tried}) — none in CSW21."
        )

    return "\n".join(lines)
