# Changelog

## Completed So Far (Phase 1 - Market Data)

* **Infrastructure/Project Setup**: Initialized project structure, `.env.example`, `.gitignore`, `requirements.txt`.
* **Configuration Module**: Implemented `config/settings.py` for configuration-driven settings without hardcoded parameters.
* **Core Domain Models**: Created `core/models.py` (Candle, Ticker, Balance, Position) and `core/enums.py` (TradingMode).
* **Exchange Layer (HTTP Transport)**: 
  * Extracted exception handling into `exchange/exceptions.py`.
  * Refactored `exchange/rest_client.py` into a pure HTTP transport layer (stateless, single `request` method).
  * Maintained `exchange/auth.py` for HMAC-SHA256 request signing.
  * Preserved `exchange/ws_client.py` as a placeholder for WebSocket capabilities.
* **Data Feeds Layer**: 
  * Defined abstract `DataFeed` base class in `feeds/base.py`.
  * Implemented concrete `LiveDataFeed` in `feeds/live_feed.py` for REST API data transformation to domain models.
* **Utilities**: Implemented centralized logging in `utils/logger.py`.
* **Bootstrap**: Created `main.py` entry point to demo the Market Data layer.

## Completed So Far (Phase 2 - Indicator Engine)

* **Indicator Engine**: 
  * Created `indicators/__init__.py` and `indicators/smma.py`.
  * Implemented pure SMMA calculation logic without side effects.
  * Added `calculate_fast_smma` (default 5 periods) and `calculate_slow_smma` (default 100 periods).

## Completed So Far (Phase 3 - Signal Engine)

* **Signal Engine**:
  * Created `strategy/__init__.py` and `strategy/smma_cross.py`.
  * Implemented pure signal generation logic handling SMMA crossovers on closed candles.
  * Added `Signal` dataclass containing side, timestamp, price, and reason.

## Completed So Far (Phase 4 - Risk Engine)

* **Risk Engine**:
  * Added `MAX_STOPLOSS_DISTANCE` and `RISK_REWARD_RATIO` to `config/settings.py` and `.env.example`.
  * Created `risk/__init__.py`, `risk/stoploss.py`, and `risk/takeprofit.py`.
  * Implemented trade rejection logic via `TradeRejected` exception when stop loss distance exceeds the maximum limit.
  * Implemented pure target calculation logic based on configurable Risk:Reward ratio.

## Completed So Far (Phase 5 - Backtesting Engine)

* **Backtesting Engine**:
  * Created `backtest/__init__.py`, `backtest/engine.py`, and `backtest/report.py`.
  * Implemented historical simulation loop that chronologically processes candles, manages signals, and enforces risk logic.
  * Extracted strategy execution via Dependency Injection of abstract `BaseStrategy`.
  * Implemented gap-aware Stop Loss execution (preventing artificial fills when opening beyond stops).
  * Implemented configurable trade fee execution to improve net profit accuracy.
  * Exit priority logic strictly evaluates Stop Loss before Take Profit.

## Completed So Far (Validation Suite)

* **Testing and Verification**:
  * Created unit test suites for `indicators`, `strategy`, `risk`, and `backtest` engines in the `tests/` directory.
  * Verified logic correctness, gap slippage handling, deterministic signal generation, and fee deduction with Pytest.
  * Achieved 81% test coverage across core modules.
  * Created `tests/test_integration.py` establishing an end-to-end pipeline test from CSV data ingestion through statistics generation.

## Completed So Far (Phase 6A - Paper Trading Engine)

* **Paper Trading Engine**:
  * Created `paper/__init__.py`, `paper/paper_position.py`, and `paper/paper_engine.py`.
  * Implemented an online simulated execution engine (`PaperEngine`) that receives single candles and manages a `PaperPosition`.
  * Verified exact reuse of Strategy, Risk, and reporting logic without duplicating business rules.
  * Ensures no real API orders are placed during simulation.

## Completed So Far (Phase 6.5 - Safety Engine)

* **Safety Engine**:
  * Created `safety/__init__.py` and `safety/safety_engine.py`.
  * Implemented 10 strict pre-execution checks (e.g., API status, balances, max positions, duplicate signals).
  * Enforced return types `ALLOW` and `REJECT` mapping to specific safety failure reasons without generating actual orders.

## Completed So Far (Phase 7A - Live Monitor Mode)

* **Live Monitor Mode**:
  * Created `live/__init__.py` and `live/live_monitor.py`.
  * Implemented an online orchestrator `LiveMonitor` that continuously polls `LiveDataFeed`.
  * Pipes real-time completed candles through the Strategy, Risk, and Safety engines.
  * Outputs generated signals directly to the console and logger.
  * Strictly read-only implementation; zero real orders are transmitted, ensuring safety.

## Completed So Far (Phase 6.8 - Streamlit Dashboard)

* **Streamlit Dashboard**:
  * Created `dashboard/__init__.py` and `dashboard/app.py`.
  * Implemented a professional, dark-themed trading terminal using Streamlit and Plotly.
  * Reused existing modules (Backtest, Live Monitor, Strategy, etc.) without duplicating business logic.
  * Added live polling for monitor mode, equity curve charts, performance metrics, and system log viewing.

## Completed So Far (Phase 6.9 - Replay Engine)

* **Replay Engine**:
  * Created `replay/__init__.py` and `replay/replay_engine.py`.
  * Implemented an orchestration layer that streams static CSV data through the live `PaperEngine` and `SafetyEngine` seamlessly.
  * Added playback controls: play, pause, stop, and granular speed settings (1x up to maximum speed).
  * Exposes precise internal state (price, signal, open position, PnL) per tick.
  * Ensures zero duplication of business logic and zero outbound API calls during simulation.

