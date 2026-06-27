"""
exchange/ws_client.py
─────────────────────
Production WebSocket client for the Delta Exchange real-time API.

Responsibilities (this module only):
    • Maintain a persistent, authenticated WebSocket connection.
    • Dispatch inbound messages to registered callbacks.
    • Keep a thread-safe cache of the latest message per channel.
    • Reconnect automatically with exponential back-off.
    • Send periodic pings to detect a dead socket.
    • Never block the caller's thread.

This module does NOT:
    • Know what channels mean (that is the feed/strategy layer's concern).
    • Parse candle, ticker, or orderbook data into domain models.
    • Place orders or manage positions.

WebSocket API reference:
    https://docs.delta.exchange/#websocket-feed

Channels supported by Delta Exchange (examples):
    Public  : v2/ticker.BTCUSD  l2_orderbook.BTCUSD  all_trades.BTCUSD
    Private : own_trades         positions             orders
"""

from __future__ import annotations

import json
import logging
import queue
import re
import threading
import time
from collections import deque
from dataclasses import dataclass, field
from typing import Any, Callable, Dict

import websocket  # websocket-client package

from config.settings import settings
from exchange.auth import get_auth_headers
from exchange.exceptions import DeltaConnectionError

# ── Module logger ─────────────────────────────────────────────────────────────
logger = logging.getLogger(__name__)

# ── Dynamic Configuration (reads from settings, uses defaults if missing) ─────
_HEARTBEAT_INTERVAL: int = getattr(settings, "WS_HEARTBEAT_INTERVAL", 20)
_RECONNECT_BACKOFF_BASE: float = getattr(settings, "WS_RECONNECT_BACKOFF_BASE", 1.0)
_RECONNECT_BACKOFF_MAX: float = getattr(settings, "WS_RECONNECT_BACKOFF_MAX", 30.0)
_MAX_CACHED_MESSAGES: int = getattr(settings, "WS_MAX_CACHED_MESSAGES", 500)
_QUEUE_SIZE: int = getattr(settings, "WS_QUEUE_SIZE", 10000)

# Channel validation regex
_CHANNEL_REGEX = re.compile(r"^[a-zA-Z0-9_/-]+(\.[a-zA-Z0-9_/-]+)*$")

# ── Type aliases ──────────────────────────────────────────────────────────────
MessageCallback = Callable[[dict[str, Any]], None]
LifecycleCallback = Callable[[], None]


# ── Internal data types ───────────────────────────────────────────────────────

@dataclass
class _SubscriptionRequest:
    """Wire payload for subscribe / unsubscribe calls."""
    action: str              # "subscribe" | "unsubscribe"
    channels: list[str]

    def to_dict(self) -> dict[str, Any]:
        return {"type": self.action, "payload": {"channels": self.channels}}


# ── Main client ───────────────────────────────────────────────────────────────

