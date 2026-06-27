"""
Tests for Risk Engine.
"""
import pytest
from core.models import Candle
from risk.stoploss import calculate_stoploss, TradeRejected
from risk.takeprofit import calculate_takeprofit

def test_buy_stoploss():
    signal_candle = Candle(
        timestamp=0,
        open=100.0,
        high=105.0,
        low=95.0,
        close=102.0,
        volume=100
    )
    sl = calculate_stoploss(side="BUY", entry_price=102.0, signal_candle=signal_candle, max_distance=10.0, mode="absolute")
    assert sl == 95.0

def test_sell_stoploss():
    signal_candle = Candle(
        timestamp=0,
        open=100.0,
        high=105.0,
        low=95.0,
        close=98.0,
        volume=100
    )
    sl = calculate_stoploss(side="SELL", entry_price=98.0, signal_candle=signal_candle, max_distance=10.0, mode="absolute")
    assert sl == 105.0

def test_max_stoploss_rejection():
    signal_candle = Candle(
        timestamp=0,
        open=100.0,
        high=110.0,
        low=90.0,
        close=102.0,
        volume=100
    )
    with pytest.raises(TradeRejected) as excinfo:
        calculate_stoploss(side="BUY", entry_price=102.0, signal_candle=signal_candle, max_distance=5.0, mode="absolute")
    assert excinfo.value.reason == "STOPLOSS_TOO_LARGE"

def test_zero_risk_rejection():
    signal_candle = Candle(
        timestamp=0,
        open=100.0,
        high=105.0,
        low=102.0,
        close=102.0,
        volume=100
    )
    # Entry at exactly the low
    with pytest.raises(TradeRejected) as excinfo:
        calculate_stoploss(side="BUY", entry_price=102.0, signal_candle=signal_candle, max_distance=10.0, mode="absolute")
    assert excinfo.value.reason == "ZERO_RISK_TRADE"

def test_take_profit_calculation():
    # Buy: Entry 100, SL 95 -> Risk 5. RR = 3. Target distance = 15. TP = 115
    tp_buy = calculate_takeprofit(side="BUY", entry_price=100.0, stoploss_price=95.0, risk_reward_ratio=3.0)
    assert tp_buy == 115.0

    # Sell: Entry 100, SL 105 -> Risk 5. RR = 3. Target distance = 15. TP = 85
    tp_sell = calculate_takeprofit(side="SELL", entry_price=100.0, stoploss_price=105.0, risk_reward_ratio=3.0)
    assert tp_sell == 85.0