## Pending Modules

* **Live Order Execution (Phase 7B)**: Real Delta Exchange order placement.

---

## Completed So Far (Production Deployment Pack)

* **Deployment Scripts** (`deploy/`):
  * `install.sh` — One-time environment setup (venv, pip, logs dir, .env check).
  * `deploy.sh` — Git pull + pip install + service restart in one command.
  * `start.sh` — Start the systemd service and print the dashboard URL.
  * `stop.sh` — Gracefully stop the systemd service.
  * `restart.sh` — Restart the systemd service with status output.
  * `status.sh` — Show service state, Python version, git branch/commit, and dashboard URL.
* **systemd Service** (`systemd/delta-algo.service`):
  * Auto-starts on reboot via `WantedBy=multi-user.target`.
  * Loads `.env` via `EnvironmentFile`.
  * `Restart=always` with 10-second back-off.
  * Logs to journald (`journalctl -u delta-algo -f`).
* **Health Check** (`healthcheck.py`):
  * Checks Python ≥ 3.10, `.env` presence, API key/secret validity, all pip packages, and dashboard file.
  * Returns PASS/FAIL per check and exits non-zero if any check fails.
* **Environment Template** (`.env.example`):
  * Complete template derived from `config/settings.py` covering every env var with inline documentation.
* **Logs Directory** (`logs/.gitkeep`):
  * Tracked empty directory for runtime log file output.

## Completed So Far (Production Deployment Pack v2 — Oracle Style)

* **systemd service** (`systemd/delta-algo.service`):
  * Fixed `WorkingDirectory` and `EnvironmentFile` to use Oracle path `/home/rdpuser/delta-algo-framework`.
  * `DASHBOARD_PORT` dynamically read from `.env` — no hardcoded port.
  * `RestartSec=5`, `After=network-online.target`, journald logging.
* **Improved scripts** (`deploy/`):
  * `install.sh` — Added Python version verification and healthcheck call.
  * `deploy.sh` — Conditional pip (only if requirements hash changed), backup before deploy, env-driven `SERVICE_NAME`.
  * `start.sh`, `stop.sh`, `restart.sh` — Dynamic `SERVICE_NAME` and port from `.env`.
  * `status.sh` — Shows git, service, Python, venv, dashboard URL, and live healthcheck.
* **New scripts** (`deploy/`):
  * `doctor.sh` — 30+ point diagnostic: .env, credentials, venv, packages, project structure, file permissions, logs directory.
  * `logs.sh` — Streams `journalctl -u $SERVICE_NAME -f` with extra argument passthrough.
  * `backup.sh` — Creates timestamped `.tar.gz` in `backups/`, writes `latest.txt` pointer.
  * `rollback.sh` — Stops service, restores backup (preserving `.env`), restarts; interactive confirmation.
  * `update.sh` — Single command: backup → git pull → pip (conditional) → doctor → restart → status.
* **Improved `healthcheck.py`**:
  * Added checks for: internet connectivity, Delta REST endpoint reachability, `config/settings.py` presence.
  * `--quiet` flag suppresses per-check lines, prints only summary.
  * Structured output with section headers; exits with non-zero code on any failure.
* **`.env.example`** — Added `SERVICE_NAME=delta-algo` deployment variable.
* **`.gitignore`** — Added `backups/` and `.requirements.md5` to ignored paths.

---

## Hotfix v2.1 — systemd Startup Failure Fix

**Root Cause**: systemd `EnvironmentFile` loads variables into the process
environment but does **not** perform shell variable expansion inside `ExecStart=`.
The token `${DASHBOARD_PORT}` was passed as a literal string to Streamlit,
causing an argument-parse failure (`status=2`).

**Fix Applied**:
* **Created `deploy/start-streamlit.sh`**: Thin wrapper script that is the
  actual `ExecStart` target. It `source`s `.env` itself, resolves
  `DASHBOARD_PORT` with a safe default, then `exec`s the venv Streamlit binary
  with the concrete port number. systemd still manages the process lifetime.
* **Updated `systemd/delta-algo.service`**: `ExecStart` now points to
  `/bin/bash /home/rdpuser/delta-algo-framework/deploy/start-streamlit.sh`.
  All other settings (`Restart`, `RestartSec`, `WorkingDirectory`,
  `EnvironmentFile`, venv) are preserved.
* **Updated `deploy/start.sh`**: Waits 3 seconds after `systemctl start` then
  checks `is-active`. On failure, automatically prints `systemctl status` and
  `journalctl -n 50` — zero manual debugging needed.
* **Updated `deploy/status.sh`**: Now displays MainPID, resolved listening port
  (from `ss -tlnp`), last start/stop timestamp, and inline healthcheck summary.
* **Updated `deploy/install.sh`**: Added step 6 — validates systemd service
  syntax (`systemd-analyze verify`), confirms `start-streamlit.sh` exists,
  confirms venv Streamlit binary exists, confirms `dashboard/app.py` exists,
  and makes all deploy scripts executable. Fails fast if any check fails.


* **Execution Engines**: 
  * `execution/base.py` (Abstract Executor)
  * `execution/live.py` (Live orders)
  * `execution/paper.py` (Simulated fills)
  * `execution/backtest.py` (Historical simulation)
* **Backtest Data Feed**: `feeds/backtest_feed.py` for reading from CSVs.
* **Trader Engine**: Orchestrator module (`engine/trader.py`) that wires Feeds, Executors, and Strategies together.