class DeltaWebSocketClient:
    """Production-grade, thread-safe WebSocket client for Delta Exchange.

    Manages its own background threads for receiving, heartbeating, and
    reconnecting.  The caller's thread is never blocked.

    Args:
        ws_url:     Override the WebSocket URL (falls back to ``settings.WS_URL``
                    or the India endpoint if unset).
        api_key:    Override the API key from ``settings``.
        api_secret: Override the API secret from ``settings``.
    """

    _DEFAULT_WS_URL = "wss://socket.india.delta.exchange"

    def __init__(
        self,
        ws_url: str | None = None,
        api_key: str | None = None,
        api_secret: str | None = None,
    ) -> None:
        # ── Configuration ─────────────────────────────────────────────────────
        raw_url = ws_url or getattr(settings, "WS_URL", "") or self._DEFAULT_WS_URL
        self._ws_url: str = raw_url.rstrip("/")
        self._api_key: str = api_key or getattr(settings, "API_KEY", "")
        self._api_secret: str = api_secret or getattr(settings, "API_SECRET", "")

        # ── State ─────────────────────────────────────────────────────────────
        self._ws: websocket.WebSocketApp | None = None
        self._connected: bool = False
        self._was_connected: bool = False      # Track for reconnect lifecycle
        self._closing: bool = False            # set by close() to stop reconnect loop
        
        self._public_subscriptions: list[str] = []
        self._private_subscriptions: list[str] = []
        self._lock: threading.Lock = threading.Lock()

        # ── Metrics ───────────────────────────────────────────────────────────
        self._messages_received: int = 0
        self._messages_dispatched: int = 0
        self._messages_dropped: int = 0

        # ── Message pipeline ──────────────────────────────────────────────────
        self._inbound: queue.Queue[dict[str, Any]] = queue.Queue(maxsize=_QUEUE_SIZE)
        # Latest message cache: channel → deque of messages
        self._latest: dict[str, deque[dict[str, Any]]] = {}
        
        # ── Callbacks ─────────────────────────────────────────────────────────
        self._callbacks: list[MessageCallback] = []
        self.on_connect: list[LifecycleCallback] = []
        self.on_disconnect: list[LifecycleCallback] = []
        self.on_reconnect: list[LifecycleCallback] = []

        # ── Threads ───────────────────────────────────────────────────────────
        self._recv_thread: threading.Thread | None = None
        self._heartbeat_thread: threading.Thread | None = None
        self._dispatch_thread: threading.Thread | None = None

        logger.info(
            "DeltaWebSocketClient initialised → %s (credentials=%s)",
            self._ws_url,
            bool(self._api_key and self._api_secret),
        )

    # ── Public API ────────────────────────────────────────────────────────────

    def connect(self) -> None:
        """Open the WebSocket and start all background threads.

        Returns immediately — connection happens on the background thread.
        Prevents duplicate thread creation.

        Raises:
            DeltaConnectionError: If called while already connected.
        """
        with self._lock:
            if self._connected:
                logger.warning("connect() called but already connected.")
                return
            self._closing = False

        self._start_receive_thread()
        self._start_dispatch_thread()
        self._start_heartbeat_thread()
        logger.info("WebSocket connect initiated.")

    def disconnect(self) -> None:
        """Gracefully close the WebSocket but allow automatic reconnection.

        Use ``close()`` to permanently stop the client.
        """
        self._close_socket()

    def close(self) -> None:
        """Permanently shut down the client and all background threads.

        Blocks until all threads have exited (max ~2 s each).
        """
        logger.info("Closing WebSocket client permanently...")
        with self._lock:
            self._closing = True
            self._connected = False

        self._close_socket()

        # Signal the dispatch thread to exit
        self._inbound.put_nowait({"__sentinel__": True})

        for t in (self._recv_thread, self._heartbeat_thread, self._dispatch_thread):
            if t and t.is_alive():
                t.join(timeout=3)

        logger.info("WebSocket client closed.")

    def _validate_channel(self, channel: str) -> None:
        """Validates the structure of the channel name.
        
        Raises:
            ValueError: If the channel name is invalid.
        """
        if not isinstance(channel, str) or not _CHANNEL_REGEX.match(channel):
            raise ValueError(f"Invalid channel format: {channel}")

    def subscribe(self, channels: list[str], private: bool = False) -> None:
        """Subscribe to one or more Delta Exchange channels.

        Channels are remembered and automatically resubscribed on reconnect.

        Args:
            channels: List of channel strings, e.g. ``["v2/ticker.BTCUSD"]``.
            private:  Whether these channels require authentication.
        """
        if not channels:
            return

        for c in channels:
            self._validate_channel(c)

        with self._lock:
            if private:
                new = [c for c in channels if c not in self._private_subscriptions]
                self._private_subscriptions.extend(new)
            else:
                new = [c for c in channels if c not in self._public_subscriptions]
                self._public_subscriptions.extend(new)

        if new:
            self._send_raw(_SubscriptionRequest("subscribe", new).to_dict())
            logger.info("Subscribed to %s channels: %s", "private" if private else "public", new)

    def unsubscribe(self, channels: list[str], private: bool = False) -> None:
        """Unsubscribe from one or more channels.

        Args:
            channels: Channel strings previously passed to ``subscribe()``.
            private:  Whether these channels were subscribed as private.
        """
        if not channels:
            return

        with self._lock:
            if private:
                self._private_subscriptions = [
                    c for c in self._private_subscriptions if c not in channels
                ]
            else:
                self._public_subscriptions = [
                    c for c in self._public_subscriptions if c not in channels
                ]

        self._send_raw(_SubscriptionRequest("unsubscribe", channels).to_dict())
        logger.info("Unsubscribed from %s channels: %s", "private" if private else "public", channels)

    def send(self, payload: dict[str, Any]) -> None:
        """Send an arbitrary JSON payload over the WebSocket.

        Args:
            payload: Dict that will be serialised to JSON.

        Raises:
            DeltaConnectionError: If the socket is not currently connected.
        """
        if not self._connected:
            raise DeltaConnectionError(
                "Cannot send: WebSocket is not connected."
            )
        self._send_raw(payload)

    def register_callback(self, callback: MessageCallback) -> None:
        """Register a callable to receive every inbound message.

        The callback is invoked on the dispatch thread, not the caller's thread.
        Multiple callbacks can be registered; all are called in registration order.

        Args:
            callback: A callable that accepts a single ``dict`` argument.
        """
        with self._lock:
            self._callbacks.append(callback)
        logger.debug("Callback registered: %s", callback)

    def latest_messages(
        self, channel: str, count: int = 1
    ) -> list[dict[str, Any]]:
        """Return the most recent cached messages for a channel.

        Args:
            channel: The channel key (e.g. ``"v2/ticker.BTCUSD"``).
            count:   Number of messages to return (most recent first).

        Returns:
            List of message dicts, newest first.  Empty list if no messages yet.
        """
        with self._lock:
            buf = self._latest.get(channel)
        if not buf:
            return []
        items = list(buf)
        return list(reversed(items[-count:]))
        
    def stats(self) -> Dict[str, Any]:
        """Return operational metrics for the WebSocket client.
        
        Returns:
            Dict containing queue metrics and message counts.
        """
        with self._lock:
            return {
                "messages_received": self._messages_received,
                "messages_dispatched": self._messages_dispatched,
                "messages_dropped": self._messages_dropped,
                "queue_size": self._inbound.qsize(),
                "connected": self._connected,
            }

    @property
    def is_connected(self) -> bool:
        """Whether the WebSocket is currently in a connected state."""
        return self._connected

    # ── Internal — socket lifecycle ───────────────────────────────────────────

    def _build_ws_app(self) -> websocket.WebSocketApp:
        """Construct a fresh WebSocketApp with bound event handlers."""
        return websocket.WebSocketApp(
            self._ws_url,
            on_open=self._on_open,
            on_message=self._on_message,
            on_error=self._on_error,
            on_close=self._on_close,
        )

    def _close_socket(self) -> None:
        """Send a clean close frame if a socket is open."""
        ws = self._ws
        if ws:
            try:
                ws.close()
            except Exception as exc:
                logger.debug("Exception during socket close (suppressed): %s", exc)

    def _send_raw(self, payload: dict[str, Any]) -> None:
        """Serialise and send a dict; silently drops if socket is gone."""
        ws = self._ws
        if not ws:
            return
        try:
            ws.send(json.dumps(payload))
        except Exception as exc:
            logger.warning("Failed to send payload: %s", exc)

    def _authenticate(self) -> None:
        """Authenticates the WebSocket connection if credentials are available."""
        if not (self._api_key and self._api_secret):
            logger.debug("No API credentials provided; skipping WS authentication.")
            return

        try:
            headers = get_auth_headers(
                api_key=self._api_key,
                api_secret=self._api_secret,
                method="GET",
                path="/live",
            )
            
            auth_payload = {
                "type": "auth",
                "payload": {
                    "api-key": headers["api-key"],
                    "signature": headers["signature"],
                    "timestamp": headers["timestamp"],
                }
            }
            self._send_raw(auth_payload)
            logger.info("WebSocket authentication payload sent.")
            # Note: We do not wait for the ack here; Delta WS processes sequentially.
        except Exception as exc:
            logger.error("WebSocket authentication failed to send: %s", exc)

    # ── Internal — event handlers (called by websocket-client internals) ──────

    def _on_open(self, ws: websocket.WebSocketApp) -> None:
        """Called by websocket-client when the connection is established."""
        with self._lock:
            self._connected = True
            is_reconnect = self._was_connected
            self._was_connected = True
            
        logger.info("WebSocket connected → %s", self._ws_url)

        # Fire lifecycle callbacks
        with self._lock:
            callbacks = list(self.on_reconnect) if is_reconnect else list(self.on_connect)
        for cb in callbacks:
            try:
                cb()
            except Exception as exc:
                logger.error("Lifecycle callback raised an exception: %s", exc, exc_info=True)

        # 1. Authenticate first (required for private subscriptions)
        self._authenticate()

        # 2. Restore private subscriptions
        with self._lock:
            priv_channels = list(self._private_subscriptions)
        if priv_channels:
            self._send_raw(_SubscriptionRequest("subscribe", priv_channels).to_dict())
            logger.info("Restored private channels: %s", priv_channels)

        # 3. Restore public subscriptions
        with self._lock:
            pub_channels = list(self._public_subscriptions)
        if pub_channels:
            self._send_raw(_SubscriptionRequest("subscribe", pub_channels).to_dict())
            logger.info("Restored public channels: %s", pub_channels)

    def _on_message(self, ws: websocket.WebSocketApp, raw: str) -> None:
        """Called by websocket-client for every inbound text frame."""
        with self._lock:
            self._messages_received += 1

        try:
            msg: dict[str, Any] = json.loads(raw)
        except json.JSONDecodeError:
            logger.warning("Received non-JSON frame (ignored): %s", raw[:200])
            return

        # Cache by channel type field if present
        channel = msg.get("type") or msg.get("channel") or "__unknown__"
        with self._lock:
            if channel not in self._latest:
                self._latest[channel] = deque(maxlen=_MAX_CACHED_MESSAGES)
            self._latest[channel].append(msg)

        # Enqueue for dispatch thread (non-blocking; drop if backpressured)
        try:
            self._inbound.put_nowait(msg)
        except queue.Full:
            with self._lock:
                self._messages_dropped += 1
            logger.warning("Inbound queue full — message dropped (channel=%s)", channel)

    def _on_error(self, ws: websocket.WebSocketApp, error: Exception) -> None:
        """Called by websocket-client on socket error."""
        logger.error("WebSocket error: %s", error)

    def _on_close(
        self,
        ws: websocket.WebSocketApp,
        close_status_code: int | None,
        close_msg: str | None,
    ) -> None:
        """Called by websocket-client when the connection is lost."""
        with self._lock:
            self._connected = False
            
        logger.warning(
            "WebSocket closed (code=%s msg=%s).", close_status_code, close_msg
        )
        
        with self._lock:
            callbacks = list(self.on_disconnect)
        for cb in callbacks:
            try:
                cb()
            except Exception as exc:
                logger.error("Disconnect callback raised an exception: %s", exc, exc_info=True)

    # ── Internal — background threads ─────────────────────────────────────────

    def _start_receive_thread(self) -> None:
        """Spawn the thread that runs WebSocketApp.run_forever (with reconnect loop)."""
        with self._lock:
            if self._recv_thread and self._recv_thread.is_alive():
                return
            self._recv_thread = threading.Thread(
                target=self._receive_loop,
                name="ws-recv",
                daemon=True,
            )
            self._recv_thread.start()

    def _start_heartbeat_thread(self) -> None:
        """Spawn the periodic ping thread."""
        with self._lock:
            if self._heartbeat_thread and self._heartbeat_thread.is_alive():
                return
            self._heartbeat_thread = threading.Thread(
                target=self._heartbeat_loop,
                name="ws-heartbeat",
                daemon=True,
            )
            self._heartbeat_thread.start()

    def _start_dispatch_thread(self) -> None:
        """Spawn the thread that drains the inbound queue and calls callbacks."""
        with self._lock:
            if self._dispatch_thread and self._dispatch_thread.is_alive():
                return
            self._dispatch_thread = threading.Thread(
                target=self._dispatch_loop,
                name="ws-dispatch",
                daemon=True,
            )
            self._dispatch_thread.start()

    def _receive_loop(self) -> None:
        """
        Reconnect loop with exponential back-off.

        Runs ``WebSocketApp.run_forever()`` in a tight loop.  Each time the
        socket drops (error or clean close) we sleep for an increasing delay
        before attempting a new connection — unless ``close()`` was called.
        """
        backoff = _RECONNECT_BACKOFF_BASE

        while True:
            with self._lock:
                if self._closing:
                    logger.info("Receive loop exiting (client is closing).")
                    return

            logger.info("Attempting WebSocket connection to %s …", self._ws_url)
            try:
                self._ws = self._build_ws_app()
                # run_forever blocks until the connection drops
                self._ws.run_forever(
                    ping_interval=0,  # we handle pings manually
                    ping_timeout=None,
                    skip_utf8_validation=True,
                )
            except Exception as exc:
                logger.error("run_forever raised unexpectedly: %s", exc)

            # Connection has dropped
            with self._lock:
                self._connected = False
                if self._closing:
                    logger.info("Receive loop exiting after socket close.")
                    return

            logger.warning(
                "WebSocket disconnected. Reconnecting in %.1f s …", backoff
            )
            # Respect close() even while sleeping
            deadline = time.monotonic() + backoff
            while time.monotonic() < deadline:
                with self._lock:
                    if self._closing:
                        return
                time.sleep(0.25)

            # Increase backoff (capped)
            backoff = min(backoff * 2, _RECONNECT_BACKOFF_MAX)

    def _heartbeat_loop(self) -> None:
        """
        Send a ping every ``_HEARTBEAT_INTERVAL`` seconds.

        Detects a dead socket: if a ping fails, close the socket so the
        reconnect loop picks it up.
        """
        while True:
            # Sleep in small increments to detect close() promptly
            for _ in range(_HEARTBEAT_INTERVAL * 4):
                with self._lock:
                    if self._closing:
                        logger.info("Heartbeat loop exiting.")
                        return
                time.sleep(0.25)

            if not self._connected:
                continue

            ws = self._ws
            if not ws:
                continue

            try:
                ws.sock.ping()  # type: ignore[union-attr]
                logger.debug("Heartbeat ping sent.")
            except Exception as exc:
                logger.warning(
                    "Heartbeat ping failed (%s) — triggering reconnect.", exc
                )
                self._close_socket()

    def _dispatch_loop(self) -> None:
        """
        Drain the inbound queue and fan-out to registered callbacks.

        Runs on a dedicated thread so slow callbacks cannot stall the receive
        thread.  Exits when it dequeues the ``__sentinel__`` message placed by
        ``close()``.
        """
        while True:
            try:
                msg = self._inbound.get(timeout=1.0)
            except queue.Empty:
                with self._lock:
                    if self._closing:
                        return
                continue

            if msg.get("__sentinel__"):
                logger.info("Dispatch loop exiting.")
                return
                
            with self._lock:
                self._messages_dispatched += 1
                callbacks = list(self._callbacks)

            for cb in callbacks:
                try:
                    cb(msg)
                except Exception as exc:
                    logger.error(
                        "Callback %s raised an exception: %s", cb, exc, exc_info=True
                    )

    # ── Dunder helpers ────────────────────────────────────────────────────────

    def __enter__(self) -> DeltaWebSocketClient:
        self.connect()
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        state = "connected" if self._connected else "disconnected"
        return f"DeltaWebSocketClient({state}, url={self._ws_url!r})"
