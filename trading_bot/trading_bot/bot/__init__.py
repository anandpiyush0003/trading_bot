"""
trading_bot.bot
================
Core package for the Binance Futures Testnet trading bot.

Modules:
    client.py         -> Low-level signed REST client for Binance Futures Testnet
    orders.py          -> Order placement / order-building logic (business layer)
    validators.py       -> CLI input validation helpers
    logging_config.py  -> Central logging configuration (console + rotating file)
"""

__version__ = "1.0.0"
