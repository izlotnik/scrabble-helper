#!/usr/bin/env python
"""
scrabble.py — Scrabble Helper CLI  (CSW21, Collins Scrabble Words 2021)
======================================================================

MODES
-----
  validate (v)    Check if a word is valid in CSW21
  suggest  (s)    Find words playable from your rack tiles
  pattern  (p)    Find all CSW21 words matching a pattern (no rack needed)

RACK FORMAT
-----------
  Letters A-Z (case-insensitive).  Use ? for a blank tile
  (blank = any letter, scores 0 points).
  Maximum 7 tiles.
  Example:  RSTLNEI          seven tiles
            RST?NEI          six tiles + one blank

PATTERN FORMAT
--------------
  _   (underscore) = exactly one unknown letter
  *   (asterisk)   = zero or more letters (variable length)
  A-Z              = literal letter, must match exactly

  Examples:
    _T_W_     5-letter word, T at position 2, W at position 4
    *ING      any word ending in ING
    S*S       any word starting and ending with S
    *QU*      any word containing QU
    *T_W*     word containing T, exactly one letter, then W
    ___       every 3-letter word

COLLINS DICTIONARY LINKS
------------------------
  Every result includes a Collins Dictionary URL.
  URL format: https://www.collinsdictionary.com/dictionary/english/<word>
  For archaic/inflected Scrabble words Collins may not have a page; the CLI
  will suggest the most likely base form (e.g. EWTS → EWT) and show that URL.

LIMITING RESULTS  (suggest and pattern)
----------------------------------------
  --top N             Show only the top N results
  --per-group         Apply --top N per letter-length group instead of overall

  Examples:
    --top 5                   top 5 words overall (highest score / alphabetical)
    --top 5 --per-group       top 5 words within each letter-length bucket
    (omit --top to show all results)

BOARD TILES  (--starts-with / --ends-with / --contains)
-------------------------------------------------------
  These letters are already on the board — they do NOT need to be in your rack.
  Multi-letter values are supported.

  Examples:
    --starts-with QU          word begins with QU (board tiles — not from rack)
    --ends-with ING           word ends with ING  (board tiles)
    --contains TION           word contains TION  (board tiles)
    --starts-with RE --ends-with TION   combines freely

QUICK REFERENCE
---------------
  python scrabble.py validate STEW
  python scrabble.py v EWTS
  python scrabble.py suggest RSTLNEI
  python scrabble.py s STLNEI --starts-with QU --length 7
  python scrabble.py s STLNEI --ends-with ING
  python scrabble.py s RST?NEI --starts-with E --length 6
  python scrabble.py s RSTLNEI --pattern "*T_W*"
  python scrabble.py s RSTLNEI --top 5
  python scrabble.py s RSTLNEI --top 3 --per-group
  python scrabble.py pattern "_T_W_"
  python scrabble.py p "*ING" --top 10 --per-group
"""
import argparse
import sys
import logging

from app.logging_config import configure_logging

configure_logging()
logger = logging.getLogger("scrabble-cli")


# ─────────────────────────────────────────────────────────────────────────────
#  Shared printer helpers
# ─────────────────────────────────────────────────────────────────────────────

def _divider(label: str = "", width: int = 52) -> str:
    if label:
        pad = (width - len(label) - 2) // 2
        return f"{'=' * pad} {label} {'=' * (width - pad - len(label) - 2)}"
    return "=" * width


