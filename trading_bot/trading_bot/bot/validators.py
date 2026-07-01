"""
validators.py
-------------
Pure, dependency-free validation helpers for CLI input.

Kept separate from the CLI and API layers so validation rules can be
unit-tested in isolation and reused (e.g. by a future GUI or REST wrapper).
"""

import re
from typing import Optional

VALID_SIDES = {"BUY", "SELL"}
VALID_ORDER_TYPES = {"MARKET", "LIMIT", "STOP_LIMIT"}

# Reasonable symbol pattern for Binance USDT-M perpetuals, e.g. BTCUSDT, ETHUSDT
_SYMBOL_RE = re.compile(r"^[A-Z0-9]{2,15}USDT$")


class ValidationError(ValueError):
    """Raised when user-supplied CLI input fails validation."""


def validate_symbol(symbol: str) -> str:
    if not symbol:
        raise ValidationError("Symbol is required (e.g. BTCUSDT).")
    symbol = symbol.strip().upper()
    if not _SYMBOL_RE.match(symbol):
        raise ValidationError(
            f"Invalid symbol '{symbol}'. Expected a USDT-M pair like 'BTCUSDT' or 'ETHUSDT'."
        )
    return symbol


def validate_side(side: str) -> str:
    if not side:
        raise ValidationError("Side is required (BUY or SELL).")
    side = side.strip().upper()
    if side not in VALID_SIDES:
        raise ValidationError(f"Invalid side '{side}'. Must be one of {sorted(VALID_SIDES)}.")
    return side


def validate_order_type(order_type: str) -> str:
    if not order_type:
        raise ValidationError("Order type is required (MARKET, LIMIT, or STOP_LIMIT).")
    order_type = order_type.strip().upper()
    if order_type not in VALID_ORDER_TYPES:
        raise ValidationError(
            f"Invalid order type '{order_type}'. Must be one of {sorted(VALID_ORDER_TYPES)}."
        )
    return order_type


def validate_quantity(quantity) -> float:
    try:
        qty = float(quantity)
    except (TypeError, ValueError):
        raise ValidationError(f"Quantity must be a number, got '{quantity}'.")
    if qty <= 0:
        raise ValidationError(f"Quantity must be greater than 0, got {qty}.")
    return qty


def validate_price(price, required: bool) -> Optional[float]:
    if price is None or price == "":
        if required:
            raise ValidationError("Price is required for LIMIT / STOP_LIMIT orders.")
        return None
    try:
        p = float(price)
    except (TypeError, ValueError):
        raise ValidationError(f"Price must be a number, got '{price}'.")
    if p <= 0:
        raise ValidationError(f"Price must be greater than 0, got {p}.")
    return p


def validate_stop_price(stop_price, required: bool) -> Optional[float]:
    if stop_price is None or stop_price == "":
        if required:
            raise ValidationError("Stop price is required for STOP_LIMIT orders.")
        return None
    try:
        sp = float(stop_price)
    except (TypeError, ValueError):
        raise ValidationError(f"Stop price must be a number, got '{stop_price}'.")
    if sp <= 0:
        raise ValidationError(f"Stop price must be greater than 0, got {sp}.")
    return sp


def validate_order_args(args) -> dict:
    """
    Validate an argparse.Namespace (or any object with the expected attributes)
    and return a clean dict of normalized order parameters.

    Raises:
        ValidationError: on any invalid field, with a message describing the problem.
    """
    symbol = validate_symbol(args.symbol)
    side = validate_side(args.side)
    order_type = validate_order_type(args.type)
    quantity = validate_quantity(args.quantity)

    price = validate_price(getattr(args, "price", None), required=(order_type in ("LIMIT", "STOP_LIMIT")))
    stop_price = validate_stop_price(
        getattr(args, "stop_price", None), required=(order_type == "STOP_LIMIT")
    )

    return {
        "symbol": symbol,
        "side": side,
        "order_type": order_type,
        "quantity": quantity,
        "price": price,
        "stop_price": stop_price,
    }
