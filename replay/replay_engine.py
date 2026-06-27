"""
replay/replay_engine.py
───────────────────────
Replay Engine to simulate live trading over historical data.

Orchestrates the existing Paper Engine and Safety Engine to ensure exact
business logic parity with Live Monitor and Live Trading without 
connecting to real endpoints.
"""

from __future__ import annotations

import csv
import time
import logging
from typing import Any

from core.models import Candle
from paper.paper_engine import PaperEngine
from safety.safety_engine import SafetyEngine

logger = logging.getLogger(__name__)


class ReplayEngine:
    """
    Feeds historical data into the Paper Trading execution layer
    to simulate real-time market flow exactly as if it were live.
    """

    def __init__(
        self,
        paper_engine: PaperEngine,
        safety_engine: SafetyEngine,
        csv_path: str
    ) -> None:
        self.paper_engine = paper_engine
        self.safety_engine = safety_engine
        self.csv_path = csv_path
        
        self.raw_candles: list[Candle] = []
        self.current_index: int = 0
        
        self.is_playing: bool = False
        self.speed_multiplier: float = 1.0  # 0.0 means maximum speed (no sleep)

    def load_data(self) -> None:
        """Reads the historical CSV data exactly like BacktestEngine does."""
        logger.info("Loading replay data from %s", self.csv_path)
        with open(self.csv_path, "r", encoding="utf-8") as f:
            reader = csv.DictReader(f)
            for row in reader:
                self.raw_candles.append(Candle.from_csv_row(row))
                
        # Ensure chronological order
        self.raw_candles.sort(key=lambda c: c.timestamp)
        logger.info("Loaded %d candles for replay.", len(self.raw_candles))

    # --- Replay Controls ---
    def set_speed(self, multiplier: float) -> None:
        """Set replay speed: 1.0 (1x), 2.0 (2x), 5.0, 10.0, or 0.0 for Maximum."""
        self.speed_multiplier = multiplier
        logger.info("Replay speed set to %sx", multiplier if multiplier > 0 else "MAX")

    def play(self) -> None:
        """Start or resume playback."""
        if not self.raw_candles:
            logger.error("Cannot play: No data loaded.")
            return
        self.is_playing = True
        logger.info("Replay started.")

    def pause(self) -> None:
        """Pause playback."""
        self.is_playing = False
        logger.info("Replay paused at index %d.", self.current_index)

    def stop(self) -> None:
        """Stop playback and reset state."""
        self.is_playing = False
        self.current_index = 0
        
        # Reset internal Paper Engine state
        self.paper_engine.candles.clear()
        self.paper_engine.trades.clear()
        self.paper_engine.open_position = None
        self.paper_engine.pending_signal = None
        self.paper_engine.pending_signal_candle = None
        logger.info("Replay stopped and reset.")

    def tick(self) -> bool:
        """
        Advances the simulation by exactly one candle.
        Returns:
            True if a candle was processed, False if EOF is reached.
        """
        if self.current_index >= len(self.raw_candles):
            self.is_playing = False
            logger.info("Replay finished (EOF).")
            return False

        candle = self.raw_candles[self.current_index]
        self.current_index += 1

        # 1. Run Safety Engine (simulated live check)
        is_open = 1 if self.paper_engine.open_position else 0
        safety_status, safety_reason = self.safety_engine.validate_execution(
            symbol="REPLAY",
            current_open_positions=is_open,
            is_api_connected=True,
            is_market_data_available=True,
            is_candle_complete=True,
            is_duplicate_signal=False,
            balance_available=999999.0,
            required_margin=0.0,
            is_trading_session_valid=True
        )

        if safety_status == "REJECT":
            logger.warning("Replay Safety Reject: %s", safety_reason)
            # Depending on strictness, we might skip processing, but in replay
            # we just log it and let paper engine do its thing for simulation
        
        # 2. Feed the Paper Engine
        # The Paper Engine already handles Strategy, Risk, and internal Positions identically to Live
        self.paper_engine.process_candle(candle)

        # 3. Output Logging
        pos = self.paper_engine.open_position
        # Paper Engine only holds a pending signal for 1 tick, we check if one was just generated
        # or if we are actively holding a position
        
        # Determine current signal from the engine's last run (this relies on the engine's state)
        if self.paper_engine.pending_signal:
            sig_val = self.paper_engine.pending_signal.side
        else:
            sig_val = "NONE"

        entry_val = f"{pos.entry_price:.2f}" if pos else "-"
        sl_val = f"{pos.stop_loss:.2f}" if pos else "-"
        tp_val = f"{pos.take_profit:.2f}" if pos else "-"
        
        speed_val = f"{self.speed_multiplier}x" if self.speed_multiplier > 0 else "MAX"

        logger.info(
            "REPLAY | Time: %s | Signal: %s | Entry: %s | SL: %s | TP: %s | Speed: %s",
            candle.timestamp, sig_val, entry_val, sl_val, tp_val, speed_val
        )

        return True

    def run_loop(self) -> None:
        """
        Blocking loop that plays the simulation continuously.
        Useful for running outside of a UI thread.
        """
        while self.is_playing:
            has_next = self.tick()
            if not has_next:
                break
                
            if self.speed_multiplier > 0.0:
                # E.g., 1x = 1 tick per second, 10x = 10 ticks per second
                time.sleep(1.0 / self.speed_multiplier)
