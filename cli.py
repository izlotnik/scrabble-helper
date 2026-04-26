#!/usr/bin/env python
"""
Scrabble Helper — command-line interface (CSW21 British English)

MODES
-----
  validate  Check whether a word is valid in CSW21
  suggest   Find words you can play from your rack tiles
  pattern   Find all CSW21 words matching a pattern (no rack needed)

RACK FORMAT
-----------
  Letters A-Z (case-insensitive), one character per tile.
  Use ? for a blank tile (acts as any letter, scores 0 points).
  Example:  RSTLNEI      (seven tiles)
            RST?NEI      (six tiles + one blank)

PATTERN FORMAT
--------------
  _   (underscore)  exactly one letter — unknown position
  *   (asterisk)    zero or more letters — variable length gap
  A-Z               literal letter — must match exactly (case-insensitive)

  Examples:
    _T_W_     5-letter word, T in position 2, W in position 4
    *ING      any word ending in ING
    S*S       any word starting and ending with S
    *QU*      any word containing QU
    *T_W*     any word containing T, exactly one letter, then W
    ___       any 3-letter word (three underscores)
"""
import argparse
import sys
import logging

from app.logging_config import configure_logging

configure_logging()
logger = logging.getLogger("cli")


def _print_grouped(grouped: dict, rack_size: int = 7) -> None:
    """Print words grouped by length, highest length first."""
    if not grouped:
        print("  (no words found)")
        return
    for length in sorted(grouped.keys(), reverse=True):
        items = grouped[length]
        sep = "-" * 40
        label_str = f"{length} letters ({len(items)} word{'s' if len(items)!=1 else ''})"
        if isinstance(items[0], tuple):
            # (word, score, rack_tiles) tuples from suggest
            print(f"\n{sep}")
            print(f"  {label_str}")
            print(sep)
            for word, sc, rt in items:
                bingo = "  ** BINGO **" if rt == rack_size and rack_size >= 7 else ""
                print(f"  {word:<15} {sc:>3} pts{bingo}")
        else:
            # plain words from pattern
            print(f"\n{sep}")
            print(f"  {label_str}")
            print(sep)
            cols = 6
            for i in range(0, len(items), cols):
                print("  " + "  ".join(f"{w:<12}" for w in items[i:i+cols]))


def cmd_validate(args) -> int:
    from app.word_finder import validate_word
    word = args.word.strip().upper()
    if not word.isalpha():
        print(f"ERROR: '{word}' contains non-letter characters. Use A-Z only.")
        logger.error("Invalid input for validate: %r", args.word)
        return 2

    valid = validate_word(word)
    if valid:
        from app.word_finder import score_word
        sc = score_word(word)
        print(f"[VALID]   {word}  ({sc} pts face value)")
        logger.info("CLI validate %r -> VALID (%d pts)", word, sc)
        return 0
    else:
        print(f"[INVALID] {word} is NOT in the CSW21 dictionary")
        logger.info("CLI validate %r -> INVALID", word)
        return 1


