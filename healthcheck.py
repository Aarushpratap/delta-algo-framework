"""
healthcheck.py
──────────────
Pre-flight health check for the Delta Algo trading framework.

Run before starting the bot to verify the environment is correctly
configured. Does NOT place orders or modify any state.

Usage:
    python healthcheck.py
    python healthcheck.py --quiet   # suppress per-check lines, print summary only
"""

from __future__ import annotations

import importlib
import os
import sys
from pathlib import Path

# ── CLI flags ────────────────────────────────────────────────────────────────
QUIET = "--quiet" in sys.argv

# ── ANSI helpers ─────────────────────────────────────────────────────────────
GREEN  = "\033[92m"
RED    = "\033[91m"
YELLOW = "\033[93m"
RESET  = "\033[0m"
BOLD   = "\033[1m"

_PASS: list[str] = []
_FAIL: list[str] = []
_WARN: list[str] = []


def _pass(msg: str) -> None:
    _PASS.append(msg)
    if not QUIET:
        print(f"  {GREEN}[PASS]{RESET}  {msg}")


def _fail(msg: str) -> None:
    _FAIL.append(msg)
    if not QUIET:
        print(f"  {RED}[FAIL]{RESET}  {msg}")


def _warn(msg: str) -> None:
    _WARN.append(msg)
    if not QUIET:
        print(f"  {YELLOW}[WARN]{RESET}  {msg}")


# ── Individual checks ─────────────────────────────────────────────────────────

PROJECT_ROOT = Path(__file__).resolve().parent


def check_python() -> None:
    major, minor = sys.version_info[:2]
    if (major, minor) >= (3, 10):
        _pass(f"Python {major}.{minor} (>= 3.10)")
    else:
        _fail(f"Python {major}.{minor} — 3.10+ required")


def check_env() -> None:
    if (PROJECT_ROOT / ".env").exists():
        _pass(".env file found")
    else:
        _fail(".env not found — run: cp .env.example .env")


def check_dashboard() -> None:
    if (PROJECT_ROOT / "dashboard" / "app.py").exists():
        _pass("dashboard/app.py found")
    else:
        _fail("dashboard/app.py not found")


def check_config() -> None:
    if (PROJECT_ROOT / "config" / "settings.py").exists():
        _pass("config/settings.py found")
    else:
        _fail("config/settings.py not found")


def check_api_key() -> None:
    key = os.getenv("DELTA_API_KEY", "")
    if key and key not in ("", "your_api_key_here"):
        _pass("DELTA_API_KEY is set")
    else:
        _fail("DELTA_API_KEY missing or still the placeholder value")


def check_api_secret() -> None:
    secret = os.getenv("DELTA_API_SECRET", "")
    if secret and secret not in ("", "your_api_secret_here"):
        _pass("DELTA_API_SECRET is set")
    else:
        _fail("DELTA_API_SECRET missing or still the placeholder value")


def check_package(module: str, label: str) -> None:
    try:
        importlib.import_module(module)
        _pass(f"{label} installed")
    except ModuleNotFoundError:
        _fail(f"{label} NOT installed — run: pip install {label}")


def check_internet() -> None:
    try:
        import urllib.request
        urllib.request.urlopen("https://www.google.com", timeout=5)
        _pass("Internet connectivity reachable")
    except Exception:
        _warn("Internet connectivity check failed (may be firewall-restricted)")


def check_delta_endpoint() -> None:
    base_url = os.getenv("DELTA_BASE_URL", "https://api.india.delta.exchange")
    endpoint = f"{base_url.rstrip('/')}/v2/tickers"
    try:
        import urllib.request
        req = urllib.request.Request(
            endpoint,
            headers={"User-Agent": "delta-algo-healthcheck/1.0"}
        )
        with urllib.request.urlopen(req, timeout=8) as resp:
            if resp.status == 200:
                _pass(f"Delta REST endpoint reachable ({base_url})")
            else:
                _warn(f"Delta REST endpoint returned HTTP {resp.status}")
    except Exception as e:
        _warn(f"Delta REST endpoint check failed: {e}")


# ── Main ─────────────────────────────────────────────────────────────────────

def main() -> None:
    print()
    print(f"{BOLD}============================================================{RESET}")
    print(f"{BOLD}  Delta Algo Framework — Health Check{RESET}")
    print(f"{BOLD}  Project: {PROJECT_ROOT}{RESET}")
    print(f"{BOLD}============================================================{RESET}")

    # Load .env before checking env vars
    try:
        from dotenv import load_dotenv
        load_dotenv(PROJECT_ROOT / ".env")
    except ImportError:
        pass  # dotenv package check will surface this below

    if not QUIET:
        print(f"\n{BOLD}[ Core Environment ]{RESET}")
    check_python()
    check_env()
    check_config()
    check_dashboard()

    if not QUIET:
        print(f"\n{BOLD}[ API Credentials ]{RESET}")
    check_api_key()
    check_api_secret()

    if not QUIET:
        print(f"\n{BOLD}[ Python Packages ]{RESET}")
    check_package("dotenv",    "python-dotenv")
    check_package("requests",  "requests")
    check_package("streamlit", "streamlit")
    check_package("plotly",    "plotly")
    check_package("pandas",    "pandas")

    if not QUIET:
        print(f"\n{BOLD}[ Network ]{RESET}")
    check_internet()
    check_delta_endpoint()

    # ── Summary ───────────────────────────────────────────────────────────────
    total  = len(_PASS) + len(_FAIL) + len(_WARN)
    passed = len(_PASS)
    failed = len(_FAIL)
    warned = len(_WARN)

    print()
    print(f"{BOLD}------------------------------------------------------------{RESET}")
    if failed == 0:
        print(f"  {GREEN}{BOLD}All {total} checks PASSED"
              f"{f' ({warned} warning[s])' if warned else ''}"
              f" — Framework ready.{RESET}")
    else:
        print(f"  {RED}{BOLD}{failed}/{total} check(s) FAILED "
              f"({passed} passed, {warned} warning[s])"
              f" — Fix the issues above.{RESET}")
    print(f"{BOLD}============================================================{RESET}")
    print()

    sys.exit(0 if failed == 0 else 1)


if __name__ == "__main__":
    main()
