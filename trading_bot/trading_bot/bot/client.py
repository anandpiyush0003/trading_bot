"""
client.py
---------
Thin, dependency-light REST client for Binance Futures Testnet (USDT-M).

Implemented with plain `requests` + HMAC-SHA256 signing rather than the
python-binance SDK so the request/response cycle is fully transparent and
easy to log/debug. This is the ONLY module that knows about HTTP, signing,
or the Binance API surface -- everything else in the app talks to this
class, not to `requests` directly.

Docs: https://binance-docs.github.io/apidocs/testnet/en/
"""

import hashlib
import hmac
import time
from typing import Any, Dict, Optional
from urllib.parse import urlencode

import requests

from .logging_config import get_logger

logger = get_logger()

DEFAULT_BASE_URL = "https://testnet.binancefuture.com"
RECV_WINDOW_MS = 5000
REQUEST_TIMEOUT_S = 10


class BinanceAPIError(Exception):
    """Raised when Binance returns an error response (4xx/5xx with a Binance error body)."""

    def __init__(self, status_code: int, code: Optional[int], message: str):
        self.status_code = status_code
        self.code = code
        self.message = message
        super().__init__(f"Binance API error [{status_code}] code={code}: {message}")


class NetworkError(Exception):
    """Raised for connectivity issues: timeouts, DNS failures, connection resets, etc."""


class FuturesTestnetClient:
    """
    Minimal signed REST client for Binance USDT-M Futures Testnet.

    Only implements the endpoints this bot needs:
      - GET  /fapi/v1/ping             (connectivity check)
      - GET  /fapi/v1/exchangeInfo     (symbol validation, optional)
      - POST /fapi/v1/order            (place an order)
      - GET  /fapi/v2/account          (optional balance check)
    """

    def __init__(self, api_key: str, api_secret: str, base_url: str = DEFAULT_BASE_URL):
        if not api_key or not api_secret:
            raise ValueError("Both api_key and api_secret must be provided.")
        self.api_key = api_key
        self.api_secret = api_secret
        self.base_url = base_url.rstrip("/")
        self.session = requests.Session()
        self.session.headers.update({"X-MBX-APIKEY": self.api_key})

    # ---------- internal helpers ----------

    def _sign(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Attach timestamp/recvWindow and an HMAC-SHA256 signature to params."""
        params = dict(params)
        params["timestamp"] = int(time.time() * 1000)
        params["recvWindow"] = RECV_WINDOW_MS
        query_string = urlencode(params, doseq=True)
        signature = hmac.new(
            self.api_secret.encode("utf-8"), query_string.encode("utf-8"), hashlib.sha256
        ).hexdigest()
        params["signature"] = signature
        return params

    @staticmethod
    def _redact(params: Dict[str, Any]) -> Dict[str, Any]:
        """Return a copy of params safe to log (never log the signature)."""
        redacted = dict(params)
        if "signature" in redacted:
            redacted["signature"] = "***REDACTED***"
        return redacted

    def _request(
        self, method: str, path: str, params: Optional[Dict[str, Any]] = None, signed: bool = False
    ) -> Dict[str, Any]:
        url = f"{self.base_url}{path}"
        params = params or {}

        if signed:
            params = self._sign(params)

        logger.debug("REQUEST %s %s | params=%s", method, url, self._redact(params))

        try:
            if method == "GET":
                resp = self.session.get(url, params=params, timeout=REQUEST_TIMEOUT_S)
            elif method == "POST":
                resp = self.session.post(url, params=params, timeout=REQUEST_TIMEOUT_S)
            else:
                raise ValueError(f"Unsupported HTTP method: {method}")
        except requests.exceptions.Timeout as exc:
            logger.error("Network timeout calling %s %s: %s", method, url, exc)
            raise NetworkError(f"Request to {path} timed out after {REQUEST_TIMEOUT_S}s.") from exc
        except requests.exceptions.ConnectionError as exc:
            logger.error("Connection error calling %s %s: %s", method, url, exc)
            raise NetworkError(f"Could not connect to {self.base_url}. Check your network/DNS.") from exc
        except requests.exceptions.RequestException as exc:
            logger.error("Unexpected network error calling %s %s: %s", method, url, exc)
            raise NetworkError(str(exc)) from exc

        logger.debug("RESPONSE %s %s | status=%s body=%s", method, url, resp.status_code, resp.text)

        try:
            body = resp.json()
        except ValueError:
            body = {"raw": resp.text}

        if not resp.ok:
            code = body.get("code") if isinstance(body, dict) else None
            msg = body.get("msg") if isinstance(body, dict) else str(body)
            logger.error("Binance API error: status=%s code=%s msg=%s", resp.status_code, code, msg)
            raise BinanceAPIError(resp.status_code, code, msg or "Unknown API error")

        return body

    # ---------- public endpoints ----------

    def ping(self) -> bool:
        """Simple connectivity check against the testnet."""
        self._request("GET", "/fapi/v1/ping")
        return True

    def get_exchange_info(self) -> Dict[str, Any]:
        return self._request("GET", "/fapi/v1/exchangeInfo")

    def get_account(self) -> Dict[str, Any]:
        """Signed account info (balances, positions). Useful for sanity checks."""
        return self._request("GET", "/fapi/v2/account", signed=True)

    def place_order(self, **order_params: Any) -> Dict[str, Any]:
        """
        Place an order via POST /fapi/v1/order.

        order_params should already be fully built/validated (see orders.py),
        e.g.:
            symbol='BTCUSDT', side='BUY', type='MARKET', quantity=0.01
            symbol='BTCUSDT', side='SELL', type='LIMIT', quantity=0.01,
                price=65000, timeInForce='GTC'
        """
        # Drop any None values -- Binance rejects unexpected null params.
        clean_params = {k: v for k, v in order_params.items() if v is not None}
        return self._request("POST", "/fapi/v1/order", params=clean_params, signed=True)
