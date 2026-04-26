#!/usr/bin/env python
"""
serve.py — start the Scrabble Helper web server, optionally with an ngrok tunnel.

Usage
-----
    python serve.py                              # local server on port 8080
    python serve.py --port 9000                 # different port
    python serve.py --add-token YOUR_TOKEN      # save ngrok auth token, then exit
    python serve.py --set-domain YOUR_DOMAIN    # save static domain, then exit

ngrok is entirely optional.  If it is not installed, or if no auth token is
configured, the server starts in local-only mode and a warning is printed.
No functionality of the Scrabble Helper itself is affected.

Auth token setup (one-time, project-local)
------------------------------------------
    1. Sign up free at https://ngrok.com
    2. Copy your token from https://dashboard.ngrok.com/get-started/your-authtoken
    3. Run:  python serve.py --add-token YOUR_TOKEN

Static domain setup (optional — gives a permanent public URL)
-------------------------------------------------------------
    1. In the ngrok dashboard go to Cloud Edge → Domains
    2. Claim your free static domain (e.g. fluffy-tiger-42.ngrok-free.app)
    3. Run:  python serve.py --set-domain fluffy-tiger-42.ngrok-free.app

Both the token and domain are stored in ngrok.yml inside this project directory
and are never written to the global ngrok config.  ngrok.yml is excluded from git.
"""
import argparse
import json
import subprocess
import sys
import time
import urllib.error
import urllib.request
from pathlib import Path

# ── Configuration ─────────────────────────────────────────────────────────────

DEFAULT_PORT = 8080

# ngrok's local management API — always runs on this port when ngrok is active
NGROK_API_PORT = 4040
NGROK_API_URL = f"http://localhost:{NGROK_API_PORT}/api/tunnels"

# Seconds to wait for ngrok to establish its tunnel before giving up
NGROK_STARTUP_TIMEOUT = 15

# Project-local ngrok config file (token stored here, not in global config)
LOCAL_NGROK_CONFIG = Path(__file__).parent / "ngrok.yml"

# Stores the static domain separately — ngrok.yml only accepts authtoken,
# not arbitrary keys, so we keep the domain in its own file.
NGROK_DOMAIN_FILE = Path(__file__).parent / ".ngrok_domain"

# Known install locations for ngrok on Windows when PATH is not yet refreshed
_NGROK_FALLBACK_PATHS = [
    Path.home() / "AppData/Local/Microsoft/WinGet/Packages"
    / "Ngrok.Ngrok_Microsoft.Winget.Source_8wekyb3d8bbwe/ngrok.exe",
    Path.home() / "scoop/apps/ngrok/current/ngrok.exe",
]


# ── Helpers ───────────────────────────────────────────────────────────────────

def _read_ngrok_config() -> dict:
    """Parse ngrok.yml into a plain dict (authtoken only). Missing file → {}."""
    cfg: dict = {}
    if not LOCAL_NGROK_CONFIG.exists():
        return cfg
    for line in LOCAL_NGROK_CONFIG.read_text().splitlines():
        if ":" in line:
            key, _, val = line.partition(":")
            key, val = key.strip(), val.strip()
            if key == "authtoken":
                cfg[key] = val
    return cfg


def _write_ngrok_config(cfg: dict) -> None:
    """Write authtoken to ngrok.yml (domain is stored separately in .ngrok_domain)."""
    lines = ['version: "2"']
    if "authtoken" in cfg:
        lines.append(f"authtoken: {cfg['authtoken']}")
    LOCAL_NGROK_CONFIG.write_text("\n".join(lines) + "\n")


def _read_static_domain() -> str:
    """Return the saved static domain, or empty string if not set."""
    if NGROK_DOMAIN_FILE.exists():
        return NGROK_DOMAIN_FILE.read_text().strip()
    return ""


def find_ngrok() -> str | None:
    """Return the path to the ngrok binary, or None if not installed."""
    import shutil
    found = shutil.which("ngrok")
    if found:
        return found
    for p in _NGROK_FALLBACK_PATHS:
        if p.exists():
            return str(p)
    return None


def get_running_ngrok_url() -> str:
    """Return the HTTPS public URL if ngrok is already running locally, else ''."""
    try:
        with urllib.request.urlopen(NGROK_API_URL, timeout=2) as resp:
            data = json.loads(resp.read())
            for tunnel in data.get("tunnels", []):
                url = tunnel.get("public_url", "")
                if url.startswith("https://"):
                    return url
            tunnels = data.get("tunnels", [])
            if tunnels:
                return tunnels[0].get("public_url", "")
    except (urllib.error.URLError, OSError):
        pass
    return ""


def wait_for_ngrok_url(timeout: int = NGROK_STARTUP_TIMEOUT) -> str:
    """Poll ngrok's local API until the HTTPS public URL appears, or timeout."""
    deadline = time.time() + timeout
    while time.time() < deadline:
        url = get_running_ngrok_url()
        if url:
            return url
        time.sleep(0.5)
    return ""


