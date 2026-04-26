# Setup Guide

Complete instructions for installing and running Scrabble Helper from source.

---

## Prerequisites

| Requirement | Minimum | Notes |
|-------------|---------|-------|
| Python | 3.10 | 3.12+ recommended |
| Internet connection | — | one-time dictionary download |
| ngrok account | — | optional, only needed for public sharing |

---

## Installation

### 1. Get the code

```bash
git clone https://github.com/YOUR_USERNAME/scrabble-helper.git
cd scrabble-helper
```

### 2. Create a virtual environment

```bash
python -m venv .venv
```

Activate it:

| Platform | Command |
|----------|---------|
| Windows (PowerShell) | `.venv\Scripts\Activate.ps1` |
| Windows (cmd) | `.venv\Scripts\activate.bat` |
| macOS / Linux | `source .venv/bin/activate` |

### 3. Install dependencies

```bash
pip install -r requirements.txt
```

Key packages installed:

| Package | Purpose |
|---------|---------|
| `fastapi` + `uvicorn` | Web server |
| `jinja2` | HTML templates |
| `wordfreq` | Common-word detection in Phrase Builder |
| `pillow` | Image processing (Phase 2 board reader, reserved) |

### 4. Download the dictionary

The CSW21 word list (~279k words) is not included in the repository.  Fetch it once:

```bash
python scripts/download_dict.py
```

This downloads from the public [scrabblewords/scrabblewords](https://github.com/scrabblewords/scrabblewords) repository and saves to `data/csw.txt`.

> **Offline install** — if you have a CSW21 word list from another source, place it at `data/csw.txt` as one uppercase word per line.  Any lines that are not purely alphabetic are ignored.

---

## Running

### Web app

```bash
python serve.py
```

Open **http://localhost:8080** in your browser.

To use a different port:

```bash
python serve.py --port 9000
```

### CLI

```bash
python scrabble.py --help
python scrabble.py validate ZOEAE
python scrabble.py suggest RSTLNEI
python scrabble.py pattern "*ING" --top 20
python scrabble.py phrase YOUIEVOL
```

---

## Public sharing with ngrok (optional)

ngrok creates a temporary public HTTPS URL that tunnels to your local server.  This is useful for playing remotely with friends.

### Install ngrok

```powershell
# Windows (scoop)
scoop install ngrok

# macOS (homebrew)
brew install ngrok/ngrok/ngrok
```

Or download directly from https://ngrok.com/download.

### Add your auth token (one-time, project-local)

1. Sign up free at https://ngrok.com
2. Copy your token from https://dashboard.ngrok.com/get-started/your-authtoken
3. Run:

```bash
python serve.py --add-token YOUR_TOKEN_HERE
```

This writes `ngrok.yml` in the project directory (excluded from git).  Your global ngrok configuration is not touched.

### Start with a public URL

```bash
python serve.py
```

The public URL is printed in the terminal.  Share it with anyone — they can use the app in their browser without installing anything.

---

## Logs

Application logs are written to `logs/scrabble.log` (rotating, 10 MB × 5 files).  The `logs/` directory is excluded from git.

---

## Troubleshooting

| Problem | Fix |
|---------|-----|
| `Dictionary not found` | Run `python scripts/download_dict.py` |
| `ModuleNotFoundError` | Activate the venv: `.venv\Scripts\Activate.ps1` |
| Port already in use | `python serve.py --port 9000` |
| ngrok: version too old | `scoop update ngrok` or download from ngrok.com/download |
| ngrok: authtoken not configured | `python serve.py --add-token YOUR_TOKEN` |
