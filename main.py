"""
main.py
───────
Phase 1 entry point — demonstrates the market data layer.

This script bootstraps logging, creates the data feed, connects to the
Delta Exchange API, and fetches candles + tickers for all configured
symbols.  No strategy, no execution, no trading logic.

Usage:
    python main.py

Before running:
    1. Copy .env.example → .env and fill in your credentials
    2. pip install -r requirements.txt
"""

from __future__ import annotations

import json
import sys

# ── Bootstrap logging FIRST (before any other project import) ──
from config.settings import settings
from utils.logger import setup_logging

setup_logging(settings.LOG_LEVEL)

import logging

logger = logging.getLogger("main")


def main() -> None:
    """Phase 1 demo: connect to the exchange and fetch market data."""

    from exchange import DeltaRestClient, DeltaConnectionError, DeltaAPIError
    from feeds.live_feed import LiveDataFeed

    logger.info("=" * 60)
    logger.info("Delta Exchange — Phase 1: Market Data")
    logger.info("=" * 60)
    logger.info("Mode         : %s", settings.TRADING_MODE)
    logger.info("Base URL     : %s", settings.BASE_URL)
    logger.info("Symbols      : %s", ", ".join(settings.SYMBOLS))
    logger.info("Resolution   : %s", settings.CANDLE_RESOLUTION)
    logger.info("=" * 60)

    # ── Create the REST transport ───────────────────────
    client = DeltaRestClient()

    # ── Create the data feed ────────────────────────────
    feed = LiveDataFeed(client)

    # ── 1. Connect ──────────────────────────────────────
    try:
        feed.connect()
    except DeltaConnectionError as exc:
        logger.error("Connection failed: %s", exc)
        sys.exit(1)
    except DeltaAPIError as exc:
        logger.error("API error during connection: %s", exc)
        sys.exit(1)

    # ── 2. Fetch candles for each configured symbol ─────
    for symbol in settings.SYMBOLS:
        try:
            candles = feed.get_candles(
                symbol=symbol,
                resolution=settings.CANDLE_RESOLUTION,
                limit=5,
            )
            logger.info(
                "%s — %d candle(s) fetched (resolution: %s)",
                symbol, len(candles), settings.CANDLE_RESOLUTION,
            )
            for c in candles:
                logger.info(
                    "  %d | O=%.2f H=%.2f L=%.2f C=%.2f V=%.2f",
                    c.timestamp, c.open, c.high, c.low, c.close, c.volume,
                )
        except DeltaAPIError as exc:
            logger.warning("Could not fetch candles for %s: %s", symbol, exc)

    # ── 3. Fetch tickers for each configured symbol ─────
    for symbol in settings.SYMBOLS:
        try:
            ticker = feed.get_ticker(symbol)
            logger.info(
                "%s — close=%s  mark=%s  volume=%s",
                ticker.symbol, ticker.close, ticker.mark_price, ticker.volume,
            )
        except DeltaAPIError as exc:
            logger.warning("Could not fetch ticker for %s: %s", symbol, exc)

    # ── 4. Auth check (if credentials are set) ──────────
    if client.has_credentials:
        logger.info("API credentials detected — verifying authentication …")
        try:
            data = client.request(
                "GET", "/v2/wallet/balances", authenticated=True,
            )
            raw_balances = data.get("result", [])
            logger.info("✓ Authentication successful — %d wallet(s).", len(raw_balances))
        except DeltaAPIError as exc:
            logger.warning("✗ Auth verification failed: %s", exc)
    else:
        logger.info("No API credentials — skipping auth check.")

    # ── Cleanup ─────────────────────────────────────────
    feed.close()
    logger.info("Phase 1 demo complete.")


if __name__ == "__main__":
    main()
