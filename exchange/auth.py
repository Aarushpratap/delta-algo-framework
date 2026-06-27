"""
exchange/auth.py
────────────────
HMAC-SHA256 request signing for the Delta Exchange REST API v2.

The Delta API requires three auth headers on private endpoints:
    api-key     → your API key
    timestamp   → current unix epoch in *seconds* (string)
    signature   → HMAC-SHA256( secret, METHOD + TIMESTAMP + PATH [+ QUERY] [+ BODY] )

Signatures must reach the server within 5 seconds of generation.

Reference:
    https://docs.delta.exchange/#authentication
"""

from __future__ import annotations

import hashlib
import hmac
import time


def generate_signature(secret: str, message: str) -> str:
    """Create an HMAC-SHA256 hex digest.

    Args:
        secret:  The API secret key.
        message: The pre-image string (method + timestamp + path + query + payload).

    Returns:
        Lowercase hex string of the HMAC-SHA256 digest.
    """
    return hmac.new(
        key=secret.encode("utf-8"),
        msg=message.encode("utf-8"),
        digestmod=hashlib.sha256,
    ).hexdigest()


def get_auth_headers(
    api_key: str,
    api_secret: str,
    method: str,
    path: str,
    query_string: str = "",
    payload: str = "",
) -> dict[str, str]:
    """Build the full set of authentication headers for a Delta API request.

    Args:
        api_key:      Your Delta Exchange API key.
        api_secret:   Your Delta Exchange API secret.
        method:       HTTP method (GET, POST, PUT, DELETE) — uppercase.
        path:         Request path starting with /v2/… (no host).
        query_string: URL query string including the leading '?' if present.
        payload:      JSON-serialised request body (empty string for GET).

    Returns:
        Dict with api-key, timestamp, signature, User-Agent, and Content-Type.
    """
    timestamp = str(int(time.time()))

    # Signature data = METHOD + TIMESTAMP + PATH + QUERY_STRING + PAYLOAD
    signature_data = method.upper() + timestamp + path + query_string + payload
    signature = generate_signature(api_secret, signature_data)

    return {
        "api-key": api_key,
        "timestamp": timestamp,
        "signature": signature,
        "User-Agent": "delta-algo-client/1.0",
        "Content-Type": "application/json",
    }
