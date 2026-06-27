"""
paper/paper_position.py
───────────────────────
Virtual position tracking for Paper Trading.
"""

from dataclasses import dataclass
from strategy.base import SignalSide

@dataclass
class PaperPosition:
    """
    State tracking for a simulated trade.
    """
    side: SignalSide
    entry_time: int
    entry_price: float
    stop_loss: float
    take_profit: float
    entry_index: int
    current_status: str = "OPEN"
    current_pnl: float = 0.0
