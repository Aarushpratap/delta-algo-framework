"""
core/enums.py
─────────────
Domain enumerations for the trading framework.

Phase 1 defines only the enums needed for market data and mode selection.
Additional enums (OrderSide, OrderType, OrderStatus, PositionSide) will
be added in later phases as the execution and strategy layers are built.
"""

from __future__ import annotations

from enum import Enum


class TradingMode(str, Enum):
    """Execution mode selector — determines which feed + executor pair is wired.

    The strategy code is identical across all three modes.  Only the data
    source and order-execution backend change.
    """

    BACKTEST = "backtest"
    PAPER    = "paper"
    LIVE     = "live"
