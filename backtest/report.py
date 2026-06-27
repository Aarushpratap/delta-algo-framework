"""
backtest/report.py
──────────────────
Data models and calculations for backtest reporting.

Generates trading statistics from a list of completed trades and prints
a console-friendly summary.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Literal


@dataclass(frozen=True, slots=True)
class TradeRecord:
    """Immutable record of a single completed trade."""
    trade_number: int
    side: Literal["BUY", "SELL"]
    entry_time: int
    entry_price: float
    exit_time: int
    exit_price: float
    stop_loss: float
    take_profit: float
    result: Literal["WIN", "LOSS"]
    profit_loss: float
    risk_reward: float
    duration_candles: int


@dataclass(frozen=True, slots=True)
class BacktestStatistics:
    """Aggregated metrics for a backtest run."""
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    net_profit: float
    gross_profit: float
    gross_loss: float
    largest_win: float
    largest_loss: float
    average_win: float
    average_loss: float
    consecutive_wins: int
    consecutive_losses: int


def generate_report(trades: list[TradeRecord]) -> BacktestStatistics:
    """Calculate aggregate statistics from a list of trades."""
    total_trades = len(trades)
    
    if total_trades == 0:
        return BacktestStatistics(
            total_trades=0, winning_trades=0, losing_trades=0, win_rate=0.0,
            net_profit=0.0, gross_profit=0.0, gross_loss=0.0,
            largest_win=0.0, largest_loss=0.0, average_win=0.0, average_loss=0.0,
            consecutive_wins=0, consecutive_losses=0
        )

    winning_trades = 0
    losing_trades = 0
    gross_profit = 0.0
    gross_loss = 0.0
    largest_win = 0.0
    largest_loss = 0.0

    current_consec_wins = 0
    max_consec_wins = 0
    current_consec_losses = 0
    max_consec_losses = 0

    for trade in trades:
        if trade.profit_loss > 0:
            winning_trades += 1
            gross_profit += trade.profit_loss
            largest_win = max(largest_win, trade.profit_loss)
            
            current_consec_wins += 1
            max_consec_wins = max(max_consec_wins, current_consec_wins)
            current_consec_losses = 0
        else:
            losing_trades += 1
            gross_loss += abs(trade.profit_loss)
            largest_loss = min(largest_loss, trade.profit_loss)
            
            current_consec_losses += 1
            max_consec_losses = max(max_consec_losses, current_consec_losses)
            current_consec_wins = 0

    net_profit = gross_profit - gross_loss
    win_rate = (winning_trades / total_trades) * 100 if total_trades > 0 else 0.0
    average_win = gross_profit / winning_trades if winning_trades > 0 else 0.0
    average_loss = gross_loss / losing_trades if losing_trades > 0 else 0.0

    return BacktestStatistics(
        total_trades=total_trades,
        winning_trades=winning_trades,
        losing_trades=losing_trades,
        win_rate=win_rate,
        net_profit=net_profit,
        gross_profit=gross_profit,
        gross_loss=gross_loss,
        largest_win=largest_win,
        largest_loss=largest_loss,
        average_win=average_win,
        average_loss=average_loss,
        consecutive_wins=max_consec_wins,
        consecutive_losses=max_consec_losses
    )


def print_report(stats: BacktestStatistics) -> None:
    """Print the backtest statistics to the console."""
    print("=" * 50)
    print(" BACKTEST REPORT")
    print("=" * 50)
    print(f"Total Trades       : {stats.total_trades}")
    print(f"Winning Trades     : {stats.winning_trades}")
    print(f"Losing Trades      : {stats.losing_trades}")
    print(f"Win Rate           : {stats.win_rate:.2f}%")
    print("-" * 50)
    print(f"Net Profit         : {stats.net_profit:.2f}")
    print(f"Gross Profit       : {stats.gross_profit:.2f}")
    print(f"Gross Loss         : {stats.gross_loss:.2f}")
    print("-" * 50)
    print(f"Largest Win        : {stats.largest_win:.2f}")
    print(f"Largest Loss       : {stats.largest_loss:.2f}")
    print(f"Average Win        : {stats.average_win:.2f}")
    print(f"Average Loss       : {stats.average_loss:.2f}")
    print("-" * 50)
    print(f"Consecutive Wins   : {stats.consecutive_wins}")
    print(f"Consecutive Losses : {stats.consecutive_losses}")
    print("=" * 50)
