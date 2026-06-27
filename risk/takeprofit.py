"""
risk/takeprofit.py
──────────────────
Take Profit calculation logic.

Determines the take profit target based on the calculated risk
and the configured Risk:Reward ratio.
"""

from __future__ import annotations

from strategy.base import SignalSide


def calculate_takeprofit(
    side: SignalSide,
    entry_price: float,
    stoploss_price: float,
    risk_reward_ratio: float,
) -> float:
    """
    Calculate the take profit target based on Risk:Reward ratio.

    Formula:
        Risk = abs(Entry - StopLoss)
        Target Distance = Risk * Risk:Reward Ratio
        BUY  -> Entry + Target Distance
        SELL -> Entry - Target Distance

    Args:
        side:              The trade direction ("BUY" or "SELL").
        entry_price:       The intended entry price for the trade.
        stoploss_price:    The calculated stop loss price.
        risk_reward_ratio: The Risk:Reward multiplier (e.g., 5.0 for 1:5).

    Returns:
        The calculated take profit price target.

    Raises:
        ValueError: If an invalid side is provided.
    """
    risk = abs(entry_price - stoploss_price)
    target_distance = risk * risk_reward_ratio

    if side == "BUY":
        return entry_price + target_distance
    elif side == "SELL":
        return entry_price - target_distance
    else:
        raise ValueError(f"Invalid trade side: {side}")
