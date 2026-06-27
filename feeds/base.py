"""
feeds/base.py
─────────────
Abstract base class for all data feeds.

Every concrete feed (live, backtest, paper-replay) implements this
interface.  The strategy engine and trader orchestrator depend ONLY on
``DataFeed`` — they never import a concrete feed class directly.  This
is what makes the same strategy code run identically in backtest, paper,
and live modes.

Phase 1 defines the market-data surface.  Account-data methods
(get_balances, get_positions) belong to the execution layer and will be
added in later phases.
"""

from __future__ import annotations

from abc import ABC, abstractmethod

from core.models import Candle, Ticker


class DataFeed(ABC):
    """Contract that every data feed must satisfy.

    Concrete implementations:
        • ``LiveDataFeed``     — fetches from the Delta Exchange REST API.
        • ``BacktestDataFeed`` — replays candles from CSV files (Phase 5).
    """

    # ──────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────

    @abstractmethod
    def connect(self) -> bool:
        """Verify that the data source is reachable.

        Returns:
            True if the feed is ready to serve data.

        Raises:
            Exception subclass on connection failure.
        """

    @abstractmethod
    def close(self) -> None:
        """Release any resources held by the feed."""

    # ──────────────────────────────────────────────────────
    # Market Data
    # ──────────────────────────────────────────────────────

    @abstractmethod
    def get_candles(
        self,
        symbol: str,
        resolution: str,
        limit: int,
    ) -> list[Candle]:
        """Fetch historical OHLCV candles.

        Args:
            symbol:     Product symbol (e.g. ``"BTCUSD"``).
            resolution: Candle timeframe (e.g. ``"1m"``, ``"5m"``, ``"1h"``).
            limit:      Maximum number of candles to return.

        Returns:
            List of ``Candle`` objects ordered chronologically (oldest first).
        """

    @abstractmethod
    def get_ticker(self, symbol: str) -> Ticker:
        """Fetch the latest ticker snapshot for a symbol.

        Args:
            symbol: Product symbol (e.g. ``"BTCUSD"``).

        Returns:
            A ``Ticker`` object with the most recent market data.
        """

    # ──────────────────────────────────────────────────────
    # Context manager
    # ──────────────────────────────────────────────────────

    def __enter__(self) -> DataFeed:
        self.connect()
        return self

    def __exit__(self, *_: object) -> None:
        self.close()
