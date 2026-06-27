# Validation Suite Test Report

## Summary
* **Total Tests:** 15
* **Passed Tests:** 15
* **Failed Tests:** 0
* **Coverage Summary:** 81% overall coverage across the trading engine modules.

## Module Coverage Breakdown
* **Indicators (`indicators/smma.py`):** 86%
* **Strategy (`strategy/smma_cross.py`):** 96%
* **Risk (`risk/stoploss.py`, `risk/takeprofit.py`):** 91%
* **Backtest (`backtest/engine.py`):** 80%

## Verified Behaviours

### Indicator Engine
* Accurate initial SMA and subsequent SMMA recursive calculations.
* Correct handling of insufficient historical candle data.

### Strategy Engine
* Successfully identified bullish SMMA crossovers.
* Successfully identified bearish SMMA crossovers.
* Handled steady non-crossing markets cleanly.
* Confirmed signal generation strictly bound to closed candles.

### Risk Engine
* Validated SL calculations mapping to entry candle boundaries.
* Successfully rejected trades that exceed maximum SL limits.
* Successfully rejected boundary zero-risk edge cases.
* Confirmed Take Profit distance extensions via Risk:Reward configurations.

### Backtesting Engine
* Enforced one-trade-at-a-time constraint across sequences.
* Executed delayed entry strictly on the next candle open.
* Respected exit priorities by checking Stop Loss *before* Take Profit within the same candle.
* Simulated gap-slippage, ensuring entry-open stops were honoured instead of strictly limit stops.
* Deducted calculated configurable trading fees strictly from final PnL outputs.

## Remaining Issues
* **None identified** that affect correctness in Version 1. The validation suite confirms the pure-functional components operate exactly according to the design criteria without logical errors.
