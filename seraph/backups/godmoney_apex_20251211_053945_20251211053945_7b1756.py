#!/usr/bin/env python3
"""
GODMONEY APEX – REAL EXECUTOR (SAFE MODE + LAB THRESHOLD)

- 8x max leverage
- 90% max equity utilization
- Min notional: 2 USDT
- Equity < 20 USDT => LAB MODE: signal is only logged, no real order.
- Signal source: logs/agg_decisions.log lines containing ">>> EXECUTE:".
"""

import os
import json
import time
import re
import logging
from pathlib import Path
from typing import Optional, Tuple

# dotenv first
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / ".env"

print(f"[APEX] Loading .env from: {env_path}")
load_dotenv(env_path)

# then ccxt
import ccxt

# Data Feeds Bridge (Chronos -> Apex) - optional
try:
    from data_feeds_bridge import get_last_tick  # noqa: F401
except Exception:
    get_last_tick = None

# =====================================================================
# CONFIG
# =====================================================================

ROOT = Path(__file__).resolve().parent
LOG_SOURCE = ROOT / "logs" / "agg_decisions.log"
STATE_FILE = ROOT / "logs" / "apex_state.json"

# Risk & execution parameters
MAX_LEVERAGE = 30                    # 8x leverage
MAX_EQUITY_UTIL = 0.90              # use up to 90% of equity
MIN_NOTIONAL = 2.0                  # minimum position size (USDT)

# Lab threshold: below this => live lab, NO REAL ORDER
MIN_EQUITY_FOR_LIVE_TRADING = 20.0  # USDT

POLL_INTERVAL = 3.0                 # seconds (log polling interval)

# Adaptive notional fallback (for margin errors)
FALLBACK_MIN_NOTIONAL = 2.0         # don't go below this
FALLBACK_RETRY_FACTOR = 0.5         # each retry: notional *= 0.5
FALLBACK_MAX_RETRIES = 3            # max attempts per signal


# =====================================================================
# LOGGING
# =====================================================================

def setup_logger() -> logging.Logger:
    logger = logging.getLogger("APEX")
    logger.setLevel(logging.INFO)

    handler = logging.StreamHandler()
    formatter = logging.Formatter(
        "%(asctime)s [APEX] %(levelname)s: %(message)s"
    )
    handler.setFormatter(formatter)

    if not logger.handlers:
        logger.addHandler(handler)

    return logger


logger = setup_logger()


# =====================================================================
# ENV & OKX
# =====================================================================

def str_to_bool(s: Optional[str]) -> bool:
    if s is None:
        return False
    return s.strip().lower() in ("1", "true", "yes", "y", "on")


def init_okx_client() -> ccxt.okx:
    """
    Read OKX credentials from .env and return client.
    """
    api_key = os.getenv("OKX_API_KEY")
    secret = os.getenv("OKX_SECRET")
    password = os.getenv("OKX_PASSWORD")
    use_sandbox = str_to_bool(os.getenv("OKX_USE_SANDBOX"))
    equity_ccy = os.getenv("GODBRAIN_OKX_EQUITY_CCY", "USDT")

    # Debug
    logger.info(f"API Key found: {bool(api_key)}")
    logger.info(f"Secret found: {bool(secret)}")
    logger.info(f"Password found: {bool(password)}")

    if not api_key or not secret or not password:
        raise RuntimeError("OKX API credentials missing in environment (.env).")

    exchange = ccxt.okx({
        "apiKey": api_key,
        "secret": secret,
        "password": password,
        "enableRateLimit": True,
    })

    # Unified account default trade type
    exchange.options["defaultType"] = "swap"
    exchange.set_sandbox_mode(use_sandbox)

    logger.info(
        "OKX client initialized (sandbox=%s, equity_ccy=%s)",
        use_sandbox,
        equity_ccy,
    )

    # Load markets
    exchange.load_markets()
    return exchange


def get_total_equity(exchange: ccxt.okx, ccy: str) -> float:
    """
    Fetch total equity in unified account.
    """
    balance = exchange.fetch_balance()

    total = balance.get("total", {})
    if ccy in total and total[ccy] is not None:
        return float(total[ccy])

    # Fallback
    if ccy in balance and isinstance(balance[ccy], dict):
        val = balance[ccy].get("total") or balance[ccy].get("free") or 0.0
        return float(val)

    return 0.0


# =====================================================================
# STATE MANAGEMENT
# =====================================================================

def load_state(path: Path) -> dict:
    if not path.exists():
        return {}
    try:
        with path.open("r", encoding="utf-8") as f:
            return json.load(f)
    except Exception:
        return {}


