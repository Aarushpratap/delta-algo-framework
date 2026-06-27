"""
exchange/rest_client.py
───────────────────────
Pure HTTP transport for the Delta Exchange REST API v2.

This module has ONE responsibility: send an HTTP request and return the
parsed JSON response.  It handles:
    • Session pooling (requests.Session)
    • HMAC-SHA256 auth-header injection
    • Timeout enforcement
    • HTTP / JSON error detection

It does NOT:
    • Know what endpoints exist (paths are passed by callers)
    • Transform response data into domain models
    • Calculate time windows or clamp limits
    • Orchestrate connectivity checks

Higher layers (feeds, execution) call ``client.request(...)`` and own
all business logic.

Reference:
    https://docs.delta.exchange
"""

from __future__ import annotations

import json as _json
import logging
from typing import Any
from urllib.parse import urlencode

import requests

from config.settings import settings
from exchange.auth import get_auth_headers
from exchange.exceptions import DeltaAPIError, DeltaConnectionError

# ── Module logger ────────────────────────────────────────────
logger = logging.getLogger(__name__)


class DeltaRestClient:
    """Stateless HTTP transport for the Delta Exchange API.

    Args:
        api_key:    Override the key from config.settings.
        api_secret: Override the secret from config.settings.
        base_url:   Override the base URL from config.settings.
        timeout:    (connect, read) timeout tuple in seconds.

    Example::

        client = DeltaRestClient()
        data = client.request("GET", "/v2/tickers/BTCUSD")
        print(data["result"]["close"])
    """

    def __init__(
        self,
        api_key: str | None = None,
        api_secret: str | None = None,
        base_url: str | None = None,
        timeout: tuple[int, int] | None = None,
    ) -> None:
        self._api_key = api_key or settings.API_KEY
        self._api_secret = api_secret or settings.API_SECRET
        self._base_url = (base_url or settings.BASE_URL).rstrip("/")
        self._timeout = timeout or settings.REST_TIMEOUT

        # Persistent session for connection pooling
        self._session = requests.Session()
        self._session.headers.update({
            "Accept": "application/json",
            "User-Agent": settings.USER_AGENT,
            "Content-Type": "application/json",
        })

        logger.info("DeltaRestClient initialised → %s", self._base_url)

    # ──────────────────────────────────────────────────────
    # Single public method — the entire API surface
    # ──────────────────────────────────────────────────────

    def request(
        self,
        method: str,
        path: str,
        params: dict[str, Any] | None = None,
        payload: dict[str, Any] | None = None,
        authenticated: bool = False,
    ) -> dict[str, Any]:
        """Send an HTTP request to the Delta Exchange API.

        Args:
            method:        HTTP verb (GET, POST, PUT, DELETE).
            path:          API path starting with ``/v2/…``.
            params:        Query-string key/value pairs.
            payload:       JSON body dict (for POST/PUT).
            authenticated: Whether to sign the request with HMAC headers.

        Returns:
            Parsed JSON response body as a dict.

        Raises:
            DeltaConnectionError: Network / DNS / TLS / timeout failures.
            DeltaAPIError:        Non-2xx status or API ``success: false``.
        """
        url = f"{self._base_url}{path}"
        headers: dict[str, str] = {}

        # ── Build signature inputs ──
        query_string = ""
        if params:
            query_string = "?" + urlencode(params, doseq=True)

        payload_str = ""
        if payload:
            payload_str = _json.dumps(payload, separators=(",", ":"))

        # ── Sign the request ──
        if authenticated:
            if not self._api_key or not self._api_secret:
                raise DeltaConnectionError(
                    "API key/secret not configured. "
                    "Set DELTA_API_KEY and DELTA_API_SECRET in your .env file."
                )
            headers = get_auth_headers(
                api_key=self._api_key,
                api_secret=self._api_secret,
                method=method.upper(),
                path=path,
                query_string=query_string,
                payload=payload_str,
            )

        logger.debug(
            "%s %s | auth=%s | params=%s",
            method.upper(), path, authenticated, params,
        )

        # ── Execute ──
        try:
            response = self._session.request(
                method=method.upper(),
                url=url,
                params=params,
                data=payload_str if payload_str else None,
                headers=headers,
                timeout=self._timeout,
            )
        except requests.exceptions.ConnectionError as exc:
            raise DeltaConnectionError(
                f"Failed to connect to {self._base_url}: {exc}"
            ) from exc
        except requests.exceptions.Timeout as exc:
            raise DeltaConnectionError(
                f"Request timed out ({self._timeout}s): {exc}"
            ) from exc
        except requests.exceptions.RequestException as exc:
            raise DeltaConnectionError(
                f"Unexpected request error: {exc}"
            ) from exc

        # ── Parse JSON ──
        try:
            data = response.json()
        except ValueError:
            raise DeltaAPIError(
                status_code=response.status_code,
                message=f"Non-JSON response body: {response.text[:500]}",
            )

        # ── Check HTTP status ──
        if not response.ok:
            error_msg = data.get("error", {}).get("message", response.text[:300])
            raise DeltaAPIError(
                status_code=response.status_code,
                message=error_msg,
                response=data,
            )

        # ── Check API-level success flag ──
        if isinstance(data, dict) and data.get("success") is False:
            error_detail = data.get("error", data.get("message", "Unknown API error"))
            raise DeltaAPIError(
                status_code=response.status_code,
                message=str(error_detail),
                response=data,
            )

        return data

    # ──────────────────────────────────────────────────────
    # Properties
    # ──────────────────────────────────────────────────────

    @property
    def has_credentials(self) -> bool:
        """True if both API key and secret are configured."""
        return bool(self._api_key and self._api_secret)

    @property
    def base_url(self) -> str:
        """The base URL this client targets."""
        return self._base_url

    # ──────────────────────────────────────────────────────
    # Lifecycle
    # ──────────────────────────────────────────────────────

    def close(self) -> None:
        """Close the underlying HTTP session and release resources."""
        self._session.close()
        logger.info("HTTP session closed.")

    def __enter__(self) -> DeltaRestClient:
        return self

    def __exit__(self, *_: Any) -> None:
        self.close()

    def __repr__(self) -> str:
        return f"DeltaRestClient(base_url={self._base_url!r})"
