"""
live/live_monitor.py
────────────────────
Connects to real Delta market data and prints signals to the console.
Strictly read-only. Does not place orders or manage actual positions.
"""

from __future__ import annotations

import logging
import time

from feeds.live_feed import LiveDataFeed
from strategy.base import BaseStrategy
from risk.stoploss import calculate_stoploss, TradeRejected
from risk.takeprofit import calculate_takeprofit
from safety.safety_engine import SafetyEngine

logger = logging.getLogger(__name__)


class LiveMonitor:
    """
    Live Monitoring Engine.
    Polls the live feed, generates signals, evaluates risk and safety,
    and logs the result to the console and logger. Never executes orders.
    """

    def __init__(
        self,
        feed: LiveDataFeed,
        strategy: BaseStrategy,
        safety_engine: SafetyEngine,
        symbol: str,
        resolution: str,
        max_sl_distance: float,
        rr_ratio: float,
        stoploss_mode: str = "absolute"
    ) -> None:
        self.feed = feed
        self.strategy = strategy
        self.safety_engine = safety_engine
        self.symbol = symbol
        self.resolution = resolution
        self.max_sl_distance = max_sl_distance
        self.rr_ratio = rr_ratio
        self.stoploss_mode = stoploss_mode
        
        self.last_signal_time: int = 0

    def tick(self) -> None:
        """
        Executes a single tick of the monitoring loop.
        """
        try:
            # Fetch enough candles to initialize the longest indicator
            candles = self.feed.get_candles(self.symbol, self.resolution, limit=200)
        except Exception as e:
            logger.error("Live Monitor failed to fetch candles: %s", e)
            return

        if not candles:
            return

        # Delta returns the currently forming candle as the last item.
        # We slice it off to guarantee we only process fully completed candles.
        closed_candles = candles[:-1]
        
        if not closed_candles:
            return

        latest_closed = closed_candles[-1]

        # 1. Run Strategy Engine
        signal = self.strategy.generate_signal(closed_candles)

        if not signal:
            # No signal this tick
            return

        # Prevent repeating the same signal for the same closed candle
        if signal.timestamp <= self.last_signal_time:
            return

        self.last_signal_time = signal.timestamp

        # 2. Run Risk Engine
        sl = 0.0
        tp = 0.0
        risk_valid = True
        risk_reason = ""
        try:
            sl = calculate_stoploss(
                side=signal.side,
                entry_price=signal.price,
                signal_candle=latest_closed,
                max_distance=self.max_sl_distance,
                mode=self.stoploss_mode
            )
            tp = calculate_takeprofit(
                side=signal.side,
                entry_price=signal.price,
                stoploss_price=sl,
                risk_reward_ratio=self.rr_ratio
            )
        except TradeRejected as e:
            risk_valid = False
            risk_reason = e.reason

        # 3. Run Safety Engine
        # We mock balances and positions since this is strictly Monitor Mode
        safety_status, safety_reason = self.safety_engine.validate_execution(
            symbol=self.symbol,
            current_open_positions=0,
            is_api_connected=self.feed.is_connected,
            is_market_data_available=True,
            is_candle_complete=True,
            is_duplicate_signal=not risk_valid, # Use this to flag risk rejections logically
            balance_available=999999.0, # Dummy
            required_margin=0.0,
            is_trading_session_valid=True
        )
        
        if not risk_valid:
            safety_status = "REJECT"
            safety_reason = f"RISK_REJECTED: {risk_reason}"

        # 4. Console Output
        print("\n--- LIVE MONITOR SIGNAL ---")
        print(f"Time          : {signal.timestamp}")
        print(f"Signal        : {signal.side}")
        print(f"Entry         : {signal.price:.4f}")
        print(f"Stop Loss     : {sl:.4f}")
        print(f"Take Profit   : {tp:.4f}")
        print(f"Safety Result : {safety_status} ({safety_reason})")
        print("No Order Sent")
        print("---------------------------\n")

        # 5. File Logging
        logger.info(
            "LIVE SIGNAL | %s | %s | Entry: %.4f | SL: %.4f | TP: %.4f | Reason: %s | Safety: %s (%s)",
            signal.timestamp,
            signal.side,
            signal.price,
            sl,
            tp,
            signal.reason,
            safety_status,
            safety_reason
        )

    def run_forever(self, interval_seconds: int = 60) -> None:
        """
        Starts the continuous polling loop.
        """
        logger.info("Starting Live Monitor Mode for %s...", self.symbol)
        try:
            while True:
                self.tick()
                time.sleep(interval_seconds)
        except KeyboardInterrupt:
            logger.info("Live Monitor Mode stopped by user.")
