"""
strategy/smma_cross.py
──────────────────────
Signal Engine for the SMMA Crossover Strategy.

This module is responsible ONLY for detecting trading signals based on
the smoothed moving averages. It evaluates historical candles and generates
a Signal object if a valid crossover has occurred.

It contains no execution logic, no API calls, no risk management, and
does not place orders.
"""

from __future__ import annotations

from core.models import Candle
from indicators.smma import calculate_fast_smma, calculate_slow_smma
from strategy.base import BaseStrategy, Signal


class SMMACrossStrategy(BaseStrategy):
    """
    SMMA Crossover Strategy implementation.
    """
    
    def __init__(self, fast_period: int = 5, slow_period: int = 100) -> None:
        self.fast_period = fast_period
        self.slow_period = slow_period

    def generate_signal(self, historical_candles: list[Candle]) -> Signal | None:
        """
        Evaluate the historical candles for a SMMA crossover.

        The signal is valid only after a candle has completely CLOSED.
        Therefore, this function relies entirely on the confirmed historical candles
        and checks the state between the two most recently closed candles.

        Args:
            historical_candles: List of confirmed/closed Candle objects.

        Returns:
            A Signal object if a crossover occurred on the latest closed candle,
            otherwise None.
        """
        # Need at least (slow_period + 1) candles to calculate prev & current values reliably.
        if not historical_candles or len(historical_candles) <= self.slow_period:
            return None

        # The most recently closed candle
        current_closed_candle = historical_candles[-1]

        # Indicator values up to the previous closed candle
        prev_fast = calculate_fast_smma(historical_candles[:-1], period=self.fast_period)
        prev_slow = calculate_slow_smma(historical_candles[:-1], period=self.slow_period)

        # Indicator values up to the current closed candle
        curr_fast = calculate_fast_smma(historical_candles, period=self.fast_period)
        curr_slow = calculate_slow_smma(historical_candles, period=self.slow_period)

        if None in (prev_fast, prev_slow, curr_fast, curr_slow):
            return None
            
        # For typing, tell mypy they are floats
        assert prev_fast is not None
        assert prev_slow is not None
        assert curr_fast is not None
        assert curr_slow is not None

        # BUY Signal: Fast SMMA crosses ABOVE Slow SMMA
        if prev_fast <= prev_slow and curr_fast > curr_slow:
            return Signal(
                side="BUY",
                timestamp=current_closed_candle.timestamp,
                price=current_closed_candle.close,
                reason="SMMA Bullish Crossover",
            )

        # SELL Signal: Fast SMMA crosses BELOW Slow SMMA
        if prev_fast >= prev_slow and curr_fast < curr_slow:
            return Signal(
                side="SELL",
                timestamp=current_closed_candle.timestamp,
                price=current_closed_candle.close,
                reason="SMMA Bearish Crossover",
            )

        return None
