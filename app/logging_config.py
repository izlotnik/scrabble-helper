"""
Centralised logging configuration.

Call configure_logging() exactly once at application or CLI startup.

Log destinations
----------------
  logs/scrabble.log  — rotating file, all levels (DEBUG and above)
  stderr             — console, INFO and above

Rotation
--------
  Each log file grows to LOG_MAX_BYTES before being rotated.
  Up to LOG_BACKUP_COUNT older files are kept (scrabble.log.1 … .5).
"""
import logging
import logging.handlers
import pathlib

# ── Configuration ─────────────────────────────────────────────────────────────

_LOG_DIR = pathlib.Path(__file__).parent.parent / "logs"
_LOG_FILE = _LOG_DIR / "scrabble.log"

LOG_MAX_BYTES = 10 * 1024 * 1024   # 10 MB per file
LOG_BACKUP_COUNT = 5                # keep 5 rotated files

_FMT = "%(asctime)s  %(levelname)-8s  %(name)s  %(message)s"
_DATE_FMT = "%Y-%m-%d %H:%M:%S"


# ── Public API ────────────────────────────────────────────────────────────────

def configure_logging(level: int = logging.DEBUG) -> None:
    """Configure root logger with a rotating file handler and a console handler.

    Idempotent — safe to call multiple times; only the first call has effect.
    """
    _LOG_DIR.mkdir(exist_ok=True)

    root = logging.getLogger()
    if root.handlers:
        return

    root.setLevel(level)

    file_handler = logging.handlers.RotatingFileHandler(
        _LOG_FILE,
        maxBytes=LOG_MAX_BYTES,
        backupCount=LOG_BACKUP_COUNT,
        encoding="utf-8",
    )
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter(_FMT, _DATE_FMT))

    console_handler = logging.StreamHandler()
    console_handler.setLevel(logging.INFO)
    console_handler.setFormatter(logging.Formatter(_FMT, _DATE_FMT))

    root.addHandler(file_handler)
    root.addHandler(console_handler)
