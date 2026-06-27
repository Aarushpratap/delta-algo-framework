"""
config/settings.py
──────────────────
Centralised, configuration-driven settings for the trading framework.

All tuneable parameters are read from environment variables (loaded from
``.env`` via python-dotenv).  Nothing is hardcoded — timeframe, symbols,
trading mode, and all future parameters (leverage, stop-loss cap,
indicator lengths) are injected via config.

Usage:
    from config.settings import settings
    print(settings.CANDLE_RESOLUTION)
"""

from __future__ import annotations

import os
import sys
from dataclasses import dataclass, field
from pathlib import Path

from dotenv import load_dotenv


# ── Load .env from the project root ─────────────────────────
_PROJECT_ROOT = Path(__file__).resolve().parent.parent
_ENV_PATH = _PROJECT_ROOT / ".env"

if _ENV_PATH.exists():
    load_dotenv(dotenv_path=_ENV_PATH)
else:
    print(
        f"[WARNING] .env file not found at {_ENV_PATH}. "
        "Copy .env.example → .env and fill in your credentials.",
        file=sys.stderr,
    )


@dataclass(frozen=True, slots=True)
class Settings:
    """Immutable container for runtime configuration.

    Every field maps 1-to-1 with an environment variable.
    Defaults are safe for development / public-endpoint usage.
    """

    # ── API credentials ──────────────────────────────────
    API_KEY: str
    API_SECRET: str
    BASE_URL: str

    # ── Trading mode ─────────────────────────────────────
    # "backtest", "paper", or "live"
    TRADING_MODE: str = "paper"

    # ── Market data ──────────────────────────────────────
    # Candle resolution passed to the data feed (1m, 3m, 5m, 15m, 1h, etc.)
    CANDLE_RESOLUTION: str = "1m"

    # Comma-separated list of symbols to track
    SYMBOLS: tuple[str, ...] = ("BTCUSD",)

    # ── REST transport ───────────────────────────────────
    REST_TIMEOUT: tuple[int, int] = (5, 30)   # (connect, read) seconds
    USER_AGENT: str = "delta-algo-client/1.0"

    # ── Logging ──────────────────────────────────────────
    LOG_LEVEL: str = "INFO"

    # ── Risk Engine ──────────────────────────────────────
    # Stop loss mode (absolute, percentage, atr)
    STOPLOSS_MODE: str = "absolute"
    MAX_STOPLOSS_DISTANCE: float = 0.50
    RISK_REWARD_RATIO: float = 5.0

    # ── Backtest Engine ──────────────────────────────────
    TRADING_FEE_RATE: float = 0.0
    BACKTEST_DATA_DIR: str = ""

    # ── WebSocket (placeholder) ──────────────────────────
    WS_URL: str = ""


def _parse_symbols(raw: str) -> tuple[str, ...]:
    """Split a comma-separated symbol string into a tuple.

    Handles whitespace and empty strings gracefully.
    """
    if not raw:
        return ("BTCUSD",)
    return tuple(s.strip().upper() for s in raw.split(",") if s.strip())


def _load_settings() -> Settings:
    """Build a Settings instance from environment variables."""
    api_key = os.getenv("DELTA_API_KEY", "")
    api_secret = os.getenv("DELTA_API_SECRET", "")
    base_url = os.getenv("DELTA_BASE_URL", "https://api.india.delta.exchange")

    if not api_key or not api_secret:
        print(
            "[WARNING] DELTA_API_KEY / DELTA_API_SECRET not set. "
            "Authenticated endpoints will fail.",
            file=sys.stderr,
        )

    # Resolve backtest data directory relative to project root
    backtest_dir_raw = os.getenv("BACKTEST_DATA_DIR", "")
    if backtest_dir_raw:
        backtest_dir = str((_PROJECT_ROOT / backtest_dir_raw).resolve())
    else:
        backtest_dir = str(_PROJECT_ROOT / "data")

    return Settings(
        API_KEY=api_key,
        API_SECRET=api_secret,
        BASE_URL=base_url.rstrip("/"),
        TRADING_MODE=os.getenv("TRADING_MODE", "paper").lower(),
        CANDLE_RESOLUTION=os.getenv("CANDLE_RESOLUTION", "1m"),
        SYMBOLS=_parse_symbols(os.getenv("SYMBOLS", "BTCUSD")),
        LOG_LEVEL=os.getenv("LOG_LEVEL", "INFO").upper(),
        STOPLOSS_MODE=os.getenv("STOPLOSS_MODE", "absolute").lower(),
        MAX_STOPLOSS_DISTANCE=float(os.getenv("MAX_STOPLOSS_DISTANCE", "0.50")),
        RISK_REWARD_RATIO=float(os.getenv("RISK_REWARD_RATIO", "5.0")),
        TRADING_FEE_RATE=float(os.getenv("TRADING_FEE_RATE", "0.0")),
        BACKTEST_DATA_DIR=backtest_dir,
    )


# Singleton — import this everywhere
settings = _load_settings()
