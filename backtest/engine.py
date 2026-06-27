"""
backtest/engine.py
──────────────────
Loop-based backtesting engine.

Sequentially processes historical candles through the indicator, signal,
and risk engines to simulate trades. Only one trade can be open at a time.
"""

from __future__ import annotations

import csv
import logging
from typing import Any

from core.models import Candle
from risk.stoploss import calculate_stoploss, TradeRejected
from risk.takeprofit import calculate_takeprofit
from strategy.base import BaseStrategy
from backtest.report import TradeRecord

logger = logging.getLogger(__name__)


class BacktestEngine:
    """
    Simulates historical trading based on static CSV data.
    
    Flow:
        Candle Close -> Check Signal -> Next Candle Open -> Validate Risk -> Enter
        During Trade -> Check Stop Loss -> Check Take Profit -> Exit
    """

    def __init__(
        self, 
        strategy: BaseStrategy,
        max_sl_distance: float, 
        rr_ratio: float,
        fee_rate: float = 0.0,
        stoploss_mode: str = "absolute"
    ) -> None:
        self.strategy = strategy
        self.max_sl_distance = max_sl_distance
        self.rr_ratio = rr_ratio
        self.fee_rate = fee_rate
        self.stoploss_mode = stoploss_mode
        
        self.candles: list[Candle] = []
        self.trades: list[TradeRecord] = []
        
        self.open_trade: dict[str, Any] | None = None
        self.pending_signal = None
        self.pending_signal_candle: Candle | None = None

    def load_csv(self, filepath: str) -> None:
        """
        Load historical candles from a CSV file.
        Format must be: timestamp, open, high, low, close, volume
        """
        logger.info("Loading backtest data from %s", filepath)
        with open(filepath, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.candles.append(Candle.from_csv_row(row))
        
        # Ensure chronological order
        self.candles.sort(key=lambda c: c.timestamp)
        logger.info("Loaded %d candles.", len(self.candles))

    def run(self) -> list[TradeRecord]:
        """
        Execute the backtest simulation over the loaded candles.

        Returns:
            A list of completed TradeRecord objects.
        """
        logger.info("Starting backtest simulation...")
        
        self.trades = []
        self.open_trade = None
        self.pending_signal = None
        
        for i in range(len(self.candles)):
            candle = self.candles[i]
            
            # 1. If we have a pending signal, attempt to enter at this candle's OPEN
            if self.pending_signal and not self.open_trade and self.pending_signal_candle:
                try:
                    # Validate risk and calculate SL based on the candle that generated the signal
                    stop_loss = calculate_stoploss(
                        side=self.pending_signal.side,
                        entry_price=candle.open,
                        signal_candle=self.pending_signal_candle,
                        max_distance=self.max_sl_distance,
                        mode=self.stoploss_mode
                    )
                    
                    take_profit = calculate_takeprofit(
                        side=self.pending_signal.side,
                        entry_price=candle.open,
                        stoploss_price=stop_loss,
                        risk_reward_ratio=self.rr_ratio
                    )
                    
                    # Enter trade
                    self.open_trade = {
                        "side": self.pending_signal.side,
                        "entry_time": candle.timestamp,
                        "entry_price": candle.open,
                        "entry_index": i,
                        "stop_loss": stop_loss,
                        "take_profit": take_profit,
                    }
                    
                except TradeRejected as e:
                    # Trade rejected by risk engine, ignore signal
                    logger.debug(f"Trade rejected: {e.reason}")
                
                # Signal consumed (whether entered or rejected)
                self.pending_signal = None
                self.pending_signal_candle = None

            # 2. If a trade is open, check for exits on this candle
            if self.open_trade:
                side = self.open_trade["side"]
                sl = self.open_trade["stop_loss"]
                tp = self.open_trade["take_profit"]
                entry_price = self.open_trade["entry_price"]
                
                exit_price = None
                result = None
                
                if side == "BUY":
                    # Check Stop Loss first
                    if candle.low <= sl:
                        # Slippage logic: if opened below SL, we exit at open
                        exit_price = min(sl, candle.open)
                        result = "LOSS"
                    # Check Take Profit
                    elif candle.high >= tp:
                        exit_price = tp
                        result = "WIN"
                elif side == "SELL":
                    # Check Stop Loss first
                    if candle.high >= sl:
                        # Slippage logic: if opened above SL, we exit at open
                        exit_price = max(sl, candle.open)
                        result = "LOSS"
                    # Check Take Profit
                    elif candle.low <= tp:
                        exit_price = tp
                        result = "WIN"
                        
                # Close trade if an exit was hit
                if exit_price is not None:
                    # Calculate PnL and deduct fees
                    fee = (entry_price * self.fee_rate) + (exit_price * self.fee_rate)
                    
                    if side == "BUY":
                        gross_pnl = exit_price - entry_price
                    else:
                        gross_pnl = entry_price - exit_price
                        
                    net_pnl = gross_pnl - fee
                    duration = i - self.open_trade["entry_index"]
                    
                    record = TradeRecord(
                        trade_number=len(self.trades) + 1,
                        side=side, # type: ignore
                        entry_time=self.open_trade["entry_time"],
                        entry_price=entry_price,
                        exit_time=candle.timestamp,
                        exit_price=exit_price,
                        stop_loss=sl,
                        take_profit=tp,
                        result=result, # type: ignore
                        profit_loss=net_pnl,
                        risk_reward=self.rr_ratio,
                        duration_candles=duration
                    )
                    self.trades.append(record)
                    self.open_trade = None

            # 3. If no trade is open, scan for new signals
            if not self.open_trade:
                # The signal engine only uses closed historical candles.
                # Passing candles up to index 'i' (inclusive) evaluates the signal 
                # immediately after candle 'i' closes.
                historical = self.candles[:i+1]
                
                signal = self.strategy.generate_signal(historical)
                if signal:
                    self.pending_signal = signal
                    self.pending_signal_candle = candle

        logger.info("Backtest simulation completed. Executed %d trades.", len(self.trades))
        return self.trades