def _print_grouped(grouped: dict, rack_size: int = 7) -> None:
    """Print words grouped by length — works for both suggest and pattern results."""
    if not grouped:
        print("  (no words found)")
        return
    for length in sorted(grouped.keys(), reverse=True):
        items = grouped[length]
        is_suggest = items and isinstance(items[0], tuple)
        if is_suggest:
            bingo_marker = "  [** BINGO **]" if rack_size >= 7 and any(rt == rack_size for _, _, rt in items) else ""
        else:
            bingo_marker = ""
        print(f"\n{_divider(f'{length} letters  ({len(items)}){bingo_marker}')}")
        if is_suggest:
            # (word, score, rack_tiles) tuples from suggest
            for word, sc, rt in items:
                bingo_flag = "  [BINGO]" if rt == rack_size and rack_size >= 7 else ""
                print(f"  {word:<15} {sc:>3} pts{bingo_flag}")
        else:
            # plain word strings from pattern
            cols, col_w = 5, 14
            for i in range(0, len(items), cols):
                print("  " + "".join(f"{w:<{col_w}}" for w in items[i:i + cols]))


# ─────────────────────────────────────────────────────────────────────────────
#  Command handlers — each calls the same app/ functions the web UI uses
# ─────────────────────────────────────────────────────────────────────────────

def cmd_validate(args) -> int:
    from app.word_finder import validate_word, score_word
    from app.links import get_word_info, format_word_info_text

    word = args.word.strip().upper()
    if not word.isalpha():
        print(f"ERROR: '{word}' contains non-letter characters. Use A-Z only.")
        logger.error("validate: invalid input %r", args.word)
        return 2

    valid = validate_word(word)
    info = get_word_info(word)          # same function app/main.py uses

    if valid:
        sc = score_word(word)
        print(f"\n[VALID]   {word}  ({sc} pts face value)")
        print(format_word_info_text(info))
        logger.info("CLI validate %r -> VALID (%d pts)", word, sc)
        return 0
    else:
        print(f"\n[INVALID] {word} is NOT in the CSW21 dictionary")
        if info["base_forms"]:
            print("  Did you mean a base form?")
            for b in info["base_forms"]:
                print(f"    {b['word']}  ->  {b['url']}")
        logger.info("CLI validate %r -> INVALID", word)
        return 1


def cmd_suggest(args) -> int:
    from app.word_finder import find_words, apply_top

    rack = args.rack.strip().upper()
    bad = [c for c in rack if not c.isalpha() and c != "?"]
    if bad:
        print(f"ERROR: Invalid tile character(s): {', '.join(set(bad))}")
        print("       Use A-Z for tiles, ? for a blank tile.")
        return 2

    try:
        length_int = int(args.length) if args.length else 0
        top_int = int(args.top) if args.top else 0
    except ValueError:
        print("ERROR: --length and --top must be whole numbers.")
        return 2

    try:
        results = find_words(      # same function app/main.py uses
            rack=rack,
            starts_with=(args.starts_with or "").strip(),
            ends_with=(args.ends_with or "").strip(),
            contains=(args.contains or "").strip(),
            length=length_int,
            pattern=(args.pattern or "").strip(),
        )
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    total = len(results)
    grouped = apply_top(results, top_int, per_group=args.per_group)  # same as web UI
    shown = sum(len(v) for v in grouped.values())

    print(f"\n{_divider()}")
    print(f"  Rack: {rack}   |   {total} word{'s' if total != 1 else ''} found", end="")
    if top_int:
        scope = "per group" if args.per_group else "overall"
        print(f"  |   showing top {top_int} {scope} ({shown} shown)", end="")
    print()
    if args.starts_with: print(f"  Starts with : {args.starts_with.upper()}  (board tile(s))")
    if args.ends_with:   print(f"  Ends with   : {args.ends_with.upper()}  (board tile(s))")
    if args.contains:    print(f"  Contains    : {args.contains.upper()}  (board tile(s))")
    if length_int:       print(f"  Length      : {length_int}")
    if args.pattern:     print(f"  Pattern     : {args.pattern}")

    if grouped:
        _print_grouped(grouped, rack_size=len(rack))
    else:
        print("\n  No CSW21 words found for those tiles and filters.")

    print()
    logger.info("CLI suggest rack=%r -> %d results (shown %d)", rack, total, shown)
    return 0


