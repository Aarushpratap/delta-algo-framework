"""
Tests for Strategy Engine.
"""
from core.models import Candle
from strategy.smma_cross import SMMACrossStrategy

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

def test_no_signal():
    strategy = SMMACrossStrategy(fast_period=2, slow_period=5)
    # Steady uptrend, fast always above slow
    candles = _make_candles([10, 11, 12, 13, 14, 15, 16])
    signal = strategy.generate_signal(candles)
    assert signal is None

def test_buy_crossover():
    strategy = SMMACrossStrategy(fast_period=2, slow_period=5)
    # Slow is higher than fast initially, then fast crosses above.
    # Fast = 2, Slow = 5
    # To construct this easily without manual calc, we can just feed raw data
    # Let's say flat at 10.0 for 5 candles.
    closes = [10.0, 10.0, 10.0, 10.0, 10.0]
    # Fast is 10.0, Slow is 10.0
    
    # Next candle drops to 5.0 (Fast drops fast, Slow drops slow)
    closes.append(5.0)
    # Fast < Slow
    
    # Next candle spikes to 30.0 (Fast rises fast, Slow rises slow)
    closes.append(30.0)
    
    candles = _make_candles(closes)
    
    signal = strategy.generate_signal(candles)
    assert signal is not None
    assert signal.side == "BUY"
    assert signal.price == 30.0
    assert signal.reason == "SMMA Bullish Crossover"

def test_sell_crossover():
    strategy = SMMACrossStrategy(fast_period=2, slow_period=5)
    # Let's say flat at 10.0 for 5 candles.
    closes = [10.0, 10.0, 10.0, 10.0, 10.0]
    
    # Spike to 30 (Fast > Slow)
    closes.append(30.0)
    
    # Drop to 5 (Fast < Slow)
    closes.append(5.0)
    closes.append(5.0)
    
    candles = _make_candles(closes)
    
    signal = strategy.generate_signal(candles)
    assert signal is not None
    assert signal.side == "SELL"
    assert signal.price == 5.0
    assert signal.reason == "SMMA Bearish Crossover"

def test_insufficient_candles_strategy():
    strategy = SMMACrossStrategy(fast_period=2, slow_period=5)
    candles = _make_candles([10.0, 10.0])
    signal = strategy.generate_signal(candles)
    assert signal is None
