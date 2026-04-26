"""
CSW21 dictionary loader.
Builds two lookup structures at import time:
  WORD_SET      — set of all valid words (uppercase), O(1) membership
  ANAGRAM_INDEX — sorted-letters -> [words]
"""
import pathlib
import logging
from collections import defaultdict

_DATA_FILE = pathlib.Path(__file__).parent.parent / "data" / "csw.txt"

logger = logging.getLogger(__name__)

WORD_SET: set[str] = set()
ANAGRAM_INDEX: dict[str, list[str]] = defaultdict(list)


def _load() -> None:
    if not _DATA_FILE.exists():
        raise FileNotFoundError(
            f"Dictionary not found at {_DATA_FILE}. "
            "Run:  python scripts/download_dict.py"
        )
    with _DATA_FILE.open(encoding="utf-8") as fh:
        for line in fh:
            word = line.strip().upper()
            if word.isalpha():
                WORD_SET.add(word)
                ANAGRAM_INDEX["".join(sorted(word))].append(word)
    logger.info("CSW21 loaded: %d words from %s", len(WORD_SET), _DATA_FILE)


_load()
