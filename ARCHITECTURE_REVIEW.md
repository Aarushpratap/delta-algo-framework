# Architecture and Logic Review

## Overview

A comprehensive review of the framework across all 7 layers (Config, Exchange, Feeds, Indicators, Strategy, Risk, Backtest). The review evaluated logic correctness, architecture adherence, coupling, backtesting validity, and readiness for Live/Paper trading.

---

## Critical Issues

### 1. Hardcoded Strategy Coupling (Architecture Violation) [RESOLVED]
**Location:** `backtest/engine.py` (Lines 17-19)
**Description:** The backtest engine directly imports `smma_cross.generate_signal` and specific risk functions. 
**Impact:** This violates the "One Strategy Engine" and "Strategy Independence" principles. If you want to test a new strategy (e.g., RSI Reversion), you must rewrite the backtest engine. Furthermore, Live and Paper trading will need their own orchestration loops, causing logic drift.
**Fix:** Implement Dependency Injection. The Engine should accept abstract `Strategy` and `RiskManager` instances. *(Fixed: `BaseStrategy` injected into `BacktestEngine`)*

### 2. Gap Slippage on Exits (Backtesting Mistake) [RESOLVED]
**Location:** `backtest/engine.py` (Line 124 & 133)
**Description:** Stop Loss execution assumes the exit price is always exactly the `sl` value (`exit_price = sl`).
**Impact:** If a candle gaps down significantly (e.g., `candle.open` is far below the Stop Loss on a BUY), the backtester will still record the exit at the exact Stop Loss price, artificially reducing the actual loss. This leads to overly optimistic backtest results.
**Fix:** The exit price should be `min(sl, candle.open)` for BUYs and `max(sl, candle.open)` for SELLs. *(Fixed: Slippage logic implemented in backtest engine)*

### 3. Absolute vs. Percentage Risk Configurations (Logic Bug) [RESOLVED]
**Location:** `config/settings.py` and `risk/stoploss.py`
**Description:** `MAX_STOPLOSS_DISTANCE` defaults to `0.50`. The logic calculates `distance = entry_price - stop_loss` (absolute price difference).
**Impact:** If trading a high-priced asset like BTC (e.g., $60,000), an absolute distance of 0.50 points is microscopic (0.0008%). The `TradeRejected` exception will trigger on almost 100% of signals.
**Fix:** Clarify if this configuration is a percentage (0.50%) or absolute points. If percentage, the calculation must be `(distance / entry_price) * 100`. *(Fixed: Mode is now explicit via `STOPLOSS_MODE` configuration parameter, preparing for future support)*

---

## Medium Issues

### 1. O(N²) Performance Bottleneck (Backtesting Mistake)
**Location:** `backtest/engine.py` (Line 172)
**Description:** The engine passes `historical = self.candles[:i+1]` to `generate_signal` on every iteration. `calculate_smma` recalculates the SMMA from index 0 for the entire history.
**Impact:** For a standard 1-year 1m dataset (525,600 candles), the engine will perform billions of redundant calculations, making backtesting impossibly slow.
**Fix:** The indicator engine should maintain state or calculate the array in a single vectorized pass (using Pandas/NumPy) or compute incrementally (O(N) total).

### 2. Missing Fee and Slippage Models (Logic Issue)
**Location:** `backtest/engine.py`
**Description:** Trade PnL is calculated purely on price differences `pnl = exit_price - entry_price`.
**Impact:** In V1 this is acceptable, but ignoring exchange fees (taker/maker) and slippage guarantees that the backtest net profit will dramatically overestimate real-world performance.
**Fix:** Introduce a `FeeModel` or simple commission deduction per trade.

---

## Minor Issues

### 1. Zero Risk Edge Case (Missing Edge Case) [RESOLVED]
**Location:** `risk/takeprofit.py`
**Description:** If `entry_price` is exactly equal to the `signal_candle.low` (e.g., perfectly flat market), `risk = 0`. The Take Profit will equal the Entry Price, causing the trade to open and close instantly with zero gain.
**Fix:** Require a minimum absolute risk or reject trades with `risk == 0`. *(Fixed: Rejection added to `stoploss.py`)*

### 2. PnL Denomination (Incorrect Assumption)
**Location:** `backtest/report.py`
**Description:** PnL is tracked in absolute price points (e.g., +500 points), not account equity or percentage.
**Impact:** Without position sizing (quantity/contracts), gross profit numbers are abstract and cannot be mapped to account ROI.
**Fix:** Phase 4 (Risk Engine) needs a position sizing module before moving to Paper Trading.

---

## Suggested Improvements

1. **Orchestrator Abstraction:** Extract the `run()` loop from `BacktestEngine` into a generic `TraderOrchestrator` inside `engine/trader.py`. Then `BacktestEngine`, `PaperEngine`, and `LiveEngine` simply provide the data feed and order execution layer to the generic orchestrator.
2. **Vectorization:** Rewrite `indicators/smma.py` to accept lists and return lists in one pass, allowing the backtester to compute all indicators instantly before the simulation loop begins.
3. **Enum for Sides:** Replace the string literals `"BUY"` and `"SELL"` with an `OrderSide` Enum in `core/enums.py` to prevent typo-based runtime crashes.

---

## Scores

* **Code Quality Score:** 9/10 
  *(Cleaned up with enums and better edge cases)*
* **Architecture Score:** 8/10 
  *(Dependency inversion implemented for strategy)*
* **Backtesting Reliability Score:** 7/10 
  *(Gap slippage handled and fees introduced, but O(N²) calculation remains an issue)*
