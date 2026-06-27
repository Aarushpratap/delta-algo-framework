"""
risk/stoploss.py
────────────────
Stop Loss calculation and risk validation logic.

This module determines the stop loss level based on the signal candle
and validates whether the risk exceeds the configured maximum threshold.
"""

from __future__ import annotations

from core.models import Candle
from strategy.base import SignalSide


class TradeRejected(Exception):
    """Raised when a trade fails risk validation."""
    
    def __init__(self, reason: str) -> None:
        self.reason = reason
        super().__init__(f"Trade Rejected: {reason}")


def calculate_stoploss(
    side: SignalSide,
    entry_price: float,
    signal_candle: Candle,
    max_distance: float,
    mode: str = "absolute",
) -> float:
    """
    Calculate the initial stop loss level and validate against maximum distance.

    Rules:
        BUY  -> Stop Loss = Low of the signal candle.
        SELL -> Stop Loss = High of the signal candle.

    Args:
        side:          The trade direction ("BUY" or "SELL").
        entry_price:   The intended entry price for the trade.
        signal_candle: The confirmed candle that generated the signal.
        max_distance:  The maximum allowed distance for the stop loss.
        mode:          The stop loss mode ("absolute", "percentage", "atr").

    Returns:
        The calculated stop loss price.

    Raises:
        TradeRejected: If the stop loss distance is strictly greater than max_distance,
                       or if the risk is exactly zero.
        ValueError:    If an invalid side is provided.
        NotImplementedError: If mode is not "absolute".
    """
    if mode != "absolute":
        raise NotImplementedError(f"Stop loss mode '{mode}' is not yet implemented.")

    if side == "BUY":
        stop_loss = signal_candle.low
        distance = entry_price - stop_loss
    elif side == "SELL":
        stop_loss = signal_candle.high
        distance = stop_loss - entry_price
    else:
        raise ValueError(f"Invalid trade side: {side}")

    # Validate risk
    # Ensure distance is positive (in case of weird gaps where entry is better than SL)
    distance = max(0.0, distance)
    
    if distance == 0.0:
        raise TradeRejected("ZERO_RISK_TRADE")
    
    if distance > max_distance:
        raise TradeRejected("STOPLOSS_TOO_LARGE")

    return stop_loss
