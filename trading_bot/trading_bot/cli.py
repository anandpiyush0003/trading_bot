#!/usr/bin/env python3
"""
cli.py
------
Command-line entry point for the Simplified Trading Bot.

Usage examples:

    # Market order
    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01

    # Limit order
    python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 70000

    # Stop-Limit order (bonus order type)
    python cli.py --symbol BTCUSDT --side BUY --type STOP_LIMIT --quantity 0.01 \\
        --price 65500 --stop-price 65000

    # Dry run (no network call, no real credentials needed) - great for demoing logging
    python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 --dry-run

Credentials are read from environment variables (or a local .env file):
    BINANCE_TESTNET_API_KEY
    BINANCE_TESTNET_API_SECRET
"""

import argparse
import os
import sys

from bot.client import DEFAULT_BASE_URL, FuturesTestnetClient
from bot.logging_config import get_logger, setup_logging
from bot.orders import OrderRequest, OrderService
from bot.validators import ValidationError, validate_order_args

try:
    from dotenv import load_dotenv

    load_dotenv()
except ImportError:
    # python-dotenv is optional; env vars can be set directly in the shell instead.
    pass


def build_arg_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="trading-bot",
        description="Place MARKET / LIMIT / STOP_LIMIT orders on Binance Futures Testnet (USDT-M).",
    )
    parser.add_argument("--symbol", required=True, help="Trading pair, e.g. BTCUSDT")
    parser.add_argument("--side", required=True, choices=["BUY", "SELL", "buy", "sell"], help="Order side")
    parser.add_argument(
        "--type",
        required=True,
        choices=["MARKET", "LIMIT", "STOP_LIMIT", "market", "limit", "stop_limit"],
        help="Order type",
    )
    parser.add_argument("--quantity", required=True, help="Order quantity, e.g. 0.01")
    parser.add_argument("--price", required=False, help="Limit price (required for LIMIT / STOP_LIMIT)")
    parser.add_argument(
        "--stop-price", dest="stop_price", required=False, help="Stop trigger price (required for STOP_LIMIT)"
    )
    parser.add_argument(
        "--base-url",
        default=DEFAULT_BASE_URL,
        help=f"API base URL (default: {DEFAULT_BASE_URL})",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Validate and build the order but do NOT send it to Binance. Useful for testing/logging demos.",
    )
    parser.add_argument("--verbose", action="store_true", help="Print DEBUG-level logs to console too.")
    return parser


def print_summary(request: OrderRequest) -> None:
    print("\n--- ORDER REQUEST SUMMARY ---")
    print(f"  Symbol      : {request.symbol}")
    print(f"  Side        : {request.side}")
    print(f"  Type        : {request.order_type}")
    print(f"  Quantity    : {request.quantity}")
    if request.price is not None:
        print(f"  Price       : {request.price}")
    if request.stop_price is not None:
        print(f"  Stop Price  : {request.stop_price}")
    print("-----------------------------\n")


def print_result(result) -> None:
    print("--- ORDER RESPONSE ---")
    if result.success:
        print(f"  Order ID       : {result.order_id}")
        print(f"  Status         : {result.status}")
        print(f"  Executed Qty   : {result.executed_qty}")
        print(f"  Avg Price      : {result.avg_price}")
        print("----------------------")
        print("SUCCESS: Order placed successfully.\n")
    else:
        print("----------------------")
        print(f"FAILED: {result.error_message}\n")


def main(argv=None) -> int:
    parser = build_arg_parser()
    args = parser.parse_args(argv)

    logger = setup_logging(verbose=args.verbose)

    # ---- 1. Validate input ----
    try:
        # Normalize case before validation for convenience (BUY/buy both work)
        args.side = args.side.upper()
        args.type = args.type.upper()
        clean = validate_order_args(args)
    except ValidationError as exc:
        logger.error("Input validation failed: %s", exc)
        print(f"Invalid input: {exc}")
        return 1

    request = OrderRequest(
        symbol=clean["symbol"],
        side=clean["side"],
        order_type=clean["order_type"],
        quantity=clean["quantity"],
        price=clean["price"],
        stop_price=clean["stop_price"],
    )
    print_summary(request)

    if args.dry_run:
        logger.info("DRY RUN enabled: order will be built and validated but not sent. %s", request.summary())
        print("DRY RUN: order was NOT sent to Binance (no network call made).")
        print("This mode is for testing the CLI/validation/logging pipeline offline.\n")
        return 0

    # ---- 2. Load credentials ----
    api_key = os.getenv("BINANCE_TESTNET_API_KEY")
    api_secret = os.getenv("BINANCE_TESTNET_API_SECRET")

    if not api_key or not api_secret:
        logger.error("Missing API credentials in environment.")
        print(
            "ERROR: BINANCE_TESTNET_API_KEY and BINANCE_TESTNET_API_SECRET must be set "
            "(env vars or a .env file). See README.md for setup steps."
        )
        return 1

    # ---- 3. Submit order ----
    try:
        client = FuturesTestnetClient(api_key=api_key, api_secret=api_secret, base_url=args.base_url)
        service = OrderService(client)
        result = service.place_order(request)
    except Exception as exc:  # noqa: BLE001 - top-level safety net, fully logged
        logger.exception("Unexpected error while placing order: %s", exc)
        print(f"FAILED: Unexpected error: {exc}")
        return 1

    print_result(result)
    return 0 if result.success else 1


if __name__ == "__main__":
    sys.exit(main())
