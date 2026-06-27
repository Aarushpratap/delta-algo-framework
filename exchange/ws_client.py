"""
exchange/ws_client.py
─────────────────────
WebSocket client placeholder for the Delta Exchange real-time API.

This module is intentionally left as a skeleton.  It defines the public
interface that future live-trading and market-data streaming code will
implement.

WebSocket docs: https://docs.delta.exchange/#websocket-feed

When ready to implement:
    1. pip install websocket-client
    2. Uncomment the dependency in requirements.txt
    3. Fill in the methods below using the Delta WS protocol
"""

from __future__ import annotations

import logging
from typing import Any, Callable

logger = logging.getLogger(__name__)


class DeltaWebSocketClient:
    """Placeholder — real-time WebSocket client for Delta Exchange.

    Future capabilities:
        • Authenticated private channels (orders, fills, positions)
        • Public channels (orderbook L2, trades, ticker, candles)
        • Auto-reconnect with exponential backoff
        • Heartbeat / pong handling

    Example (future)::

        ws = DeltaWebSocketClient()
        ws.on_message = my_handler
        ws.subscribe(["trade.BTCUSD", "l2_orderbook.BTCUSD"])
        ws.connect()
    """

    # Delta WS endpoints (to be configured via settings)
    _WS_URL_GLOBAL = "wss://socket.delta.exchange"
    _WS_URL_INDIA = "wss://socket.india.delta.exchange"
    _WS_URL_TESTNET = "wss://testnet-socket.delta.exchange"

    def __init__(self) -> None:
        self._connected = False
        self._subscriptions: list[str] = []
        self.on_message: Callable[[dict[str, Any]], None] | None = None
        self.on_error: Callable[[Exception], None] | None = None
        self.on_close: Callable[[], None] | None = None
        logger.info("DeltaWebSocketClient initialised (placeholder).")

    def connect(self) -> None:
        """Establish a WebSocket connection (NOT YET IMPLEMENTED)."""
        raise NotImplementedError(
            "WebSocket support is not yet implemented. "
            "This is a placeholder for future development."
        )

    def subscribe(self, channels: list[str]) -> None:
        """Subscribe to one or more channels (NOT YET IMPLEMENTED)."""
        raise NotImplementedError("WebSocket subscribe not yet implemented.")

    def unsubscribe(self, channels: list[str]) -> None:
        """Unsubscribe from channels (NOT YET IMPLEMENTED)."""
        raise NotImplementedError("WebSocket unsubscribe not yet implemented.")

    def disconnect(self) -> None:
        """Close the WebSocket connection (NOT YET IMPLEMENTED)."""
        raise NotImplementedError("WebSocket disconnect not yet implemented.")

    @property
    def is_connected(self) -> bool:
        """Whether the WebSocket connection is currently active."""
        return self._connected
