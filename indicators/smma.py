"""
indicators/smma.py
──────────────────
Smoothed Moving Average (SMMA) indicator calculations.

This module is strictly responsible for calculating indicator values.
It contains no strategy logic, order placement, or external side effects.

Formulas:
    Initial SMMA: SMA of the first N periods.
    Subsequent SMMA: (Previous SMMA * (N - 1) + Current Close) / N
"""

from __future__ import annotations

from core.models import Candle


def calculate_smma(
    historical_candles: list[Candle],
    live_candles: list[Candle] | None = None,
    period: int = 5,
) -> float | None:
    """
    Calculate the Smoothed Moving Average (SMMA) for the given period.

    Args:
        historical_candles: A list of confirmed historical Candle objects.
        live_candles:       An optional list of real-time/unconfirmed Candle objects.
        period:             The lookback period for the SMMA calculation.

    Returns:
        The latest SMMA value as a float, or None if there is insufficient data.
    """
    if not historical_candles and not live_candles:
        return None

    all_candles = historical_candles.copy()
    if live_candles:
        all_candles.extend(live_candles)

    if len(all_candles) < period:
        return None

    # Extract closing prices
    closes = [candle.close for candle in all_candles]

    # Calculate initial SMMA (which is a simple moving average)
    smma = sum(closes[:period]) / period

    # Calculate SMMA for the remaining periods
    for close_price in closes[period:]:
        smma = (smma * (period - 1) + close_price) / period

    return smma


def calculate_fast_smma(
    historical_candles: list[Candle],
    live_candles: list[Candle] | None = None,
    period: int = 5,
) -> float | None:
    """
    Calculate the Fast SMMA (defaults to 5 periods).

    Args:
        historical_candles: A list of confirmed historical Candle objects.
        live_candles:       An optional list of real-time/unconfirmed Candle objects.
        period:             The lookback period (defaults to 5).

    Returns:
        The latest Fast SMMA value as a float, or None if insufficient data.
    """
    return calculate_smma(historical_candles, live_candles, period)


def calculate_slow_smma(
    historical_candles: list[Candle],
    live_candles: list[Candle] | None = None,
    period: int = 100,
) -> float | None:
    """
    Calculate the Slow SMMA (defaults to 100 periods).

    Args:
        historical_candles: A list of confirmed historical Candle objects.
        live_candles:       An optional list of real-time/unconfirmed Candle objects.
        period:             The lookback period (defaults to 100).

    Returns:
        The latest Slow SMMA value as a float, or None if insufficient data.
    """
    return calculate_smma(historical_candles, live_candles, period)


def get_smma_values(
    historical_candles: list[Candle],
    live_candles: list[Candle] | None = None,
    fast_period: int = 5,
    slow_period: int = 100,
) -> dict[str, float | None]:
    """
    Calculate and return both Fast and Slow SMMA values as a dictionary.

    Args:
        historical_candles: A list of confirmed historical Candle objects.
        live_candles:       An optional list of real-time/unconfirmed Candle objects.
        fast_period:        The lookback period for the Fast SMMA (default 5).
        slow_period:        The lookback period for the Slow SMMA (default 100).

    Returns:
        A dictionary containing the calculated indicator values.
        Example:
            {
                "fast_smma": 50000.5,
                "slow_smma": 48000.0
            }
    """
    return {
        "fast_smma": calculate_fast_smma(historical_candles, live_candles, fast_period),
        "slow_smma": calculate_slow_smma(historical_candles, live_candles, slow_period),
    }