def cmd_scramble(args) -> int:
    import random
    letters = args.letters.strip().upper()
    bad = [c for c in letters if not c.isalpha()]
    if bad:
        print(f"ERROR: Letters must be A-Z only — got: {', '.join(set(bad))}")
        return 2
    shuffled = list(letters)
    random.shuffle(shuffled)
    print("".join(shuffled))
    return 0


def cmd_phrase(args) -> int:
    from app.phrase_finder import find_phrases, phrase_is_common, MAX_LETTERS

    letters = args.letters.strip().upper().replace(" ", "")
    if not letters.isalpha():
        print("ERROR: Letters must be A-Z only — no numbers or punctuation.")
        return 2
    if len(letters) > MAX_LETTERS:
        print(f"ERROR: Too many letters — maximum {MAX_LETTERS}.")
        return 2

    try:
        min_len_int = max(1, int(args.min_len)) if args.min_len else 1
        max_words_int = max(2, int(args.max_words)) if args.max_words else 4
    except ValueError:
        print("ERROR: --min-len and --max-words must be whole numbers.")
        return 2

    extra = [w for w in args.names.replace(",", " ").split() if w.isalpha()] if args.names else None

    results, timed_out = find_phrases(
        letters,
        min_word_len=min_len_int,
        max_words=max_words_int,
        extra_words=extra,
    )
    total = len(results)

    if args.common_only:
        results = [r for r in results if phrase_is_common(r)]

    print(f"\n{_divider()}")
    suffix = " (timed out -- partial)" if timed_out else ""
    shown = len(results)
    count_str = f"{shown} of {total}" if shown != total else str(total)
    print(f"  Letters: {letters}   |   {count_str} combination{'s' if total != 1 else ''} found{suffix}")
    print()

    if results:
        for combo in results:
            marker = "[phrase] " if phrase_is_common(combo) else "         "
            print(f"  {marker}" + " + ".join(combo))
    else:
        print("  No combinations found. Try fewer letters, --max-words N, or remove --common.")

    print()
    logger.info("CLI phrase %r -> %d results%s", letters, total, " (timed out)" if timed_out else "")
    return 0


def cmd_pattern(args) -> int:
    from app.pattern import find_by_pattern, apply_top

    pat = args.pattern.strip()
    try:
        top_int = int(args.top) if args.top else 0
    except ValueError:
        print("ERROR: --top must be a whole number.")
        return 2

    try:
        words = find_by_pattern(pat)   # same function app/main.py uses
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    total = len(words)
    grouped = apply_top(words, top_int, per_group=args.per_group)  # same as web UI
    shown = sum(len(v) for v in grouped.values())

    print(f"\n{_divider()}")
    print(f"  Pattern: {pat}   |   {total} word{'s' if total != 1 else ''} found", end="")
    if top_int:
        scope = "per group" if args.per_group else "overall"
        print(f"  |   showing top {top_int} {scope} ({shown} shown)", end="")
    print()

    if grouped:
        _print_grouped(grouped)
    else:
        print("\n  No CSW21 words match that pattern.")

    print()
    logger.info("CLI pattern %r -> %d results (shown %d)", pat, total, shown)
    return 0


# ─────────────────────────────────────────────────────────────────────────────
#  Argument parser
# ─────────────────────────────────────────────────────────────────────────────

