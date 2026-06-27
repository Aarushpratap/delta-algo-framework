# Integration Test Report

## Summary
* **Total Integration Tests:** 1
* **Passed:** 1
* **Failed:** 0

## Full Pipeline Status
The end-to-end integration test successfully validated the entire data flow and state machine of the trading framework:

**Pipeline Verified:** `Historical CSV` → `Feed Layer` → `Indicator Engine` → `Strategy Engine` → `Risk Engine` → `Backtesting Engine` → `Trade Report`

### Behaviours Validated
1. **Historical Candles loaded correctly:** Verified parsing string data into `Candle` models.
2. **Indicators calculated correctly:** SMMA initialized and maintained state cleanly over time.
3. **Signal generation occurs only after candle close:** Verified cross-overs trigger signals without look-ahead bias.
4. **Risk Engine receives correct signal:** Stop losses accurately mapped to the specific `Signal` source candle.
5. **Stop Loss is calculated correctly:** Confirmed exact target levels mapping.
6. **Take Profit is calculated correctly:** Confirmed RR distances are correctly established.
7. **Trade opens on next candle OPEN:** Execution is strictly delayed until the next chronological candle opens.
8. **Trade exits correctly:** Exits trigger logically on intra-candle highs/lows.
9. **Statistics are updated correctly:** Accuracy validated on gross/net metrics and win rates.
10. **Trade log is correct:** Output trade arrays track all lifecycle events accurately.
11. **No duplicate trades:** Multiple signals in the same direction did not result in stacked orders.
12. **One trade at a time:** Opposing signals generated while a trade was active were correctly ignored.
13. **Fees deducted correctly:** Exact fee math (percentage of Entry + Exit) successfully deducted from Net PNL.
14. **Gap stoploss behaves correctly:** When the market gapped beyond a limit Stop Loss, the exit executed dynamically at the worse OPEN price rather than the artificial SL price.

## Remaining Risks
* **O(N²) Indicator Loop:** The Backtest engine currently evaluates strategy signals by passing *all* historical candles up to index `i` on every loop iteration. While mathematically accurate, this does not scale to datasets with millions of rows. This must be refactored to a streaming data architecture or vectorized arrays before running heavy optimization backtests.
* **Paper Trading Execution Variance:** The pipeline correctly routes simulated orders, but Paper Trading will introduce latency, WebSocket asynchronous ticks, and partial fills which are currently mocked as immediate FOK (Fill-or-Kill) logic here.
