"""
safety/safety_engine.py
───────────────────────
Safety Engine to validate trades before execution.

Enforces rules regarding connection state, positions, margin, and session
validity to prevent catastrophic trading errors.
"""

from __future__ import annotations


class SafetyEngine:
    """
    Validates trading state against 10 critical safety checks.
    """

    def __init__(
        self,
        trading_enabled: bool = True,
        max_open_positions: int = 1,
        valid_symbols: list[str] | None = None
    ) -> None:
        self.trading_enabled = trading_enabled
        self.max_open_positions = max_open_positions
        self.valid_symbols = valid_symbols or []

    def validate_execution(
        self,
        symbol: str,
        current_open_positions: int,
        is_api_connected: bool,
        is_market_data_available: bool,
        is_candle_complete: bool,
        is_duplicate_signal: bool,
        balance_available: float,
        required_margin: float,
        is_trading_session_valid: bool = True
    ) -> tuple[str, str]:
        """
        Evaluates the current state against all safety checks.

        Returns:
            A tuple of (Status, Reason).
            Example: ("ALLOW", "ALLOW") or ("REJECT", "API_DISCONNECTED")
        """
        # 1. Trading Enabled
        if not self.trading_enabled:
            return "REJECT", "TRADING_DISABLED"

        # 4. API Connection Status
        if not is_api_connected:
            return "REJECT", "API_DISCONNECTED"

        # 5. Market Data Available
        if not is_market_data_available:
            return "REJECT", "DATA_UNAVAILABLE"

        # 10. Trading Session Valid
        if not is_trading_session_valid:
            return "REJECT", "INVALID_SESSION"

        # 7. Symbol Valid
        if self.valid_symbols and symbol not in self.valid_symbols:
            return "REJECT", "INVALID_SYMBOL"

        # 6. Latest Candle Complete
        if not is_candle_complete:
            return "REJECT", "INCOMPLETE_CANDLE"

        # 3. Duplicate Signal Prevention
        if is_duplicate_signal:
            return "REJECT", "DUPLICATE_SIGNAL"

        # 2. Maximum Open Positions
        if current_open_positions >= self.max_open_positions:
            return "REJECT", "OPEN_POSITION_EXISTS"

        # 8. Account Balance Available
        if balance_available <= 0:
            return "REJECT", "INSUFFICIENT_BALANCE"

        # 9. Required Margin Available
        if balance_available < required_margin:
            return "REJECT", "INSUFFICIENT_MARGIN"

        return "ALLOW", "ALLOW"