def save_state(path: Path, state: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(state, f, ensure_ascii=False, indent=2)
    tmp.replace(path)


# =====================================================================
# SIGNAL PARSING (agg_decisions.log)
# =====================================================================

EXEC_REGEX = re.compile(
    r">>> EXECUTE:\s+(BUY|SELL)\s+([A-Z0-9/:\-]+)\s+\|\s*\$(\d+(?:\.\d+)?)"
)


def get_latest_signal(log_path: Path) -> Optional[Tuple[str, str, str, float, str]]:
    """
    Find the last '>>> EXECUTE:' line and parse it.
    """
    if not log_path.exists():
        return None

    try:
        with log_path.open("r", encoding="utf-8", errors="ignore") as f:
            lines = f.readlines()
    except Exception as e:
        logger.error("Failed to read log file %s: %s", log_path, e)
        return None

    last_exec_index = None
    for i in range(len(lines) - 1, -1, -1):
        if ">>> EXECUTE:" in lines[i]:
            last_exec_index = i
            break

    if last_exec_index is None:
        return None

    exec_line = lines[last_exec_index].strip()
    ts_line = ""
    if last_exec_index > 0:
        ts_line = lines[last_exec_index - 1].strip()

    m = EXEC_REGEX.search(exec_line)
    if not m:
        return None

    side, symbol, notional_str = m.groups()
    requested_notional = float(notional_str)

    signature = f"{ts_line}|{exec_line}"
    return ts_line, side, symbol, requested_notional, signature


# =====================================================================
# ORDER PLACEMENT WITH MARGIN FALLBACK
# =====================================================================

def place_order_with_fallback(
    exchange: ccxt.okx,
    symbol: str,
    side: str,
    equity_ccy: str,
    price: float,
    requested_notional: float,
    max_notional: float,
) -> bool:
    """
    Try to place order; on margin error shrink notional and retry.

    - Starts from min(requested_notional, max_notional), but not below MIN_NOTIONAL.
    - On 51008 / 'Insufficient ... margin' errors, halves notional and retries.
    - Stops when notional would fall below FALLBACK_MIN_NOTIONAL or retries exhausted.
    """
    side_lower = side.lower()
    notional = max(MIN_NOTIONAL, min(requested_notional, max_notional))

    for attempt in range(1, FALLBACK_MAX_RETRIES + 1):
        eff_notional = max(FALLBACK_MIN_NOTIONAL, notional)
        amount = eff_notional / price

        logger.info(
            "TRY %d: %s %s | notional=%.4f %s | price=%.4f | amount=%.8f",
            attempt,
            side,
            symbol,
            eff_notional,
            equity_ccy,
            price,
            amount,
        )

        try:
            order = exchange.create_order(
                symbol,
                type="market",
                side=side_lower,
                amount=exchange.amount_to_precision(symbol, amount),
                params={
                    "tdMode": "cross",
                },
            )
            logger.info(
                "ORDER SUCCESS: id=%s, status=%s",
                order.get("id"),
                order.get("status"),
            )
            return True

        except Exception as e:
            msg = str(e)
            logger.error(
                "ORDER ERROR attempt %d for %s %s: %s",
                attempt,
                side,
                symbol,
                msg,
            )

            # Margin-related errors → shrink notional and retry
            if "51008" in msg or "Insufficient" in msg or "margin" in msg:
                new_notional = eff_notional * FALLBACK_RETRY_FACTOR
                if new_notional < FALLBACK_MIN_NOTIONAL:
                    logger.error(
                        "[APEX] Giving up: not enough margin even for %.2f %s",
                        FALLBACK_MIN_NOTIONAL,
                        equity_ccy,
                    )
                    return False
                logger.warning(
                    "[APEX] Shrinking notional due to margin error: %.2f -> %.2f %s",
                    eff_notional,
                    new_notional,
                    equity_ccy,
                )
                notional = new_notional
                continue

            # Non-margin error → do not retry
            return False

    logger.error(
        "[APEX] Giving up: still insufficient margin after %d attempts.",
        FALLBACK_MAX_RETRIES,
    )
    return False


# =====================================================================
# MAIN LOOP
# =====================================================================

def main() -> None:
    equity_ccy = os.getenv("GODBRAIN_OKX_EQUITY_CCY", "USDT")

    logger.info("=======================================================")
    logger.info("   🧠 GODMONEY APEX – REAL EXECUTOR (SAFE MODE)")
    logger.info("   Max Leverage   : %dx", MAX_LEVERAGE)
    logger.info("   Max Equity Util: %d%%", int(MAX_EQUITY_UTIL * 100))
    logger.info("   Min Notional   : %.2f %s", MIN_NOTIONAL, equity_ccy)
    logger.info(
        "   Lab Threshold  : %.2f %s (equity below => NO REAL ORDER)",
        MIN_EQUITY_FOR_LIVE_TRADING,
        equity_ccy,
    )
    logger.info("   Margin Mode    : CROSS")
    logger.info("   Log Source     : %s", LOG_SOURCE)
    logger.info("   State File     : %s", STATE_FILE)
    logger.info("=======================================================")

    # OKX client init (retry loop)
    exchange = None
    while exchange is None:
        try:
            exchange = init_okx_client()
        except Exception as e:
            logger.error("Failed to initialize OKX client: %s", e)
            time.sleep(7)
        else:
            break

    # Initial equity log
    try:
        equity = get_total_equity(exchange, equity_ccy)
        logger.info("Initial equity: %.4f %s", equity, equity_ccy)
    except Exception as e:
        logger.warning("Couldn't fetch initial equity: %s", e)

    # State
    state = load_state(STATE_FILE)
    last_signature = state.get("last_signature")

    # Main loop
    while True:
        try:
            signal = get_latest_signal(LOG_SOURCE)
            if signal is None:
                time.sleep(POLL_INTERVAL)
                continue

            ts_line, side, symbol, requested_notional, signature = signal

            if signature == last_signature:
                # No new signal
                time.sleep(POLL_INTERVAL)
                continue

            logger.info(
                "NEW SIGNAL: %s %s | requested_notional=%.4f %s",
                side,
                symbol,
                requested_notional,
                equity_ccy,
            )

            # Fetch equity
            try:
                equity = get_total_equity(exchange, equity_ccy)
                logger.info("Current equity: %.4f %s", equity, equity_ccy)
            except Exception as e:
                logger.error("Failed to fetch equity: %s", e)
                time.sleep(POLL_INTERVAL)
                continue

            # =========================================================
            # LAB MODE (no real orders)
            # =========================================================
            if equity < MIN_EQUITY_FOR_LIVE_TRADING:
                logger.warning(
                    "[APEX] LAB MODE: Equity %.2f %s < %.2f %s threshold, "
                    "signal logged only, NO REAL ORDER SENT.",
                    equity,
                    equity_ccy,
                    MIN_EQUITY_FOR_LIVE_TRADING,
                    equity_ccy,
                )
                last_signature = signature
                save_state(STATE_FILE, {"last_signature": last_signature})
                time.sleep(POLL_INTERVAL)
                continue

            # =========================================================
            # REAL ORDER SECTION (SAFE + ADAPTIVE)
            # =========================================================

            max_notional = equity * MAX_EQUITY_UTIL
            effective_notional = max(
                MIN_NOTIONAL,
                min(requested_notional, max_notional),
            )

            logger.info(
                "EFFECTIVE NOTIONAL (pre-fallback): requested=%.4f %s, "
                "capped=%.4f %s (%.0f%% of equity)",
                requested_notional,
                equity_ccy,
                effective_notional,
                equity_ccy,
                MAX_EQUITY_UTIL * 100,
            )

            okx_symbol = symbol

            # Fetch price
            try:
                ticker = exchange.fetch_ticker(okx_symbol)
                price = ticker.get("last") or ticker.get("close")
            except Exception as e:
                logger.error("Failed to fetch ticker for %s: %s", okx_symbol, e)
                time.sleep(POLL_INTERVAL)
                continue

            if not price or price <= 0:
                logger.error("Ticker price is invalid for %s: %s", okx_symbol, price)
                time.sleep(POLL_INTERVAL)
                continue

            # Set leverage – CROSS MARGIN
            try:
                exchange.set_leverage(
                    MAX_LEVERAGE,
                    okx_symbol,
                    params={"mgnMode": "cross"},
                )
                logger.info(
                    "Leverage set: %dx for %s (cross margin)",
                    MAX_LEVERAGE,
                    okx_symbol,
                )
            except Exception as e:
                logger.warning(
                    "WARN: leverage setting problem for %s: %s",
                    okx_symbol,
                    e,
                )

            # Place order with adaptive fallback
            placed = place_order_with_fallback(
                exchange=exchange,
                symbol=okx_symbol,
                side=side,
                equity_ccy=equity_ccy,
                price=price,
                requested_notional=effective_notional,
                max_notional=max_notional,
            )

            if not placed:
                logger.warning(
                    "[APEX] Order could not be placed after fallback attempts."
                )

            # Mark signal as processed
            last_signature = signature
            save_state(STATE_FILE, {"last_signature": last_signature})

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt – executor shutting down.")
            break
        except Exception as e:
            logger.exception("UNCAUGHT ERROR in main loop: %s", e)
            time.sleep(5)


if __name__ == "__main__":
    main()
