"""
orders.py
---------
Business logic for turning validated CLI input into a Binance Futures
order request, submitting it, and normalizing the response for display.

Kept separate from client.py (raw HTTP) and cli.py (argument parsing/UI)
so each layer has a single responsibility.
"""

from dataclasses import dataclass
from typing import Any, Dict, Optional

from .client import BinanceAPIError, FuturesTestnetClient, NetworkError
from .logging_config import get_logger

logger = get_logger()


@dataclass
class OrderRequest:
    """Normalized, validated representation of an order the user wants to place."""

    symbol: str
    side: str  # BUY / SELL
    order_type: str  # MARKET / LIMIT / STOP_LIMIT
    quantity: float
    price: Optional[float] = None
    stop_price: Optional[float] = None

    def to_binance_params(self) -> Dict[str, Any]:
        """Translate to the exact parameter names Binance's /fapi/v1/order expects."""
        params: Dict[str, Any] = {
            "symbol": self.symbol,
            "side": self.side,
            "quantity": self.quantity,
        }

        if self.order_type == "MARKET":
            params["type"] = "MARKET"

        elif self.order_type == "LIMIT":
            params["type"] = "LIMIT"
            params["price"] = self.price
            params["timeInForce"] = "GTC"  # Good-Til-Canceled: standard default for limit orders

        elif self.order_type == "STOP_LIMIT":
            # Binance Futures calls this order type STOP; it becomes a LIMIT
            # order once the mark price crosses stopPrice.
            params["type"] = "STOP"
            params["price"] = self.price
            params["stopPrice"] = self.stop_price
            params["timeInForce"] = "GTC"

        else:
            raise ValueError(f"Unsupported order type: {self.order_type}")

        return params

    def summary(self) -> str:
        parts = [
            f"symbol={self.symbol}",
            f"side={self.side}",
            f"type={self.order_type}",
            f"quantity={self.quantity}",
        ]
        if self.price is not None:
            parts.append(f"price={self.price}")
        if self.stop_price is not None:
            parts.append(f"stopPrice={self.stop_price}")
        return " | ".join(parts)


@dataclass
class OrderResult:
    """Normalized order outcome, regardless of order type, for consistent display."""

    success: bool
    order_id: Optional[int] = None
    status: Optional[str] = None
    executed_qty: Optional[str] = None
    avg_price: Optional[str] = None
    raw_response: Optional[Dict[str, Any]] = None
    error_message: Optional[str] = None


class OrderService:
    """High-level API: build an OrderRequest, submit it, return a normalized OrderResult."""

    def __init__(self, client: FuturesTestnetClient):
        self.client = client

    def place_order(self, request: OrderRequest) -> OrderResult:
        logger.info("Submitting order: %s", request.summary())

        params = request.to_binance_params()

        try:
            response = self.client.place_order(**params)
        except BinanceAPIError as exc:
            logger.error("Order rejected by Binance: %s", exc)
            return OrderResult(success=False, error_message=str(exc))
        except NetworkError as exc:
            logger.error("Order failed due to network error: %s", exc)
            return OrderResult(success=False, error_message=str(exc))

        logger.info(
            "Order accepted: orderId=%s status=%s executedQty=%s",
            response.get("orderId"),
            response.get("status"),
            response.get("executedQty"),
        )

        return OrderResult(
            success=True,
            order_id=response.get("orderId"),
            status=response.get("status"),
            executed_qty=response.get("executedQty"),
            avg_price=response.get("avgPrice"),
            raw_response=response,
        )
