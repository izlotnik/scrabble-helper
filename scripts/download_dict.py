"""
One-time script to download the CSW21 (Collins Scrabble Words 2021) wordlist.
Run from the project root: python scripts/download_dict.py
"""
import urllib.request
import pathlib
import sys

# Official CSW21 — licensed by Collins/HarperCollins, hosted by scrabblewords project
CSW_URL = "https://raw.githubusercontent.com/scrabblewords/scrabblewords/main/words/British/CSW21.txt"
OUT_PATH = pathlib.Path(__file__).parent.parent / "data" / "csw.txt"


def parse_word(line: str) -> str | None:
    """Extract the bare word from a CSW21 annotation line.
    Lines look like:  STEW (something) a definition...
    Comment lines start with #.
    """
    line = line.strip()
    if not line or line.startswith("#"):
        return None
    word = line.split()[0]
    return word if word.isalpha() else None


def main():
    OUT_PATH.parent.mkdir(exist_ok=True)
    print(f"Downloading CSW21 wordlist from scrabblewords/scrabblewords ...")
    try:
        tmp = OUT_PATH.with_suffix(".tmp")
        urllib.request.urlretrieve(CSW_URL, tmp)

        words: list[str] = []
        with tmp.open(encoding="utf-8") as fh:
            for line in fh:
                w = parse_word(line)
                if w:
                    words.append(w.upper())

        with OUT_PATH.open("w", encoding="utf-8") as fh:
            fh.write("\n".join(words))

        tmp.unlink()
        print(f"Done — {len(words):,} CSW21 words saved to {OUT_PATH}")
    except Exception as e:
        print(f"Download failed: {e}", file=sys.stderr)
        sys.exit(1)


if __name__ == "__main__":
    main()
