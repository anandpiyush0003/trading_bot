"""
Unit tests for bot/validators.py.

Run with:  python -m pytest tests/ -v
(or, without pytest installed:  python -m unittest tests.test_validators -v)
"""

import os
import sys
import unittest

sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from bot.validators import (  # noqa: E402
    ValidationError,
    validate_order_args,
    validate_price,
    validate_quantity,
    validate_side,
    validate_symbol,
)


class Args:
    """Simple stand-in for argparse.Namespace in tests."""

    def __init__(self, symbol, side, type, quantity, price=None, stop_price=None):
        self.symbol = symbol
        self.side = side
        self.type = type
        self.quantity = quantity
        self.price = price
        self.stop_price = stop_price


class TestSymbolValidation(unittest.TestCase):
    def test_valid_symbol(self):
        self.assertEqual(validate_symbol("btcusdt"), "BTCUSDT")

    def test_empty_symbol_raises(self):
        with self.assertRaises(ValidationError):
            validate_symbol("")

    def test_non_usdt_pair_rejected(self):
        with self.assertRaises(ValidationError):
            validate_symbol("BTCBUSD")


class TestSideValidation(unittest.TestCase):
    def test_valid_sides(self):
        self.assertEqual(validate_side("buy"), "BUY")
        self.assertEqual(validate_side("SELL"), "SELL")

    def test_invalid_side_raises(self):
        with self.assertRaises(ValidationError):
            validate_side("HOLD")


class TestQuantityValidation(unittest.TestCase):
    def test_valid_quantity(self):
        self.assertEqual(validate_quantity("0.01"), 0.01)

    def test_zero_quantity_raises(self):
        with self.assertRaises(ValidationError):
            validate_quantity("0")

    def test_negative_quantity_raises(self):
        with self.assertRaises(ValidationError):
            validate_quantity("-1")

    def test_non_numeric_quantity_raises(self):
        with self.assertRaises(ValidationError):
            validate_quantity("abc")


class TestPriceValidation(unittest.TestCase):
    def test_price_required_for_limit(self):
        with self.assertRaises(ValidationError):
            validate_price(None, required=True)

    def test_price_optional_for_market(self):
        self.assertIsNone(validate_price(None, required=False))

    def test_valid_price(self):
        self.assertEqual(validate_price("65000", required=True), 65000.0)


class TestFullOrderValidation(unittest.TestCase):
    def test_valid_market_order(self):
        args = Args(symbol="BTCUSDT", side="BUY", type="MARKET", quantity="0.01")
        result = validate_order_args(args)
        self.assertEqual(result["symbol"], "BTCUSDT")
        self.assertIsNone(result["price"])

    def test_valid_limit_order(self):
        args = Args(symbol="ETHUSDT", side="SELL", type="LIMIT", quantity="0.5", price="3500")
        result = validate_order_args(args)
        self.assertEqual(result["price"], 3500.0)

    def test_limit_order_missing_price_fails(self):
        args = Args(symbol="ETHUSDT", side="SELL", type="LIMIT", quantity="0.5")
        with self.assertRaises(ValidationError):
            validate_order_args(args)

    def test_stop_limit_missing_stop_price_fails(self):
        args = Args(symbol="BTCUSDT", side="BUY", type="STOP_LIMIT", quantity="0.01", price="65500")
        with self.assertRaises(ValidationError):
            validate_order_args(args)


if __name__ == "__main__":
    unittest.main()
