"""
End-to-End Integration Tests.
Verifies the complete pipeline: Historical CSV -> Engine -> Indicator -> Strategy -> Risk -> Stats -> Report.
"""
import pytest
from pathlib import Path

from strategy.smma_cross import SMMACrossStrategy
from backtest.engine import BacktestEngine
from backtest.report import generate_report

def create_mock_csv(filepath: Path):
    """
    Creates a deterministic dataset.
    Strategy: Fast=2, Slow=5.
    """
    csv_content = "timestamp,open,high,low,close,volume\n"
    # T=0 to T=4: Flat market to initialize SMMAs at 100
    for i in range(5):
        csv_content += f"{i*60},100,100,100,100,10\n"
    
    # T=5: Drop to 50. Fast < Slow
    csv_content += f"300,100,100,50,50,10\n"
    
    # T=6: Spike to 150. Fast crosses ABOVE Slow. BUY signal on close! Low=50.
    csv_content += f"360,50,150,50,150,10\n"
    
    # T=7: Trade Entered on OPEN at 150. SL=50 (from signal candle Low). Risk=100. RR=2 -> Target distance=200 -> TP=350.
    # New signal might try to generate, but we ignore it while trade is open.
    csv_content += f"420,150,200,140,150,10\n"
    
    # T=8: Gap down below SL! Open=20. SL=50.
    # Exit triggered. Exit price should be min(SL, Open) = 20. (Loss)
    csv_content += f"480,20,150,20,20,10\n"
    
    # T=9, T=10, T=11, T=12, T=13: Reset SMMA to 20
    for i in range(9, 14):
        csv_content += f"{i*60},20,20,20,20,10\n"
        
    # T=14: Spike to 400. Fast crosses ABOVE Slow. BUY signal on close! Low=20.
    csv_content += f"840,20,400,20,400,10\n"
    
    # T=15: Trade Entered on OPEN at 400. SL=20. Risk=380. TP = 400 + 760 = 1160.
    csv_content += f"900,400,1000,390,900,10\n"
    
    # T=16: TP hit during the candle. High=1200. Exit at 1160. (Win)
    csv_content += f"960,900,1200,800,1200,10\n"
    
    with open(filepath, "w", encoding="utf-8") as f:
        f.write(csv_content)

def test_full_pipeline(tmp_path):
    csv_file = tmp_path / "mock_data.csv"
    create_mock_csv(csv_file)
    
    strategy = SMMACrossStrategy(fast_period=2, slow_period=5)
    # Fee rate of 10% to easily verify fee deduction
    engine = BacktestEngine(
        strategy=strategy,
        max_sl_distance=500.0,
        rr_ratio=2.0,
        fee_rate=0.10,
        stoploss_mode="absolute"
    )
    
    # 1. Verify Historical Candles loaded correctly
    engine.load_csv(str(csv_file))
    assert len(engine.candles) == 17
    
    trades = engine.run()
    
    # We should have exactly 4 trades due to the alternating crossovers.
    assert len(trades) == 4
    
    t1, t2, t3, t4 = trades
    
    # Trade 1: SELL generated at T=5 (Bearish cross), entered at T=6, SL hit immediately.
    assert t1.side == "SELL"
    assert t1.entry_price == 50.0
    assert t1.stop_loss == 100.0
    assert t1.result == "LOSS"
    assert t1.exit_price == 100.0
    # Fee = (50 * 0.1) + (100 * 0.1) = 15. Gross PNL = 50 - 100 = -50. Net = -65.
    assert t1.profit_loss == -65.0
    
    # Trade 2: BUY generated at T=6 (Bullish cross), entered at T=7, gap SL hit at T=8.
    assert t2.side == "BUY"
    assert t2.entry_price == 150.0
    assert t2.stop_loss == 50.0
    assert t2.take_profit == 350.0
    assert t2.result == "LOSS"
    assert t2.exit_price == 20.0  # Gap slippage simulation worked!
    # Fee = (150 * 0.1) + (20 * 0.1) = 17. Gross PNL = 20 - 150 = -130. Net = -147.
    assert t2.profit_loss == -147.0
    
    # Trade 3: SELL generated at T=8 (Bearish cross), entered at T=9, SL hit at T=14.
    assert t3.side == "SELL"
    assert t3.entry_price == 20.0
    assert t3.stop_loss == 150.0
    assert t3.result == "LOSS"
    assert t3.exit_price == 150.0
    # Fee = (20 * 0.1) + (150 * 0.1) = 17. Gross PNL = 20 - 150 = -130. Net = -147.
    assert t3.profit_loss == -147.0
    
    # Trade 4: BUY generated at T=14 (Bullish cross), entered at T=15, TP hit at T=16.
    assert t4.side == "BUY"
    assert t4.entry_price == 400.0
    assert t4.stop_loss == 20.0
    assert t4.take_profit == 1160.0
    assert t4.result == "WIN"
    assert t4.exit_price == 1160.0
    # Fee = (400 * 0.1) + (1160 * 0.1) = 156. Gross PNL = 1160 - 400 = 760. Net = 604.
    assert t4.profit_loss == 604.0
    
    # Generate statistics
    stats = generate_report(trades)
    assert stats.total_trades == 4
    assert stats.winning_trades == 1
    assert stats.losing_trades == 3
    assert stats.win_rate == 25.0
    
    expected_net = -65.0 - 147.0 - 147.0 + 604.0
    assert stats.net_profit == expected_net
    assert stats.gross_profit == 604.0
    assert stats.gross_loss == (65.0 + 147.0 + 147.0)
