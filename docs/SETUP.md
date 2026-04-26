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

ngrok creates a temporary public HTTPS URL that tunnels to your local server.  This is useful for playing remotely with friends — they open the URL in their browser with no setup required.

On the **free tier**, the URL is randomly assigned each session (e.g. `https://abc123.ngrok-free.app`).  It changes every time you restart, so just copy it from the terminal and share it (message, chat, etc.) at the start of each session.

### 1. Install ngrok

Minimum required version: **3.20.0**.  Install via a package manager to get automatic updates:

```powershell
# Windows — recommended (keeps ngrok up to date)
scoop install ngrok

# macOS
brew install ngrok/ngrok/ngrok
```

Or download directly from https://ngrok.com/download.

### 2. Create a free account and get your auth token

1. Sign up at https://ngrok.com (free, no credit card)
2. Go to https://dashboard.ngrok.com/get-started/your-authtoken
3. Copy your token

### 3. Save the token to your project (one-time)

```bash
python serve.py --add-token YOUR_TOKEN_HERE
```

This writes `ngrok.yml` in the project directory (gitignored).  Your global ngrok configuration is not touched.

### 4. Start with a public URL

```bash
python serve.py
```

The public URL is printed in the terminal.  Share it with anyone on any network.

```
======================================================
  Local  : http://localhost:8080
  Public : https://abc123.ngrok-free.app
======================================================
```

Press `Ctrl+C` to stop both the server and the tunnel.

---

### ngrok free tier — important notes

| Topic | Detail |
|-------|--------|
| URL persistence | Changes every session — share fresh each time |
| Static domains | Require a paid ngrok plan |
| Cloud Endpoints | **Avoid** — `.ngrok-free.dev` addresses are always-on cloud infrastructure that conflicts with agent tunnels and shows a default ngrok page instead of your app |

> **If you accidentally created a Cloud Endpoint:** go to the ngrok dashboard → **Endpoints**, find the `.ngrok-free.dev` address, and delete it.  Then `python serve.py` will work normally.

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
| ngrok: ERR_NGROK_334 "endpoint already online" | You have a Cloud Endpoint registered — delete it in the ngrok dashboard under **Endpoints** |
| ngrok: shows default ngrok page instead of app | Same cause as above — delete the Cloud Endpoint from the dashboard |
