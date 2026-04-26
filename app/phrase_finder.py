"""
Phrase builder — find multi-word combinations that use all supplied letters.

Given a pool of letters, returns every set of CSW21 words (plus "A" and "I",
which are valid English words absent from the Scrabble-only CSW21 list) that
collectively use *all* letters exactly once.

Results are lists of words in sorted order; the caller can rearrange them
into the desired phrase.
"""
import logging
import time
from collections import Counter
from app.dictionary import WORD_SET

logger = logging.getLogger(__name__)

MAX_LETTERS = 20
MAX_RESULTS = 500

# Frequency threshold below which a word is considered an obscure Scrabble word
# rather than a common English word. Calibrated so LOVE (~6e-4) passes and
# CEE (~9e-7) / MONTHLING (0.0) do not.
COMMON_THRESHOLD = 1e-5

# A and I are valid single-letter English words not in CSW21 (min 2 letters in Scrabble)
_EXTRAS = {"A", "I"}
_AUGMENTED = WORD_SET | _EXTRAS


def _can_form(word: str, pool: Counter) -> bool:
    for ch, count in Counter(word).items():
        if pool.get(ch, 0) < count:
            return False
    return True


def phrase_is_common(words: list[str]) -> bool:
    """Return True if every word in the combination is a common English word."""
    from wordfreq import word_frequency
    return all(word_frequency(w.lower(), "en") >= COMMON_THRESHOLD for w in words)


def find_phrases(
    letters: str,
    min_word_len: int = 1,
    max_words: int = 4,
    max_results: int = MAX_RESULTS,
    timeout_sec: float = 0.0,
    extra_words: list[str] | None = None,
) -> tuple[list[list[str]], bool]:
    """
    Return (results, timed_out) where results is a list of word-lists that
    together use all letters exactly, and timed_out is True if the search was
    cut short by the timeout.

    letters      — A-Z only (uppercase); caller must validate and strip spaces
    min_word_len — minimum letters per word (1 to include A and I)
    max_words    — maximum words per combination (depth limit)
    max_results  — stop collecting after this many combinations
    timeout_sec  — stop after this many seconds (0 = no limit)
    extra_words  — additional words to include (e.g. proper names not in CSW21)
    """
    pool = Counter(letters.upper())

    vocabulary = _AUGMENTED
    if extra_words:
        clean = {w.strip().upper() for w in extra_words if w.strip().isalpha()}
        if clean:
            vocabulary = vocabulary | clean

    candidates = sorted(
        w for w in vocabulary
        if len(w) >= min_word_len and _can_form(w, pool)
    )

    results: list[list[str]] = []
    timed_out = False
    deadline = time.perf_counter() + timeout_sec if timeout_sec > 0 else None
    call_count = 0

    def dfs(remaining: Counter, current: list[str]) -> None:
        nonlocal timed_out, call_count
        if timed_out or len(results) >= max_results:
            return
        call_count += 1
        if deadline and call_count % 5000 == 0 and time.perf_counter() > deadline:
            timed_out = True
            return
        if sum(remaining.values()) == 0:
            results.append(list(current))
            return
        if len(current) >= max_words:
            return
        for word in candidates:
            if current and word < current[-1]:  # sorted order → no permutation duplicates
                continue
            if _can_form(word, remaining):
                for ch in word:
                    remaining[ch] -= 1
                current.append(word)
                dfs(remaining, current)
                current.pop()
                for ch in word:
                    remaining[ch] += 1

    dfs(pool, [])
    logger.info(
        "find_phrases(letters=%r min_len=%d max_words=%d timeout=%.1fs extra=%r) -> %d results%s",
        letters, min_word_len, max_words, timeout_sec,
        list(extra_words) if extra_words else None,
        len(results), " (timed out)" if timed_out else "",
    )
    return results, timed_out
