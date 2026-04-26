import logging
import pathlib

import jinja2
from fastapi import FastAPI, Request
from fastapi.responses import HTMLResponse
from fastapi.staticfiles import StaticFiles
from fastapi.templating import Jinja2Templates

from app.logging_config import configure_logging
from app.word_finder import find_words, validate_word, apply_top
from app.pattern import find_by_pattern, apply_top as pattern_apply_top
from app.links import get_word_info
from app.phrase_finder import find_phrases, phrase_is_common, MAX_LETTERS

# Web-only timeout for the phrase builder DFS — prevents long-running requests.
# The CLI has no timeout (runs to completion).
PHRASE_WEB_TIMEOUT_SEC = 8.0

configure_logging()
logger = logging.getLogger(__name__)

app = FastAPI(title="Scrabble Helper")

_BASE = pathlib.Path(__file__).parent.parent
app.mount("/static", StaticFiles(directory=_BASE / "static"), name="static")

# cache_size=0 avoids a Python 3.14 incompatibility with Jinja2's LRUCache
_jinja_env = jinja2.Environment(
    loader=jinja2.FileSystemLoader(_BASE / "templates"),
    autoescape=jinja2.select_autoescape(),
    cache_size=0,
)
templates = Jinja2Templates(env=_jinja_env)


def _render(request: Request, **ctx):
    return templates.TemplateResponse(request, "index.html", ctx)


# ── Home ──────────────────────────────────────────────────────────────────────

@app.get("/", response_class=HTMLResponse)
async def index(request: Request):
    logger.debug("GET / from %s", request.client)
    return _render(request, mode="validate", params={},
                   valid=None, word_info=None, error=None)


# ── Validate a single word ────────────────────────────────────────────────────

@app.get("/validate", response_class=HTMLResponse)
async def validate(request: Request, word: str = ""):
    params = {"word": word}
    valid = None
    word_info = None
    error = None

    if word.strip():
        cleaned = word.strip().upper()
        if not cleaned.isalpha():
            error = "Word must contain letters only (A-Z)."
        else:
            valid = validate_word(cleaned)
            word_info = get_word_info(cleaned)   # same function CLI uses
            logger.info("VALIDATE %r -> %s", cleaned, "VALID" if valid else "INVALID")

    return _render(request, mode="validate", params=params,
                   valid=valid, word_info=word_info, error=error)


# ── Suggest words from rack ───────────────────────────────────────────────────

@app.get("/suggest", response_class=HTMLResponse)
async def suggest(
    request: Request,
    rack: str = "",
    starts_with: str = "",
    ends_with: str = "",
    contains: str = "",
    length: str = "",
    pattern: str = "",
    top: str = "",
    per_group: str = "",
):
    params = dict(rack=rack, starts_with=starts_with, ends_with=ends_with,
                  contains=contains, length=length, pattern=pattern,
                  top=top, per_group=per_group)
    grouped = None
    total = 0
    shown = 0
    error = None
    rack_size = 0
    bingo_lengths: set[int] = set()

    if rack.strip():
        rack_clean = rack.strip().upper()
        rack_size = len(rack_clean)
        invalid_chars = [c for c in rack_clean if not c.isalpha() and c != "?"]
        if invalid_chars:
            error = (f"Invalid tile character(s): {', '.join(set(invalid_chars))}. "
                     "Use A-Z or ? for blank.")
        else:
            try:
                length_int = int(length) if length.strip() else 0
                top_int = int(top) if top.strip() else 0
            except ValueError:
                error = "Length and Top must be whole numbers."
                length_int = top_int = 0

            if not error:
                try:
                    results = find_words(
                        rack=rack_clean,
                        starts_with=starts_with.strip(),
                        ends_with=ends_with.strip(),
                        contains=contains.strip(),
                        length=length_int,
                        pattern=pattern.strip(),
                    )
                    total = len(results)
                    grouped = apply_top(results, top_int, per_group=bool(per_group))
                    shown = sum(len(v) for v in grouped.values())
                    bingo_lengths = {
                        length
                        for length, items in grouped.items()
                        if rack_size >= 7 and any(rt == rack_size for _, _, rt in items)
                    }
                except ValueError as exc:
                    error = str(exc)

    return _render(request, mode="suggest", params=params,
                   grouped=grouped, total=total, shown=shown, error=error,
                   rack_size=rack_size, bingo_lengths=bingo_lengths)


# ── Find words by pattern only (no rack) ─────────────────────────────────────

@app.get("/pattern", response_class=HTMLResponse)
async def by_pattern(
    request: Request,
    pattern: str = "",
    top: str = "",
    per_group: str = "",
):
    params = {"pattern": pattern, "top": top, "per_group": per_group}
    grouped = None
    total = 0
    shown = 0
    error = None

    if pattern.strip():
        try:
            top_int = int(top) if top.strip() else 0
        except ValueError:
            error = "Top must be a whole number."
            top_int = 0

        if not error:
            try:
                words = find_by_pattern(pattern.strip())
                total = len(words)
                grouped = pattern_apply_top(words, top_int, per_group=bool(per_group))
                shown = sum(len(v) for v in grouped.values())
                logger.info("PATTERN %r -> %d results (showing %d)", pattern.strip(), total, shown)
            except ValueError as exc:
                error = str(exc)

    return _render(request, mode="pattern", params=params,
                   grouped=grouped, total=total, shown=shown, error=error)


# ── Phrase builder (multi-word anagram) ──────────────────────────────────────

@app.get("/phrase", response_class=HTMLResponse)
async def phrase_builder(
    request: Request,
    letters: str = "",
    min_len: str = "1",
    max_words: str = "4",
    names: str = "",
    common_only: str = "",
):
    params = {"letters": letters, "min_len": min_len, "max_words": max_words,
              "names": names, "common_only": common_only}
    combos = None
    total = 0
    timed_out = False
    error = None

    if letters.strip():
        cleaned = letters.strip().upper().replace(" ", "")
        if not cleaned.isalpha():
            error = "Letters must be A-Z only — no numbers, spaces, or punctuation."
        elif len(cleaned) > MAX_LETTERS:
            error = f"Too many letters — maximum {MAX_LETTERS}."
        else:
            try:
                min_len_int = max(1, int(min_len)) if min_len.strip() else 1
                max_words_int = max(2, int(max_words)) if max_words.strip() else 4
            except ValueError:
                error = "Min length and Max words must be whole numbers."
                min_len_int = max_words_int = 0

            if not error:
                extra = [w for w in names.replace(",", " ").split() if w.isalpha()] if names.strip() else None
                results, timed_out = find_phrases(
                    cleaned,
                    min_word_len=min_len_int,
                    max_words=max_words_int,
                    timeout_sec=PHRASE_WEB_TIMEOUT_SEC,
                    extra_words=extra,
                )
                total = len(results)
                combos = [{"words": r, "common": phrase_is_common(r)} for r in results]
                if common_only:
                    combos = [c for c in combos if c["common"]]
                logger.info("PHRASE %r -> %d combinations%s", cleaned, total,
                            " (timed out)" if timed_out else "")

    return _render(request, mode="phrase", params=params,
                   combos=combos, total=total, timed_out=timed_out, error=error)
