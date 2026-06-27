"""
paper/paper_engine.py
─────────────────────
Paper Trading execution engine.

Receives live candles, evaluates signals, and manages a virtual position
by reusing the exact Strategy and Risk logic used in Backtesting.
"""

from __future__ import annotations

import logging

from core.models import Candle
from risk.stoploss import calculate_stoploss, TradeRejected
from risk.takeprofit import calculate_takeprofit
from strategy.base import BaseStrategy
from backtest.report import TradeRecord
from paper.paper_position import PaperPosition

logger = logging.getLogger(__name__)


class PaperEngine:
    """
    Simulates live trading using real-time market data without placing actual orders.
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
        
        self.open_position: PaperPosition | None = None
        
        # Pending signals wait for the next candle to open
        self.pending_signal = None
        self.pending_signal_candle: Candle | None = None

    def process_candle(self, candle: Candle) -> None:
        """
        Process a new incoming live candle.
        This function handles Entry, Exit, and Signal Generation in order.
        """
        # 1. Attempt to enter trade if we have a pending signal (Entry on next candle OPEN)
        if self.pending_signal and not self.open_position and self.pending_signal_candle:
            try:
                # Validate risk based on the signal candle, entering at current candle's open
                sl = calculate_stoploss(
                    side=self.pending_signal.side,
                    entry_price=candle.open,
                    signal_candle=self.pending_signal_candle,
                    max_distance=self.max_sl_distance,
                    mode=self.stoploss_mode
                )
                
                tp = calculate_takeprofit(
                    side=self.pending_signal.side,
                    entry_price=candle.open,
                    stoploss_price=sl,
                    risk_reward_ratio=self.rr_ratio
                )
                
                self.open_position = PaperPosition(
                    side=self.pending_signal.side,
                    entry_time=candle.timestamp,
                    entry_price=candle.open,
                    stop_loss=sl,
                    take_profit=tp,
                    entry_index=len(self.candles)
                )
                logger.info(
                    "PAPER TRADE OPENED: Side=%s, Entry=%.2f, SL=%.2f, TP=%.2f",
                    self.open_position.side, self.open_position.entry_price, sl, tp
                )
            except TradeRejected as e:
                logger.debug("PAPER TRADE REJECTED: %s", e.reason)
            
            # Consume the signal
            self.pending_signal = None
            self.pending_signal_candle = None

        # 2. Monitor active position (Exits and PnL updates)
        if self.open_position:
            side = self.open_position.side
            sl = self.open_position.stop_loss
            tp = self.open_position.take_profit
            entry = self.open_position.entry_price
            
            # Update floating PnL (for potential dashboards/monitoring)
            if side == "BUY":
                gross_pnl = candle.close - entry
            else:
                gross_pnl = entry - candle.close
                
            fee_accumulated = (entry * self.fee_rate) + (candle.close * self.fee_rate)
            self.open_position.current_pnl = gross_pnl - fee_accumulated
            
            exit_price = None
            result = None
            
            if side == "BUY":
                # Exit gap simulation: open could gap past SL
                if candle.low <= sl:
                    exit_price = min(sl, candle.open)
                    result = "LOSS"
                elif candle.high >= tp:
                    exit_price = tp
                    result = "WIN"
            elif side == "SELL":
                # Exit gap simulation: open could gap past SL
                if candle.high >= sl:
                    exit_price = max(sl, candle.open)
                    result = "LOSS"
                elif candle.low <= tp:
                    exit_price = tp
                    result = "WIN"
            
            if exit_price is not None:
                # Calculate final closed PnL
                fee_final = (entry * self.fee_rate) + (exit_price * self.fee_rate)
                if side == "BUY":
                    net_pnl = (exit_price - entry) - fee_final
                else:
                    net_pnl = (entry - exit_price) - fee_final
                    
                duration = len(self.candles) - self.open_position.entry_index
                
                record = TradeRecord(
                    trade_number=len(self.trades) + 1,
                    side=side, # type: ignore
                    entry_time=self.open_position.entry_time,
                    entry_price=entry,
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
                self.open_position = None
                logger.info(
                    "PAPER TRADE CLOSED: Result=%s, Exit=%.2f, PnL=%.2f",
                    result, exit_price, net_pnl
                )

        # Append candle to historical state *after* evaluating exits for the current candle,
        # but *before* generating signals, to ensure the new candle is fully closed.
        self.candles.append(candle)

        # 3. Scan for new signals if flat
        if not self.open_position:
            # We generate a signal based on the history including the recently closed candle.
            signal = self.strategy.generate_signal(self.candles)
            if signal:
                self.pending_signal = signal
                self.pending_signal_candle = candle
                logger.info(
                    "PAPER SIGNAL GENERATED: %s at %.2f (Reason: %s)",
                    signal.side, signal.price, signal.reason
                )
