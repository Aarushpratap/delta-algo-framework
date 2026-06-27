# Delta Exchange Algo — Trading Framework

Production-grade, modular Python framework for the Delta Exchange API.  
Designed for **backtesting → paper trading → live trading** using the same strategy engine.

> **Current Phase: 1 — Market Data**  
> Phases 2–7 (indicators, signals, risk, backtesting, paper, live) will be added incrementally.

## Quick Start

```bash
# 1. Create a virtual environment
cd "Delta exchange algo"
python -m venv venv
venv\Scripts\activate          # Windows
# source venv/bin/activate     # macOS/Linux

# 2. Install dependencies
pip install -r requirements.txt

# 3. Configure
copy .env.example .env
# Edit .env with your API key, secret, symbols, and timeframe

# 4. Run Phase 1 demo
python main.py
```

## Architecture

```
┌─────────────────────────────────────────────────────────────────┐
│  main.py                         Bootstrap / entry point        │
├─────────────────────────────────────────────────────────────────┤
│  engine/trader.py                Orchestrator (Phase 5+)        │
├─────────────────────────────────────────────────────────────────┤
│  strategy/base.py                Abstract strategy (Phase 3+)   │
├──────────────────────┬──────────────────────────────────────────┤
│  feeds/              │  execution/                              │
│  ├ base.py           │  ├ base.py          (Phase 5+)          │
│  ├ live_feed.py  ✓   │  ├ live.py                              │
│  └ backtest_feed.py  │  ├ paper.py                             │
│                      │  └ backtest.py                           │
├──────────────────────┴──────────────────────────────────────────┤
│  exchange/                       Pure HTTP transport             │
│  ├ auth.py           HMAC-SHA256 signing                        │
│  ├ exceptions.py     Error hierarchy                            │
│  ├ rest_client.py    Single request() method                    │
│  └ ws_client.py      WebSocket placeholder                     │
├─────────────────────────────────────────────────────────────────┤
│  core/                           Domain models & enums          │
│  ├ enums.py          TradingMode                                │
│  └ models.py         Candle, Ticker, Balance, Position          │
├─────────────────────────────────────────────────────────────────┤
│  config/settings.py              Env-driven configuration       │
│  utils/logger.py                 Centralised logging            │
└─────────────────────────────────────────────────────────────────┘
```

**✓ = implemented** · unmarked = planned for future phases

## Project Structure

```
Delta exchange algo/
├── .env.example              # All configurable parameters
├── .gitignore
├── requirements.txt
├── README.md
├── main.py                   # Entry point (Phase 1 demo)
│
├── config/
│   ├── __init__.py
│   └── settings.py           # Reads .env → frozen Settings dataclass
│
├── core/
│   ├── __init__.py
│   ├── enums.py              # TradingMode (backtest / paper / live)
│   └── models.py             # Candle, Ticker, Balance, Position
│
├── exchange/
│   ├── __init__.py
│   ├── auth.py               # HMAC-SHA256 request signing
│   ├── exceptions.py         # DeltaAPIError, DeltaConnectionError
│   ├── rest_client.py        # Pure HTTP — single request() method
│   └── ws_client.py          # WebSocket placeholder
│
├── feeds/
│   ├── __init__.py
│   ├── base.py               # Abstract DataFeed interface
│   └── live_feed.py          # REST API → Candle/Ticker models
│
├── utils/
│   ├── __init__.py
│   └── logger.py             # Centralised logging config
│
└── data/
    └── .gitkeep              # Backtest CSV files (Phase 5)
```

## Design Principles

| Principle | Implementation |
|---|---|
| **Single Responsibility** | Each module does exactly one thing |
| **Strategy Independence** | Strategy never knows if it's backtesting or live |
| **Configuration Driven** | Timeframe, symbols, mode — all from `.env` |
| **No Hardcoding** | Zero magic numbers in source code |
| **Incremental Build** | 7 phases, each stable before the next begins |

## Configuration

All parameters live in `.env` — nothing is hardcoded:

| Variable | Values | Default |
|---|---|---|
| `DELTA_API_KEY` | Your API key | — |
| `DELTA_API_SECRET` | Your API secret | — |
| `DELTA_BASE_URL` | See URL table below | `https://api.india.delta.exchange` |
| `TRADING_MODE` | `backtest`, `paper`, `live` | `paper` |
| `CANDLE_RESOLUTION` | `1m`, `5m`, `15m`, `1h`, `4h`, `1d`, … | `1m` |
| `SYMBOLS` | Comma-separated (e.g. `BTCUSD,ETHUSD`) | `BTCUSD` |
| `LOG_LEVEL` | `DEBUG`, `INFO`, `WARNING`, `ERROR` | `INFO` |
| `BACKTEST_DATA_DIR` | Path to CSV data directory | `data` |

## Roadmap

| Phase | Focus | Status |
|---|---|---|
| 1 | Market Data | ✅ Complete |
| 2 | Indicators | ⬜ Planned |
| 3 | Signal Engine | ⬜ Planned |
| 4 | Risk Engine | ⬜ Planned |
| 5 | Backtesting | ⬜ Planned |
| 6 | Paper Trading | ⬜ Planned |
| 7 | Live Trading | ⬜ Planned |

## License

Private — internal use only.