def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python scrabble.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
        add_help=True,
    )
    sub = parser.add_subparsers(dest="command", metavar="MODE")
    sub.required = True

    # ── validate ──────────────────────────────────────────────────────────────
    p_val = sub.add_parser(
        "validate", aliases=["v"],
        help="Check if a word is in CSW21",
        description=(
            "Validate WORD against the CSW21 (Collins Scrabble Words 2021) dictionary.\n\n"
            "Letters only — A-Z, no numbers, spaces, or punctuation.\n\n"
            "If Collins Dictionary does not have a page for the word (common for archaic\n"
            "or inflected Scrabble words), the tool will suggest the likely base form\n"
            "and show its Collins URL instead.\n\n"
            "Examples:\n"
            "  python scrabble.py validate STEW\n"
            "  python scrabble.py v EWTS"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_val.add_argument("word", metavar="WORD",
                       help="Word to check (e.g. STEW, EWTS, ZONKS)")
    p_val.set_defaults(func=cmd_validate)

    # ── suggest ───────────────────────────────────────────────────────────────
    p_sug = sub.add_parser(
        "suggest", aliases=["s", "find"],
        help="Find words playable from your rack tiles",
        description=(
            "Find all CSW21 words that can be formed from the tiles in RACK.\n\n"
            "RACK FORMAT:\n"
            "  A-Z  tile letters (case-insensitive), up to 7\n"
            "  ?    blank tile — plays as any letter, scores 0 points\n"
            "  Example:  RSTLNEI   or   RST?NEI   (one blank)\n\n"
            "BOARD TILE OPTIONS (letters already on the board — NOT from your rack):\n"
            "  --starts-with LETTERS   Word begins with LETTERS (multi-letter ok)\n"
            "  --ends-with   LETTERS   Word ends with LETTERS   (multi-letter ok)\n"
            "  --contains    LETTERS   Word contains LETTERS    (multi-letter ok)\n\n"
            "  Use | for OR alternatives — word must satisfy at least one:\n"
            "    --contains 'Y|L'        word contains Y or L (board tile)\n"
            "    --ends-with 'ING|ED'    word ends with ING or ED\n"
            "    --starts-with 'A|B|C'  word starts with A, B, or C\n\n"
            "OTHER FILTERS:\n"
            "  --length N      Word must be exactly N letters long (includes board tiles)\n"
            "  --pattern MASK  Word must match the mask (see PATTERN FORMAT below)\n\n"
            "PATTERN FORMAT (--pattern):\n"
            "  _  = exactly one unknown letter\n"
            "  *  = zero or more letters\n"
            "  A-Z = literal letter\n"
            "  Example: --pattern '*T_W*'   words containing T, one letter, then W\n"
            "           --pattern '____S'   5-letter words ending in S\n\n"
            "Results are grouped by word length (longest first).\n"
            "7-letter words are bingos (+50 pts when played on the board).\n\n"
            "LIMITING RESULTS:\n"
            "  --top N           Show only top N results\n"
            "  --per-group       Apply --top N per letter-length bucket instead of overall\n\n"
            "Examples:\n"
            "  python scrabble.py suggest RSTLNEI\n"
            "  python scrabble.py s STLNEI --starts-with QU         (QU on board)\n"
            "  python scrabble.py s STLNEI --ends-with ING          (ING on board)\n"
            "  python scrabble.py s RST?NEI --starts-with E --length 6\n"
            "  python scrabble.py s RSTLNEI --pattern '*T_W*'\n"
            "  python scrabble.py s RSTLNEI --top 5\n"
            "  python scrabble.py s RSTLNEI --top 3 --per-group"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_sug.add_argument("rack", metavar="RACK",
                       help="Your tiles, e.g. RSTLNEI  (use ? for blank tile)")
    p_sug.add_argument("--starts-with", metavar="LETTERS", default="",
                       help="Board tile(s) at start — use | for OR, e.g. 'A|B'")
    p_sug.add_argument("--ends-with", metavar="LETTERS", default="",
                       help="Board tile(s) at end — use | for OR, e.g. 'ING|ED'")
    p_sug.add_argument("--contains", metavar="LETTERS", default="",
                       help="Board tile(s) anywhere — use | for OR, e.g. 'Y|L'")
    p_sug.add_argument("--length", metavar="N", default="",
                       help="Exact word length (2-7)")
    p_sug.add_argument("--pattern", metavar="MASK", default="",
                       help="Pattern mask: _ = one letter, * = any letters, A-Z = literal")
    p_sug.add_argument("--top", metavar="N", default="",
                       help="Show only top N results (e.g. --top 5)")
    p_sug.add_argument("--per-group", action="store_true",
                       help="Apply --top N per letter-length group instead of overall")
    p_sug.set_defaults(func=cmd_suggest)

    # ── pattern ───────────────────────────────────────────────────────────────
    p_pat = sub.add_parser(
        "pattern", aliases=["p"],
        help="Find all CSW21 words matching a pattern (no rack needed)",
        description=(
            "Search the entire CSW21 dictionary for words matching PATTERN.\n"
            "No rack tiles needed — searches all 279,077 words.\n\n"
            "PATTERN FORMAT:\n"
            "  _  (underscore) = exactly one unknown letter\n"
            "  *  (asterisk)   = zero or more letters (variable length)\n"
            "  A-Z             = literal letter (case-insensitive)\n\n"
            "Examples:\n"
            "  python scrabble.py pattern '_T_W_'   5-letter: T at pos 2, W at pos 4\n"
            "  python scrabble.py p '*ING'           any word ending in ING\n"
            "  python scrabble.py p 'S*S'            starts and ends with S\n"
            "  python scrabble.py p '*QU*'           any word containing QU\n"
            "  python scrabble.py p '___'            every 3-letter word\n"
            "  python scrabble.py p '*T_W*'          T, one letter, W — anywhere\n\n"
            "LIMITING RESULTS:\n"
            "  --top N           Show only top N results (alphabetical within each group)\n"
            "  --per-group       Apply --top N per letter-length bucket instead of overall\n\n"
            "  python scrabble.py p '*ING' --top 10\n"
            "  python scrabble.py p '*ING' --top 5 --per-group\n\n"
            "Note: quote the pattern in the shell to prevent * expansion."
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_pat.add_argument(
        "pattern", metavar="PATTERN",
        help="Pattern to match — quote it: '*ING', '_T_W_', 'S*S'",
    )
    p_pat.add_argument("--top", metavar="N", default="",
                       help="Show only top N results (e.g. --top 10)")
    p_pat.add_argument("--per-group", action="store_true",
                       help="Apply --top N per letter-length group instead of overall")
    p_pat.set_defaults(func=cmd_pattern)

    # ── phrase ────────────────────────────────────────────────────────────────
    p_phr = sub.add_parser(
        "phrase", aliases=["ph"],
        help="Find word combinations that use all supplied letters",
        description=(
            "Find every combination of CSW21 words (plus A and I) that together\n"
            "use every letter in LETTERS exactly once.\n\n"
            "LETTERS FORMAT:\n"
            "  A-Z only, up to 15 letters, no blanks or spaces.\n\n"
            "Results are shown in sorted word order — rearrange them into the phrase you want.\n\n"
            "Examples:\n"
            "  python scrabble.py phrase YOUIEVOL          -> I + LOVE + YOU\n"
            "  python scrabble.py ph YOUIEVOL --max-words 3\n"
            "  python scrabble.py ph EARTHLINGS --min-len 3"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_phr.add_argument("letters", metavar="LETTERS",
                       help="Letter pool (A-Z only, no blanks, max 20)")
    p_phr.add_argument("--min-len", metavar="N", default="1",
                       help="Minimum letters per word (default: 1)")
    p_phr.add_argument("--max-words", metavar="N", default="4",
                       help="Maximum words per phrase (default: 4)")
    p_phr.add_argument("--names", metavar="WORDS", default="",
                       help="Extra words to include (names etc), space or comma separated")
    p_phr.add_argument("--common", dest="common_only", action="store_true",
                       help="Show only combinations where all words are common English words")
    p_phr.set_defaults(func=cmd_phrase)

    # ── scramble ──────────────────────────────────────────────────────────────
    p_sc = sub.add_parser(
        "scramble", aliases=["sc"],
        help="Shuffle a set of letters into a random order",
    )
    p_sc.add_argument("letters", metavar="LETTERS", help="Letters to shuffle (A-Z)")
    p_sc.set_defaults(func=cmd_scramble)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
