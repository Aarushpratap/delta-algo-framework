"""
exchange/exceptions.py
──────────────────────
Custom exception hierarchy for the Delta Exchange API layer.

These exceptions are raised exclusively by the exchange/ package and
caught by higher layers (feeds, execution, engine).  Keeping them in a
dedicated module prevents circular imports and gives every layer a
stable error contract to depend on.
"""

from __future__ import annotations

from typing import Any


class DeltaAPIError(Exception):
    """Raised when the Delta Exchange API returns a non-success response.

    Attributes:
        status_code: HTTP status code from the response.
        message:     Human-readable error description.
        response:    Full parsed JSON body (if available).
    """

    def __init__(
        self,
        status_code: int,
        message: str,
        response: dict[str, Any] | None = None,
    ) -> None:
        self.status_code = status_code
        self.message = message
        self.response = response
        super().__init__(f"[HTTP {status_code}] {message}")


class DeltaConnectionError(Exception):
    """Raised when the client cannot reach the Delta Exchange servers.

    Covers DNS failures, TLS errors, socket timeouts, and any other
    transport-level issue that prevents a request from completing.
    """
