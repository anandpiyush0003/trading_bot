# Simplified Trading Bot — Binance Futures Testnet (USDT-M)

A small, structured Python CLI application for placing **MARKET**, **LIMIT**, and
**STOP-LIMIT** orders on Binance Futures Testnet, with full request/response
logging and layered, testable code.

```
trading_bot/
  bot/
    __init__.py
    client.py          # Signed REST client (all HTTP + auth lives here)
    orders.py           # Order building / placement business logic
    validators.py       # CLI input validation (pure functions, unit tested)
    logging_config.py   # Rotating file + console logging setup
  tests/
    test_validators.py  # Unit tests for the validation layer
  logs/                 # trading_bot.log written here at runtime
  cli.py                # CLI entry point (argparse)
  requirements.txt
  .env.example
  README.md
```

## Architecture at a glance

- **`bot/client.py`** — the only module that talks HTTP. Builds Binance's
  HMAC-SHA256 signed requests and translates transport/API errors into two
  clean exception types: `NetworkError` and `BinanceAPIError`.
- **`bot/orders.py`** — translates a validated `OrderRequest` into the exact
  Binance parameter shape (`MARKET` / `LIMIT` / `STOP` order types) and
  normalizes any response into an `OrderResult` for consistent display.
- **`bot/validators.py`** — pure, dependency-free input validation, fully
  unit tested in isolation from HTTP/CLI concerns.
- **`bot/logging_config.py`** — one rotating log file (`logs/trading_bot.log`)
  capturing every request, response, and error at DEBUG level; the console
  only shows INFO+ (clean UX) unless `--verbose` is passed.
- **`cli.py`** — argument parsing and user-facing output only; contains no
  HTTP or signing logic.

## Setup

### 1. Create a Binance Futures Testnet account
1. Go to https://testnet.binancefuture.com and log in with a GitHub account.
2. Once logged in, generate an **API Key** and **Secret** from the site
   (top-right menu → API Key).
3. The testnet gives you a virtual USDT balance automatically — no real funds
   are involved anywhere in this project.

### 2. Install dependencies
Requires Python 3.9+.

```bash
python3 -m venv .venv
source .venv/bin/activate  
pip install -r requirements.txt
```

### 3. Configure credentials
```bash
cp .env.example .env
```
Environment variables read by the app:
```
BINANCE_TESTNET_API_KEY=...
BINANCE_TESTNET_API_SECRET=...
```
(`python-dotenv` auto-loads `.env`; you can also `export` these directly.)

## How to run

**Market order:**
```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01
```

**Limit order:**
```bash
python cli.py --symbol BTCUSDT --side SELL --type LIMIT --quantity 0.01 --price 70000
```

**Stop-Limit order (bonus order type):**
```bash
python cli.py --symbol BTCUSDT --side BUY --type STOP_LIMIT --quantity 0.01 \
    --price 65500 --stop-price 65000
```

**Dry run** (validates and builds the order but does not call the API — useful
to sanity-check input or demo the logging pipeline without live credentials):
```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 --dry-run
```

**Verbose mode** (prints DEBUG-level request/response detail to console too):
```bash
python cli.py --symbol BTCUSDT --side BUY --type MARKET --quantity 0.01 --verbose
```

### Example output
```
--- ORDER REQUEST SUMMARY ---
  Symbol      : BTCUSDT
  Side        : BUY
  Type        : MARKET
  Quantity    : 0.01
-----------------------------

--- ORDER RESPONSE ---
  Order ID       : 3457891234
  Status         : FILLED
  Executed Qty   : 0.010
  Avg Price      : 65423.10
----------------------
SUCCESS: Order placed successfully.
```

### Logs
Every run appends to `logs/trading_bot.log`:
- every outgoing request (with the HMAC signature redacted),
- every raw response,
- every error (validation, API, or network) with a full stack trace on
  unexpected exceptions.

The log file rotates at 5MB (keeping 3 backups) so it stays bounded across
long-running use.

## Running the tests
```bash
python -m pytest tests/ -v
python -m unittest tests.test_validators -v
```

## Assumptions & design notes

- **Order types**: `MARKET`, `LIMIT`, and `STOP_LIMIT` (bonus) are supported.
  `STOP_LIMIT` maps to Binance Futures' `STOP` order type (a limit order that
  activates once the mark price crosses `stopPrice`), the direct testnet
  equivalent of a "stop-limit" order.
- **Time-in-force**: `LIMIT` and `STOP_LIMIT` orders default to `GTC`
  (Good-Til-Canceled), the standard default and the only value required by
  the assignment scope.
- **Symbol validation**: the CLI validates that the symbol looks like a
  USDT-M pair (e.g. `BTCUSDT`) client-side before ever calling the API;
  it does not call `exchangeInfo` to verify the symbol is actually listed,
  to keep the happy path to a single API call per order (the `client.py`
  layer does expose `get_exchange_info()` if this is wanted later).
- **Credentials**: read from environment variables / `.env`, never passed on
  the command line or written to logs (the HMAC signature is explicitly
  redacted before every log line).
- **REST vs. `python-binance`**: implemented with plain `requests` and manual
  HMAC-SHA256 signing rather than the `python-binance` SDK, so the exact
  request/response cycle is transparent, easy to log, and has one fewer
  third-party dependency to pin/debug.
- **Log file deliverable**: this repository ships the code and log
  *machinery* rather than pre-baked log files, since valid orders require a
  live Binance Testnet account and personal API keys that only the account
  owner can generate. Running any of the commands above against your own
  testnet account will produce `logs/trading_bot.log` entries for that
  order — run one `MARKET` and one `LIMIT` order as described above to
  produce the two required log samples.

## Error handling summary

| Failure mode                          | Behavior                                                        |
|----------------------------------------|-------------------------------------------------------------------|
| Invalid/missing CLI input               | `ValidationError` caught in `cli.py`, printed + logged, exit code 1 |
| Missing API credentials                 | Clear error message before any network call is attempted          |
| Binance rejects the order (4xx/5xx)     | `BinanceAPIError` with status/code/message, logged + printed      |
| Network/timeout/DNS failure             | `NetworkError`, logged + printed, no stack trace shown to user    |
| Any other unexpected exception          | Caught at top level, full traceback logged, friendly message shown |
