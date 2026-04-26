"""
Word finder and validator against the CSW21 dictionary.

Rack format:   letters A-Z plus ? for blank tiles (worth 0 pts, any letter)
Pattern format: see app/pattern.py
"""
import logging
from collections import Counter
from app.dictionary import WORD_SET

logger = logging.getLogger(__name__)

LETTER_VALUES: dict[str, int] = {
    "A": 1,  "B": 3,  "C": 3,  "D": 2,  "E": 1,
    "F": 4,  "G": 2,  "H": 4,  "I": 1,  "J": 8,
    "K": 5,  "L": 1,  "M": 3,  "N": 1,  "O": 1,
    "P": 3,  "Q": 10, "R": 1,  "S": 1,  "T": 1,
    "U": 1,  "V": 4,  "W": 4,  "X": 8,  "Y": 4,
    "Z": 10,
}


def score_word(word: str) -> int:
    return sum(LETTER_VALUES.get(ch, 0) for ch in word.upper())


def validate_word(word: str) -> bool:
    """Return True if word is in the CSW21 dictionary."""
    result = word.upper() in WORD_SET
    logger.debug("validate_word(%r) -> %s", word.upper(), result)
    return result


def _can_form(word: str, rack_counter: Counter, blanks: int,
              board: Counter | None = None) -> bool:
    """Check if `word` can be formed from the rack, optionally with free board letters.

    When board letters are given the player must still contribute at least one
    rack tile — a word covered entirely by board tiles is not a legal play.
    """
    needed = Counter(word)
    if board:
        needed -= board  # Counter subtraction clamps at 0 — board letters are free
        if not needed:   # board covers every letter → no rack tile used → illegal
            return False
    shortage = sum(max(0, count - rack_counter.get(ch, 0)) for ch, count in needed.items())
    return shortage <= blanks


def find_words(
    rack: str,
    starts_with: str = "",
    ends_with: str = "",
    contains: str = "",
    length: int = 0,
    pattern: str = "",
) -> list[tuple[str, int]]:
    """
    Return (word, score) tuples for all CSW words formable from the rack,
    matching optional filters, sorted by score desc then word asc.

    rack      — up to 7 letters; ? = blank tile (any letter, 0 pts)
    pattern   — optional mask applied after rack check (see app/pattern.py)
    """
    from app.pattern import pattern_to_regex, validate_pattern

    rack_upper = rack.upper()
    blanks = rack_upper.count("?")
    rack_counter = Counter(ch for ch in rack_upper if ch != "?")

    # Each field supports | for OR alternatives, e.g. "Y|L" or "ING|ED".
    # Board letters (already on the board — not from the rack) are free for the player.
    sw_alts = [s for s in starts_with.upper().split("|") if s]
    ew_alts = [s for s in ends_with.upper().split("|") if s]
    ct_alts = [s for s in contains.upper().split("|") if s]

    pat_re = None
    # Literal letters in the pattern (A-Z) are board tiles — the player plays
    # through them, so they don't need to come from the rack.
    pat_board = Counter(ch for ch in pattern.upper() if ch.isalpha()) if pattern.strip() else Counter()
    if pattern.strip():
        err = validate_pattern(pattern)
        if err:
            raise ValueError(err)
        pat_re = pattern_to_regex(pattern)

    # Generous upper bound on word length (longest possible board contribution).
    max_board = (max((len(s) for s in sw_alts), default=0) +
                 max((len(s) for s in ew_alts), default=0) +
                 max((len(s) for s in ct_alts), default=0) +
                 sum(pat_board.values()))
    max_len = len(rack_upper) + max_board

    results: list[tuple[str, int, int]] = []
    for word in WORD_SET:
        if sw_alts and not any(word.startswith(s) for s in sw_alts):
            continue
        if ew_alts and not any(word.endswith(s) for s in ew_alts):
            continue
        if ct_alts and not any(s in word for s in ct_alts):
            continue
        if length and len(word) != length:
            continue
        if len(word) > max_len:
            continue
        if pat_re and not pat_re.match(word):
            continue

        # Try every combination of matching alternatives; include word if any works.
        # This handles e.g. contains="Y|L": a word with both Y and L is included
        # if the rack can cover everything except at least one of them.
        sw_hits = [s for s in sw_alts if word.startswith(s)] or [""]
        ew_hits = [s for s in ew_alts if word.endswith(s)] or [""]
        ct_hits = [s for s in ct_alts if s in word] or [""]
        max_rack_used: int | None = None
        word_ctr = Counter(word)
        for sw_h in sw_hits:
            for ew_h in ew_hits:
                for ct_h in ct_hits:
                    # Combine sw/ew/ct board letters with pattern literal letters
                    board_ctr = Counter(sw_h + ew_h + ct_h) + pat_board
                    board = board_ctr or None
                    if _can_form(word, rack_counter, blanks, board):
                        board_used = sum(
                            min(word_ctr[ch], board_ctr.get(ch, 0)) for ch in board_ctr
                        )
                        rt = len(word) - board_used
                        if max_rack_used is None or rt > max_rack_used:
                            max_rack_used = rt
        if max_rack_used is not None:
            results.append((word, score_word(word), max_rack_used))

    results.sort(key=lambda x: (-x[1], x[0]))
    logger.info(
        "find_words(rack=%r sw=%r ew=%r ct=%r len=%r pat=%r) -> %d results",
        rack, starts_with, ends_with, contains, length, pattern, len(results),
    )
    return results


def group_by_length(results: list[tuple[str, int, int]]) -> dict[int, list[tuple[str, int, int]]]:
    """Group (word, score, rack_tiles) list into {length: [...]} sorted by length desc."""
    groups: dict[int, list[tuple[str, int, int]]] = {}
    for word, sc, rt in results:
        groups.setdefault(len(word), []).append((word, sc, rt))
    return dict(sorted(groups.items(), reverse=True))


def apply_top(
    results: list[tuple[str, int, int]],
    top_n: int,
    per_group: bool = False,
) -> dict[int, list[tuple[str, int, int]]]:
    """
    Apply optional top-N limit then group by word length.

    top_n=0       — no limit, return all
    per_group=False — take the N highest-scoring words overall, then group
    per_group=True  — group first, then keep the top N within each length bucket
    """
    if per_group:
        grouped = group_by_length(results)
        if top_n:
            grouped = {k: v[:top_n] for k, v in grouped.items()}
        return grouped
    else:
        if top_n:
            results = results[:top_n]
        return group_by_length(results)
