"""
core/models.py
──────────────
Immutable domain models for the trading framework.

Every model is a frozen dataclass with a ``from_api_dict()`` classmethod
that translates raw Delta Exchange API dicts into typed objects.  Higher
layers (feeds, execution) use these models — they never pass raw dicts
across boundaries.

Phase 1 defines the four read-only models that map to current API
endpoints.  Order and Trade models will be added in later phases when
the execution layer is built.
"""

from __future__ import annotations

import time
from dataclasses import dataclass
from typing import Any


# ─────────────────────────────────────────────────────────────
# Market Data Models
# ─────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class Candle:
    """Single OHLCV candle bar.

    Attributes:
        timestamp: Unix epoch seconds for the candle open.
        open:      Opening price.
        high:      Highest price during the period.
        low:       Lowest price during the period.
        close:     Closing price.
        volume:    Traded volume during the period.
    """

    timestamp: int
    open: float
    high: float
    low: float
    close: float
    volume: float

    @classmethod
    def from_api_dict(cls, raw: dict[str, Any]) -> Candle:
        """Parse a single candle from the Delta ``/v2/history/candles`` response.

        The API returns candles as dicts with keys:
        ``time``, ``open``, ``high``, ``low``, ``close``, ``volume``.
        """
        return cls(
            timestamp=int(raw.get("time", 0)),
            open=float(raw.get("open", 0.0)),
            high=float(raw.get("high", 0.0)),
            low=float(raw.get("low", 0.0)),
            close=float(raw.get("close", 0.0)),
            volume=float(raw.get("volume", 0.0)),
        )

    @classmethod
    def from_csv_row(cls, row: dict[str, str]) -> Candle:
        """Parse a candle from a CSV DictReader row.

        Expected CSV columns: timestamp, open, high, low, close, volume.
        Used by BacktestDataFeed (Phase 5).
        """
        return cls(
            timestamp=int(row["timestamp"]),
            open=float(row["open"]),
            high=float(row["high"]),
            low=float(row["low"]),
            close=float(row["close"]),
            volume=float(row["volume"]),
        )


@dataclass(frozen=True, slots=True)
class Ticker:
    """Latest market ticker snapshot for a symbol.

    Attributes:
        symbol:     Product symbol (e.g. "BTCUSD").
        mark_price: Current mark price (for margining).
        last_price: Last traded price.
        close:      24h close / settlement price.
        volume:     24h traded volume.
        timestamp:  Unix epoch seconds when the ticker was captured.
    """

    symbol: str
    mark_price: float | None
    last_price: float | None
    close: float | None
    volume: float | None
    timestamp: int

    @classmethod
    def from_api_dict(cls, raw: dict[str, Any]) -> Ticker:
        """Parse a ticker from the Delta ``/v2/tickers/{symbol}`` response."""
        return cls(
            symbol=str(raw.get("symbol", "")),
            mark_price=_safe_float(raw.get("mark_price")),
            last_price=_safe_float(raw.get("last_price")),
            close=_safe_float(raw.get("close")),
            volume=_safe_float(raw.get("volume")),
            timestamp=int(raw.get("timestamp", int(time.time()))),
        )


# ─────────────────────────────────────────────────────────────
# Account Data Models
# ─────────────────────────────────────────────────────────────

@dataclass(frozen=True, slots=True)
class Balance:
    """Wallet balance for a single asset.

    Attributes:
        asset_id:          Numeric asset identifier.
        asset_symbol:      Human-readable symbol (e.g. "USDT", "BTC").
        available_balance: Balance available for new orders.
        total_balance:     Total wallet balance (including margin).
        position_margin:   Margin locked in open positions.
        order_margin:      Margin locked in pending orders.
        commission:        Accumulated commissions.
    """

    asset_id: int
    asset_symbol: str
    available_balance: float
    total_balance: float
    position_margin: float
    order_margin: float
    commission: float

    @classmethod
    def from_api_dict(cls, raw: dict[str, Any]) -> Balance:
        """Parse a balance from the Delta ``/v2/wallet/balances`` response."""
        return cls(
            asset_id=int(raw.get("asset_id", 0)),
            asset_symbol=str(raw.get("asset_symbol", "")),
            available_balance=_safe_float(raw.get("available_balance")) or 0.0,
            total_balance=_safe_float(raw.get("balance")) or 0.0,
            position_margin=_safe_float(raw.get("position_margin")) or 0.0,
            order_margin=_safe_float(raw.get("order_margin")) or 0.0,
            commission=_safe_float(raw.get("commission")) or 0.0,
        )


@dataclass(frozen=True, slots=True)
class Position:
    """Open margined position on a single product.

    Attributes:
        product_id:      Numeric product identifier.
        symbol:          Product symbol (e.g. "BTCUSD").
        size:            Position size (positive = long, negative = short, 0 = flat).
        entry_price:     Average entry price.
        margin:          Margin assigned to this position.
        liquidation_price: Estimated liquidation price.
        unrealised_pnl:  Unrealised profit/loss.
        realised_pnl:    Realised profit/loss.
    """

    product_id: int
    symbol: str
    size: float
    entry_price: float
    margin: float
    liquidation_price: float | None
    unrealised_pnl: float
    realised_pnl: float

    @classmethod
    def from_api_dict(cls, raw: dict[str, Any]) -> Position:
        """Parse a position from the Delta ``/v2/positions/margined`` response."""
        return cls(
            product_id=int(raw.get("product_id", 0)),
            symbol=str(raw.get("product", {}).get("symbol", raw.get("product_symbol", ""))),
            size=_safe_float(raw.get("size")) or 0.0,
            entry_price=_safe_float(raw.get("entry_price")) or 0.0,
            margin=_safe_float(raw.get("margin")) or 0.0,
            liquidation_price=_safe_float(raw.get("liquidation_price")),
            unrealised_pnl=_safe_float(raw.get("unrealised_pnl")) or 0.0,
            realised_pnl=_safe_float(raw.get("realised_pnl")) or 0.0,
        )


# ─────────────────────────────────────────────────────────────
# Internal helpers
# ─────────────────────────────────────────────────────────────

def _safe_float(value: Any) -> float | None:
    """Convert a value to float, returning None for missing / unparseable data.

    The Delta API sometimes returns numeric fields as strings (e.g. "123.45")
    and sometimes as null.  This helper handles both.
    """
    if value is None or value == "":
        return None
    try:
        return float(value)
    except (ValueError, TypeError):
        return None
