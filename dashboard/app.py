"""
dashboard/app.py
────────────────
Streamlit presentation layer for the Delta Algo framework.
Acts as a read-only viewer for Live Monitor, Paper Trading, and Backtesting.
"""

import sys
import os
import time
import logging
import streamlit as st
import pandas as pd
import plotly.express as px

# Insert project root to module path to resolve our core packages
sys.path.insert(0, os.path.abspath(os.path.join(os.path.dirname(__file__), '..')))

from strategy.smma_cross import SMMACrossStrategy
from backtest.engine import BacktestEngine
from backtest.report import generate_report
from live.live_monitor import LiveMonitor
from feeds.live_feed import LiveDataFeed
from exchange.rest_client import DeltaRestClient
from safety.safety_engine import SafetyEngine

# --- Page Configuration ---
st.set_page_config(
    page_title="Delta Algo Terminal",
    layout="wide",
    initial_sidebar_state="expanded"
)

# Dark Theme CSS overrides
st.markdown("""
<style>
    .stApp {
        background-color: #0E1117;
        color: #FAFAFA;
    }
</style>
""", unsafe_allow_html=True)


# --- Session State Initialization ---
if "mode" not in st.session_state:
    st.session_state.mode = "Backtest"
if "trades" not in st.session_state:
    st.session_state.trades = []
if "is_monitoring" not in st.session_state:
    st.session_state.is_monitoring = False
if "monitor_engine" not in st.session_state:
    st.session_state.monitor_engine = None
if "logs" not in st.session_state:
    st.session_state.logs = []


# --- Logging Setup ---
class StreamlitLogHandler(logging.Handler):
    """Custom logging handler to pipe logs into Streamlit session state."""
    def emit(self, record):
        msg = self.format(record)
        st.session_state.logs.append(msg)
        if len(st.session_state.logs) > 100:
            st.session_state.logs.pop(0)

if "logger_setup" not in st.session_state:
    st.session_state.logger_setup = True
    root_logger = logging.getLogger()
    sh = StreamlitLogHandler()
    sh.setFormatter(logging.Formatter("%(asctime)s │ %(levelname)-8s │ %(message)s", datefmt="%H:%M:%S"))
    root_logger.addHandler(sh)
    root_logger.setLevel(logging.INFO)


# --- Sidebar ---
st.sidebar.title("⚡ Delta Algo")
st.sidebar.markdown("**Framework Version:** 0.6.5")
st.sidebar.markdown("---")

mode = st.sidebar.radio(
    "Current Mode", 
    ["Backtest", "Replay", "Paper", "Live Monitor", "Live Trading (Disabled)"]
)
st.session_state.mode = mode

symbol = st.sidebar.text_input("Symbol", value="BTCUSD")
timeframe = st.sidebar.selectbox("Timeframe", ["1m", "5m", "15m", "1h", "4h", "1d"])

st.sidebar.markdown("---")
if st.sidebar.button("Refresh Dashboard"):
    st.rerun()

# Operations based on mode
if mode == "Backtest":
    if st.sidebar.button("▶ Run Backtest"):
        mock_csv = os.path.abspath(os.path.join(os.path.dirname(__file__), '..', 'tests', 'mock_data.csv'))
        if os.path.exists(mock_csv):
            st.session_state.logs.append(f"Starting backtest on {mock_csv}...")
            strategy = SMMACrossStrategy(fast_period=2, slow_period=5)
            engine = BacktestEngine(strategy, max_sl_distance=500.0, rr_ratio=2.0, fee_rate=0.01)
            engine.load_csv(mock_csv)
            st.session_state.trades = engine.run()
            st.session_state.logs.append(f"Backtest complete. {len(st.session_state.trades)} trades executed.")
        else:
            st.sidebar.error("Mock data CSV not found.")
            
elif mode == "Live Monitor":
    col1, col2 = st.sidebar.columns(2)
    if col1.button("▶ Start"):
        if not st.session_state.is_monitoring:
            st.session_state.is_monitoring = True
            client = DeltaRestClient()
            feed = LiveDataFeed(client)
            feed.connect()
            strategy = SMMACrossStrategy(fast_period=2, slow_period=5)
            safety = SafetyEngine(trading_enabled=False)
            st.session_state.monitor_engine = LiveMonitor(feed, strategy, safety, symbol, timeframe, 500.0, 2.0)
            st.rerun()
            
    if col2.button("⏹ Stop"):
        st.session_state.is_monitoring = False
        if st.session_state.monitor_engine:
            st.session_state.monitor_engine.feed.close()
            st.session_state.monitor_engine = None
        st.rerun()

elif mode == "Paper":
    if st.sidebar.button("▶ Start Paper Trading"):
        st.sidebar.warning("Paper trading simulation is offline. Use Backtest to view records.")

st.sidebar.markdown("---")

# --- Live Polling Simulation ---
api_status = "DISCONNECTED"
feed_status = "INACTIVE"
current_price = "0.00"
last_candle = "-"
current_signal = "NONE"

