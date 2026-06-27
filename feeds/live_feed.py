"""
feeds/live_feed.py
──────────────────
Concrete ``DataFeed`` that fetches market data from the Delta Exchange
REST API in real time.

This module owns ALL business logic related to market-data retrieval:
    • Time-window calculation for candle requests
    • Limit clamping to the API maximum (2000)
    • Raw dict → domain model transformation
    • Connectivity verification

The underlying ``DeltaRestClient`` is a pure HTTP transport — it knows
nothing about endpoints or data shapes.
"""

from __future__ import annotations

import logging
import time
from typing import Any

from core.models import Candle, Ticker
from exchange.exceptions import DeltaAPIError, DeltaConnectionError
from exchange.rest_client import DeltaRestClient
from feeds.base import DataFeed

logger = logging.getLogger(__name__)

# ── Delta API v2 paths ───────────────────────────────────────
_PATH_TICKERS      = "/v2/tickers"
_PATH_TICKER       = "/v2/tickers/{symbol}"
_PATH_CANDLES      = "/v2/history/candles"

# ── API constraints ──────────────────────────────────────────
_MAX_CANDLES_PER_REQUEST = 2000

# ── Resolution → seconds mapping (for time-window calculation) ──
_RESOLUTION_SECONDS: dict[str, int] = {
    "1m":  60,
    "3m":  180,
    "5m":  300,
    "15m": 900,
    "30m": 1800,
    "1h":  3600,
    "2h":  7200,
    "4h":  14400,
    "6h":  21600,
    "1d":  86400,
    "7d":  604800,
    "1w":  604800,
    "2w":  1209600,
    "30d": 2592000,
}


class LiveDataFeed(DataFeed):
    """Real-time data feed backed by the Delta Exchange REST API.

    Args:
        client: A ``DeltaRestClient`` instance (injected, not created here).

    Example::

        from exchange import DeltaRestClient
        from feeds.live_feed import LiveDataFeed

        client = DeltaRestClient()
        feed = LiveDataFeed(client)
        feed.connect()

        candles = feed.get_candles("BTCUSD", "1m", limit=100)
        ticker  = feed.get_ticker("ETHUSD")

        feed.close()
    """

    def __init__(self, client: DeltaRestClient) -> None:
        self._client = client
        self._connected = False

    # ──────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────

    def connect(self) -> bool:
        """Verify the Delta API is reachable by hitting the public tickers endpoint.

        Returns:
            True if the API responded successfully.

        Raises:
            DeltaConnectionError: If the server is unreachable.
            DeltaAPIError:        If the API returned an error.
        """
        logger.info("Testing connection to %s …", self._client.base_url)

        try:
            self._client.request("GET", _PATH_TICKERS)
        except (DeltaConnectionError, DeltaAPIError):
            logger.error("✗ Data feed connection failed.")
            raise

        self._connected = True
        logger.info("✓ Data feed connected → %s", self._client.base_url)
        return True

    def close(self) -> None:
        """Close the underlying HTTP client."""
        self._client.close()
        self._connected = False
        logger.info("Data feed closed.")

    # ──────────────────────────────────────────────────────
    # Market Data
    # ──────────────────────────────────────────────────────

    def get_candles(
        self,
        symbol: str,
        resolution: str,
        limit: int,
    ) -> list[Candle]:
        """Fetch OHLCV candles from ``/v2/history/candles``.

        Args:
            symbol:     Product symbol (e.g. ``"BTCUSD"``).
            resolution: Candle timeframe (e.g. ``"1m"``, ``"5m"``, ``"1h"``).
            limit:      Number of candles requested (clamped to API max of 2000).

        Returns:
            List of ``Candle`` objects, oldest first.

        Raises:
            DeltaConnectionError: Network failure.
            DeltaAPIError:        Invalid symbol or API error.
        """
        # Clamp limit to API maximum
        limit = min(max(1, limit), _MAX_CANDLES_PER_REQUEST)

        # Calculate the time window
        bar_seconds = _RESOLUTION_SECONDS.get(resolution, 60)
        end_ts = int(time.time())
        start_ts = end_ts - (limit * bar_seconds)

        params: dict[str, Any] = {
            "resolution": resolution,
            "symbol": symbol,
            "start": str(start_ts),
            "end": str(end_ts),
        }

        logger.info(
            "Fetching %d × %s candles for %s [%d → %d] …",
            limit, resolution, symbol, start_ts, end_ts,
        )

        data = self._client.request("GET", _PATH_CANDLES, params=params)
        raw_candles = data.get("result", [])

        # Transform raw dicts → Candle domain models
        candles = [Candle.from_api_dict(c) for c in raw_candles]

        logger.info("Retrieved %d candle(s) for %s.", len(candles), symbol)
        return candles

    def get_ticker(self, symbol: str) -> Ticker:
        """Fetch the latest ticker for a symbol from ``/v2/tickers/{symbol}``.

        Args:
            symbol: Product symbol (e.g. ``"BTCUSD"``).

        Returns:
            A ``Ticker`` domain model with latest market data.

        Raises:
            DeltaConnectionError: Network failure.
            DeltaAPIError:        Invalid symbol or API error.
        """
        path = _PATH_TICKER.format(symbol=symbol)

        logger.info("Fetching ticker for %s …", symbol)
        data = self._client.request("GET", path)
        raw_ticker = data.get("result", {})

        ticker = Ticker.from_api_dict(raw_ticker)
        logger.info(
            "%s → close=%s  mark=%s  vol=%s",
            ticker.symbol, ticker.close, ticker.mark_price, ticker.volume,
        )
        return ticker

    # ──────────────────────────────────────────────────────
    # Introspection
    # ──────────────────────────────────────────────────────

    @property
    def is_connected(self) -> bool:
        """Whether ``connect()`` has been called successfully."""
        return self._connected

    def __repr__(self) -> str:
        status = "connected" if self._connected else "disconnected"
        return f"LiveDataFeed({status}, url={self._client.base_url!r})"
