"""
Tests for Indicator Engine.
"""
from core.models import Candle
from indicators.smma import calculate_fast_smma, calculate_slow_smma, calculate_smma

def _make_candles(closes: list[float]) -> list[Candle]:
    return [
        Candle(
            timestamp=i*60,
            open=c,
            high=c,
            low=c,
            close=c,
            volume=100
        )
        for i, c in enumerate(closes)
    ]

def test_smma_insufficient_data():
    candles = _make_candles([10.0, 11.0, 12.0])
    result = calculate_smma(candles, period=5)
    assert result is None

def test_fast_smma_calculation():
    # 5 periods
    candles = _make_candles([10.0, 10.0, 10.0, 10.0, 10.0])
    result = calculate_fast_smma(candles, period=5)
    # First SMMA is just the SMA
    assert result == 10.0
    
    candles = _make_candles([10.0, 10.0, 10.0, 10.0, 10.0, 20.0])
    result = calculate_fast_smma(candles, period=5)
    # Previous SMMA = 10.0. Current Close = 20.0.
    # New SMMA = (10.0 * 4 + 20.0) / 5 = 60 / 5 = 12.0
    assert result == 12.0

def test_slow_smma_calculation():
    # 10 periods for slow testing
    candles = _make_candles([10.0] * 10)
    result = calculate_slow_smma(candles, period=10)
    assert result == 10.0

    candles = _make_candles([10.0] * 10 + [20.0])
    result = calculate_slow_smma(candles, period=10)
    # New SMMA = (10.0 * 9 + 20.0) / 10 = 11.0
    assert result == 11.0