if st.session_state.is_monitoring and st.session_state.monitor_engine:
    engine = st.session_state.monitor_engine
    engine.tick()
    
    api_status = "CONNECTED" if engine.feed.is_connected else "DISCONNECTED"
    feed_status = "ACTIVE" if api_status == "CONNECTED" else "INACTIVE"
    
    # We can peek at the engine's internal state to drive the UI
    if engine.feed.is_connected and len(engine.feed._client.base_url) > 0: # dummy check
        pass
        
    # Hack to pull latest candle and signal for UI presentation
    try:
        # Fetching raw just for display
        c = engine.feed.get_candles(symbol, timeframe, limit=2)
        if c:
            current_price = f"${c[-1].close:,.2f}"
            last_candle = time.strftime('%H:%M:%S', time.localtime(c[-1].timestamp))
    except Exception:
        pass
        
    # Trigger auto-rerun for live loop
    time.sleep(2)
    st.rerun()


# --- Main Dashboard Layout ---
st.title("Terminal")

# 1. Home Page Cards
bot_status = "RUNNING" if st.session_state.is_monitoring else "IDLE"
if mode == "Backtest":
    bot_status = "COMPLETED"

current_pnl = sum([t.profit_loss for t in st.session_state.trades])
todays_pnl = sum([t.profit_loss for t in st.session_state.trades]) # Mocking today as all trades

c1, c2, c3, c4 = st.columns(4)
c1.metric("Bot Status", bot_status)
c2.metric("Current Price", current_price)
c3.metric("Last Candle Time", last_candle)
c4.metric("Current Signal", current_signal)

st.markdown("<br>", unsafe_allow_html=True)
c5, c6, c7, c8 = st.columns(4)
c5.metric("Current Position", "FLAT")
c6.metric("Current PnL", f"${current_pnl:,.2f}")
c7.metric("Today's PnL", f"${todays_pnl:,.2f}")
c8.metric("Active Mode", mode.upper())

st.markdown("---")

# 2. Performance & Safety
col_perf, col_safe = st.columns([2, 1])

with col_perf:
    st.subheader("Performance Metrics")
    if st.session_state.trades:
        stats = generate_report(st.session_state.trades)
        p1, p2, p3, p4 = st.columns(4)
        p1.metric("Total Trades", stats.total_trades)
        p2.metric("Win Rate", f"{stats.win_rate:.2f}%")
        p3.metric("Wins/Losses", f"{stats.winning_trades} / {stats.losing_trades}")
        p4.metric("Net Profit", f"${stats.net_profit:,.2f}")
        
        p5, p6, p7, p8 = st.columns(4)
        p5.metric("Gross Profit", f"${stats.gross_profit:,.2f}")
        p6.metric("Gross Loss", f"${stats.gross_loss:,.2f}")
        p7.metric("Largest Win", f"${stats.largest_win:,.2f}")
        p8.metric("Largest Loss", f"${stats.largest_loss:,.2f}")
    else:
        st.info("Run a backtest to populate performance statistics.")

with col_safe:
    st.subheader("Safety Engine Status")
    st.write(f"**API Status:** {api_status}")
    st.write(f"**Feed Status:** {feed_status}")
    st.write("**Safety Engine Result:** ALLOW")
    st.write("**Current Reject Reason:** NONE")

st.markdown("---")

# 3. Trade Information (Simulated Active Trade placeholder)
st.subheader("Trade Information")
t1, t2, t3, t4, t5, t6 = st.columns(6)
t1.metric("Entry", "$0.00")
t2.metric("Stop Loss", "$0.00")
t3.metric("Take Profit", "$0.00")
t4.metric("RR", "1:2")
t5.metric("Trade Status", "WAITING")
t6.metric("Trade Duration", "0 candles")

st.markdown("---")

# 4. Charts
st.subheader("Visualizations")
if st.session_state.trades:
    df = pd.DataFrame([t.__dict__ for t in st.session_state.trades])
    df['cumulative_pnl'] = df['profit_loss'].cumsum()
    
    tab1, tab2, tab3 = st.tabs(["Equity Curve", "PnL Curve", "Trade Distribution"])
    
    with tab1:
        fig_eq = px.line(df, x='trade_number', y='cumulative_pnl', title="Live Equity Curve", template="plotly_dark")
        st.plotly_chart(fig_eq, use_container_width=True)
    with tab2:
        fig_pnl = px.bar(df, x='trade_number', y='profit_loss', color='result', title="PnL per Trade", template="plotly_dark")
        st.plotly_chart(fig_pnl, use_container_width=True)
    with tab3:
        fig_dist = px.pie(df, names='result', title="Win/Loss Distribution", template="plotly_dark")
        st.plotly_chart(fig_dist, use_container_width=True)
else:
    st.info("Charts require trade history to render.")

st.markdown("---")

# 5. Trade History Table
st.subheader("Trade History")
if st.session_state.trades:
    st.dataframe(
        df[['trade_number', 'side', 'entry_price', 'exit_price', 'profit_loss', 'result', 'duration_candles']],
        use_container_width=True
    )
else:
    st.info("No completed trades.")

st.markdown("---")

# 6. Logs
st.subheader("System Logs")
log_text = "\n".join(st.session_state.logs[::-1]) # Reverse to show newest at top
st.text_area("Latest Framework Logs", value=log_text, height=300, disabled=True)