# ── Main ──────────────────────────────────────────────────────────────────────

def main() -> None:
    parser = argparse.ArgumentParser(
        description=__doc__,
        formatter_class=argparse.RawDescriptionHelpFormatter,
    )
    parser.add_argument(
        "--port", type=int, default=DEFAULT_PORT, metavar="N",
        help=f"Local port for the web server (default: {DEFAULT_PORT})",
    )
    parser.add_argument(
        "--add-token", metavar="TOKEN",
        help="Save an ngrok auth token to project-local ngrok.yml and exit",
    )
    parser.add_argument(
        "--set-domain", metavar="DOMAIN",
        help="Save a static ngrok domain to project-local ngrok.yml and exit",
    )
    args = parser.parse_args()

    # ── one-time config setup ─────────────────────────────────────────────────
    if args.add_token or args.set_domain:
        if args.add_token:
            cfg = _read_ngrok_config()
            cfg["authtoken"] = args.add_token.strip()
            _write_ngrok_config(cfg)
            print(f"Token saved to {LOCAL_NGROK_CONFIG}")
        if args.set_domain:
            NGROK_DOMAIN_FILE.write_text(args.set_domain.strip() + "\n")
            print(f"Static domain saved to {NGROK_DOMAIN_FILE.name}: {args.set_domain.strip()}")
        print("Run 'python serve.py' to start the server.")
        return

    # ── start uvicorn ─────────────────────────────────────────────────────────
    venv_uvicorn = Path(".venv/Scripts/uvicorn")
    uvicorn_bin = str(venv_uvicorn) if venv_uvicorn.exists() else "uvicorn"

    print(f"\n[1] Starting Scrabble Helper on http://localhost:{args.port} …")
    server = subprocess.Popen(
        [uvicorn_bin, "app.main:app", "--host", "0.0.0.0", "--port", str(args.port)],
        cwd=Path(__file__).parent,
        stdout=subprocess.DEVNULL,
        stderr=subprocess.DEVNULL,
    )
    time.sleep(1.5)
    if server.poll() is not None:
        sys.exit(
            "ERROR: uvicorn failed to start.  Run manually to see the error:\n"
            f"  .venv\\Scripts\\uvicorn app.main:app --port {args.port}"
        )

    # ── attempt ngrok tunnel (optional) ───────────────────────────────────────
    ngrok = find_ngrok()
    ngrok_proc = None

    if not ngrok:
        print("[2] ngrok not found — running in local-only mode.")
        print("    Install ngrok (scoop install ngrok) to expose the server publicly.")
    else:
        static_domain = _read_static_domain()

        # Reuse tunnel if ngrok is already running (avoids ERR_NGROK_334)
        existing_url = get_running_ngrok_url()
        if existing_url:
            print(f"[2] ngrok already running — reusing existing tunnel.")
            public_url = existing_url
            ngrok_proc = None
        else:
            print(f"[2] Starting ngrok tunnel → port {args.port} …")
            ngrok_cmd = [ngrok]
            if LOCAL_NGROK_CONFIG.exists():
                ngrok_cmd += ["--config", str(LOCAL_NGROK_CONFIG)]
                print(f"    (using project token from {LOCAL_NGROK_CONFIG.name})")
            ngrok_cmd += ["http", str(args.port)]
            if static_domain:
                ngrok_cmd += ["--url", static_domain]
                print(f"    (static domain: {static_domain})")

            ngrok_proc = subprocess.Popen(
                ngrok_cmd,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.PIPE,
            )
            print("[3] Waiting for public URL …")
            public_url = wait_for_ngrok_url()

            if not public_url:
                rc = ngrok_proc.poll()
                if rc is not None:
                    stderr_out = ngrok_proc.stderr.read().decode(errors="replace").strip()
                    print(f"\n  WARNING: ngrok exited (code {rc}).")
                    if stderr_out:
                        for line in stderr_out.splitlines()[:6]:
                            print(f"    {line}")
                    if "authtoken" in stderr_out.lower() or rc == 1:
                        print("\n  To add a project-local token:")
                        print("    python serve.py --add-token YOUR_TOKEN")
                    print(f"\n  Running in local-only mode.")
                else:
                    print(f"\n  WARNING: ngrok URL not retrieved automatically.")
                    print(f"  Check http://localhost:{NGROK_API_PORT} in your browser.")
                ngrok_proc = None

        if public_url:
            print(f"\n{'='*54}")
            print(f"  Local  : http://localhost:{args.port}")
            print(f"  Public : {public_url}")
            print(f"{'='*54}")
            print("  Share the Public URL with anyone on any network.")

    # ── keep running until Ctrl-C ─────────────────────────────────────────────
    print(f"\n  Local app: http://localhost:{args.port}")
    print("  Press Ctrl+C to stop.\n")
    try:
        server.wait()
    except KeyboardInterrupt:
        print("\nShutting down …")
        server.terminate()
        if ngrok_proc:
            ngrok_proc.terminate()


if __name__ == "__main__":
    main()
