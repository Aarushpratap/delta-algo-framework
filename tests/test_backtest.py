"""
Tests for Backtesting Engine.
"""
from core.models import Candle
from strategy.base import BaseStrategy, Signal
from backtest.engine import BacktestEngine
from backtest.report import generate_report

class MockStrategy(BaseStrategy):
    def __init__(self, signals_to_emit: dict[int, Signal]):
        self.signals_to_emit = signals_to_emit

    def generate_signal(self, historical_candles: list[Candle]) -> Signal | None:
        idx = len(historical_candles) - 1
        return self.signals_to_emit.get(idx)

def _make_candle(idx: int, o: float, h: float, l: float, c: float) -> Candle:
    return Candle(
        timestamp=idx*60,
        open=o,
        high=h,
        low=l,
        close=c,
        volume=100
    )

def test_backtest_execution():
    # Signal emitted on candle 0 (closed).
    # Expected entry on candle 1 OPEN.
    signals = {
        0: Signal(side="BUY", timestamp=0, price=100.0, reason="Test")
    }
    
    candles = [
        # Candle 0 (Signal generated here: Low=90)
        _make_candle(0, 100.0, 105.0, 90.0, 100.0),
        # Candle 1 (Entry at OPEN=100. SL=90, TP=100+(10*2)=120)
        # Price goes 95 -> 110, neither hit
        _make_candle(1, 100.0, 110.0, 95.0, 105.0),
        # Candle 2 (Price goes to 125, hits TP=120)
        _make_candle(2, 105.0, 125.0, 100.0, 120.0),
    ]
    
    strategy = MockStrategy(signals)
    engine = BacktestEngine(
        strategy=strategy,
        max_sl_distance=20.0,
        rr_ratio=2.0,
        fee_rate=0.0,
        stoploss_mode="absolute"
    )
    engine.candles = candles
    trades = engine.run()
    
    assert len(trades) == 1
    trade = trades[0]
    assert trade.side == "BUY"
    assert trade.entry_price == 100.0
    assert trade.stop_loss == 90.0
    assert trade.take_profit == 120.0
    assert trade.result == "WIN"
    assert trade.profit_loss == 20.0
    
    # Test statistics
    stats = generate_report(trades)
    assert stats.total_trades == 1
    assert stats.win_rate == 100.0
    assert stats.net_profit == 20.0

def test_gap_stoploss_slippage():
    signals = {
        0: Signal(side="BUY", timestamp=0, price=100.0, reason="Test")
    }
    
    candles = [
        # Candle 0 (Signal: SL=95)
        _make_candle(0, 100.0, 100.0, 95.0, 100.0),
        # Candle 1 (Entry at OPEN=100. SL=95)
        _make_candle(1, 100.0, 100.0, 98.0, 100.0),
        # Candle 2 (Gap down open! OPEN=90, which is below SL=95)
        _make_candle(2, 90.0, 92.0, 80.0, 90.0),
    ]
    
    strategy = MockStrategy(signals)
    engine = BacktestEngine(
        strategy=strategy,
        max_sl_distance=20.0,
        rr_ratio=2.0,
        fee_rate=0.0
    )
    engine.candles = candles
    trades = engine.run()
    
    assert len(trades) == 1
    trade = trades[0]
    assert trade.result == "LOSS"
    # Due to gap, exit should be at OPEN (90.0), NOT SL (95.0)
    assert trade.exit_price == 90.0
    assert trade.profit_loss == -10.0

def test_fee_deduction():
    signals = {
        0: Signal(side="BUY", timestamp=0, price=100.0, reason="Test")
    }
    
    candles = [
        # Candle 0 (Signal: SL=90)
        _make_candle(0, 100.0, 100.0, 90.0, 100.0),
        # Candle 1 (Entry at 100, hits TP at 120)
        _make_candle(1, 100.0, 125.0, 95.0, 120.0),
    ]
    
    strategy = MockStrategy(signals)
    # 10% fee to make it obvious
    engine = BacktestEngine(
        strategy=strategy,
        max_sl_distance=20.0,
        rr_ratio=2.0,
        fee_rate=0.10
    )
    engine.candles = candles
    trades = engine.run()
    
    trade = trades[0]
    # Gross PNL = +20.0
    # Entry fee = 100 * 0.10 = 10.0
    # Exit fee = 120 * 0.10 = 12.0
    # Net PNL = 20.0 - 22.0 = -2.0
    assert trade.profit_loss == -2.0
