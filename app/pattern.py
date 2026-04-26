"""
Pattern / mask matching for word lookup.

Pattern syntax (case-insensitive):
  _   exactly one letter  (e.g.  _T_W_  = 5-letter word, T at pos 2, W at pos 4)
  *   zero or more letters (e.g. *ING   = any word ending in ING)
  A-Z literal letter

Examples
--------
  _T_W_    five-letter word with T in position 2 and W in position 4
  *ING     any word ending in ING
  S*       any word starting with S
  *QU*     any word containing QU
  *T_W*    any word containing T, then exactly one letter, then W
  ___      any 3-letter word (three underscores)

Note: rack blanks use ? (a different context).
"""
import re
import logging
from app.dictionary import WORD_SET

logger = logging.getLogger(__name__)

_SPECIAL = re.compile(r"[^A-Z_*]")


def validate_pattern(pattern: str) -> str | None:
    """Return an error message if the pattern is invalid, else None."""
    upper = pattern.upper()
    bad = _SPECIAL.findall(upper)
    if bad:
        unique = sorted(set(bad))
        return f"Invalid character(s) in pattern: {', '.join(repr(c) for c in unique)}. Use A-Z, _ (one letter), or * (any letters)."
    return None


def pattern_to_regex(pattern: str) -> re.Pattern[str]:
    """Convert a user-facing pattern string to a compiled regex."""
    parts: list[str] = []
    for ch in pattern.upper():
        if ch == "_":
            parts.append("[A-Z]")
        elif ch == "*":
            parts.append("[A-Z]*")
        else:
            parts.append(re.escape(ch))
    return re.compile("^" + "".join(parts) + "$")


def find_by_pattern(pattern: str) -> list[str]:
    """Return all CSW words matching the pattern, sorted alphabetically."""
    err = validate_pattern(pattern)
    if err:
        raise ValueError(err)
    compiled = pattern_to_regex(pattern)
    results = sorted(w for w in WORD_SET if compiled.match(w))
    logger.debug("Pattern %r matched %d words", pattern, len(results))
    return results


def group_by_length(words: list[str]) -> dict[int, list[str]]:
    """Group a flat list of words into {length: [words]} sorted by length desc."""
    groups: dict[int, list[str]] = {}
    for w in words:
        groups.setdefault(len(w), []).append(w)
    return dict(sorted(groups.items(), reverse=True))


def apply_top(
    words: list[str],
    top_n: int,
    per_group: bool = False,
) -> dict[int, list[str]]:
    """
    Apply optional top-N limit then group by word length.
    Words are already sorted alphabetically by find_by_pattern().

    top_n=0        — no limit
    per_group=False — take the first N words overall (alphabetical), then group
    per_group=True  — group first, keep first N per length bucket
    """
    if per_group:
        grouped = group_by_length(words)
        if top_n:
            grouped = {k: v[:top_n] for k, v in grouped.items()}
        return grouped
    else:
        if top_n:
            words = words[:top_n]
        return group_by_length(words)