def cmd_suggest(args) -> int:
    from app.word_finder import find_words, group_by_length

    rack = args.rack.strip().upper()
    invalid = [c for c in rack if not c.isalpha() and c != "?"]
    if invalid:
        print(f"ERROR: Invalid tile character(s): {', '.join(set(invalid))}")
        print("       Use A-Z for tiles, ? for a blank tile.")
        return 2

    try:
        length_int = int(args.length) if args.length else 0
    except ValueError:
        print("ERROR: --length must be a whole number.")
        return 2

    try:
        results = find_words(
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

    if not results:
        print(f"No CSW21 words found for rack '{rack}' with those filters.")
        return 0

    grouped = group_by_length(results)
    print(f"\nRack: {rack}   |   {len(results)} word{'s' if len(results)!=1 else ''} found")
    if args.starts_with: print(f"  Starts with : {args.starts_with.upper()}")
    if args.ends_with:   print(f"  Ends with   : {args.ends_with.upper()}")
    if args.contains:    print(f"  Contains    : {args.contains.upper()}")
    if length_int:       print(f"  Length      : {length_int}")
    if args.pattern:     print(f"  Pattern     : {args.pattern}")
    _print_grouped(grouped, rack_size=len(rack))
    print()
    logger.info("CLI suggest rack=%r -> %d results", rack, len(results))
    return 0


def cmd_pattern(args) -> int:
    from app.pattern import find_by_pattern, group_by_length

    pat = args.pattern.strip()
    try:
        words = find_by_pattern(pat)
    except ValueError as exc:
        print(f"ERROR: {exc}")
        return 2

    if not words:
        print(f"No CSW21 words match pattern '{pat}'.")
        return 0

    grouped = group_by_length(words)
    print(f"\nPattern: {pat}   |   {len(words)} word{'s' if len(words)!=1 else ''} found")
    _print_grouped(grouped)
    print()
    logger.info("CLI pattern %r -> %d results", pat, len(words))
    return 0


def build_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="python cli.py",
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    sub = parser.add_subparsers(dest="command", metavar="MODE")
    sub.required = True

    # ── validate ──────────────────────────────────────────────────────────────
    p_val = sub.add_parser(
        "validate", aliases=["v"],
        help="Check if a word is valid in CSW21",
        description=(
            "Check whether WORD exists in the CSW21 (Collins Scrabble Words 2021) dictionary.\n"
            "Letters only (A-Z), no numbers or punctuation."
        ),
    )
    p_val.add_argument("word", metavar="WORD", help="The word to validate (e.g. STEW)")
    p_val.set_defaults(func=cmd_validate)

    # ── suggest ───────────────────────────────────────────────────────────────
    p_sug = sub.add_parser(
        "suggest", aliases=["s", "find"],
        help="Find words you can play from your rack",
        description=(
            "Find all CSW21 words that can be formed from RACK tiles.\n\n"
            "RACK FORMAT:\n"
            "  Use letters A-Z (case-insensitive), one per tile.\n"
            "  Use ? for a blank tile (any letter, scores 0 points).\n"
            "  Example:  RSTLNEI   or   RST?NEI  (with one blank)\n\n"
            "PATTERN FORMAT (--pattern):\n"
            "  _  = exactly one unknown letter\n"
            "  *  = zero or more letters\n"
            "  A-Z = literal letter\n"
            "  Example: *T_W*  matches any word with T, one letter, then W"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_sug.add_argument(
        "rack", metavar="RACK",
        help="Your tiles, e.g. RSTLNEI  (use ? for blank tile)",
    )
    p_sug.add_argument("--starts-with", metavar="LETTERS", default="",
                       help="Word must start with these letters (e.g. --starts-with E)")
    p_sug.add_argument("--ends-with", metavar="LETTERS", default="",
                       help="Word must end with these letters (e.g. --ends-with ING)")
    p_sug.add_argument("--contains", metavar="LETTERS", default="",
                       help="Word must contain these letters (e.g. --contains X)")
    p_sug.add_argument("--length", metavar="N", default="",
                       help="Exact word length (e.g. --length 5)")
    p_sug.add_argument(
        "--pattern", metavar="MASK", default="",
        help=(
            "Pattern mask applied to suggested words.\n"
            "_ = one letter, * = any letters, A-Z = literal.\n"
            "Example: --pattern '*T_W*'"
        ),
    )
    p_sug.set_defaults(func=cmd_suggest)

    # ── pattern ───────────────────────────────────────────────────────────────
    p_pat = sub.add_parser(
        "pattern", aliases=["p"],
        help="Find all CSW21 words matching a pattern (no rack needed)",
        description=(
            "Find every CSW21 word that matches the given pattern.\n\n"
            "PATTERN FORMAT:\n"
            "  _  (underscore)  = exactly one unknown letter\n"
            "  *  (asterisk)    = zero or more letters\n"
            "  A-Z              = literal letter (case-insensitive)\n\n"
            "EXAMPLES:\n"
            "  python cli.py pattern '_T_W_'   5-letter word, T at pos 2, W at pos 4\n"
            "  python cli.py pattern '*ING'     any word ending in ING\n"
            "  python cli.py pattern 'S*S'      starts and ends with S\n"
            "  python cli.py pattern '*QU*'     any word containing QU\n"
            "  python cli.py pattern '___'      any 3-letter word\n"
            "  python cli.py pattern '*T_W*'    word with T, one letter, then W"
        ),
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    p_pat.add_argument(
        "pattern", metavar="PATTERN",
        help="Pattern to match (e.g. '*ING' or '_T_W_'  — quote it in the shell)",
    )
    p_pat.set_defaults(func=cmd_pattern)

    return parser


def main() -> None:
    parser = build_parser()
    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
