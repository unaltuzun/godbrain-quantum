#!/usr/bin/env python3
"""
GODMONEY APEX – REAL EXECUTOR (SAFE MODE + LAB THRESHOLD)

- 5x max leverage
- 50% max equity utilization
- Min notional: 2 USDT
- Equity < 20 USDT => LAB MODE: sinyal sadece loglanır, OKX'e emir gönderilmez.
- Sinyal kaynağı: logs/agg_decisions.log içindeki ">>> EXECUTE:" satırları.
"""

import os
import json
import time
import re
import logging
from pathlib import Path
from typing import Optional, Tuple

# ÖNCE dotenv import ve load
from dotenv import load_dotenv

BASE_DIR = Path(__file__).resolve().parent
env_path = BASE_DIR / ".env"

print(f"[APEX] Loading .env from: {env_path}")
load_dotenv(env_path)

# SONRA ccxt import
import ccxt

# Data Feeds Bridge (Chronos -> Apex) - opsiyonel
try:
    from data_feeds_bridge import get_last_tick
except Exception:
    get_last_tick = None

# =====================================================================
# KONFİG
# =====================================================================

ROOT = Path(__file__).resolve().parent
LOG_SOURCE = ROOT / "logs" / "agg_decisions.log"
STATE_FILE = ROOT / "logs" / "apex_state.json"

# Risk & execution parametreleri
MAX_LEVERAGE = 5                   # 5x kaldıraç
MAX_EQUITY_UTIL = 0.70             # %50 equity kullanımı
MIN_NOTIONAL = 2.0                 # minimum pozisyon büyüklüğü (USDT)

# Lab threshold: bunun altı sadece "canlı lab", gerçek emir YOK
MIN_EQUITY_FOR_LIVE_TRADING = 20.0  # USDT

POLL_INTERVAL = 3.0                # saniye (log tarama periyodu)


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
    .env içinden OKX bilgilerini okuyup client döndürür.
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

    # Unified account için varsayılan trade modu
    exchange.options["defaultType"] = "swap"
    exchange.set_sandbox_mode(use_sandbox)

    logger.info(
        "OKX client initialized (sandbox=%s, equity_ccy=%s)",
        use_sandbox,
        equity_ccy,
    )

    # Piyasaları yükle
    exchange.load_markets()
    return exchange


def get_total_equity(exchange: ccxt.okx, ccy: str) -> float:
    """
    Unified account'ta toplam equity'yi çeker.
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
# SİNYAL PARSING (agg_decisions.log)
# =====================================================================

EXEC_REGEX = re.compile(
    r">>> EXECUTE:\s+(BUY|SELL)\s+([A-Z0-9/:\-]+)\s+\|\s*\$(\d+(?:\.\d+)?)"
)


def get_latest_signal(log_path: Path) -> Optional[Tuple[str, str, str, float, str]]:
    """
    agg_decisions.log içindeki SON ">>> EXECUTE:" satırını bulur.
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
# ANA LOOP
# =====================================================================

def main() -> None:
    equity_ccy = os.getenv("GODBRAIN_OKX_EQUITY_CCY", "USDT")

    logger.info("=======================================================")
    logger.info("   🧠 GODMONEY APEX – REAL EXECUTOR (SAFE MODE)")
    logger.info("   Max Leverage   : %dx", MAX_LEVERAGE)
    logger.info("   Max Equity Util: %d%%", int(MAX_EQUITY_UTIL * 100))
    logger.info("   Min Notional   : %.2f %s", MIN_NOTIONAL, equity_ccy)
    logger.info("   Lab Threshold  : %.2f %s (equity altı => EMİR YOK)", MIN_EQUITY_FOR_LIVE_TRADING, equity_ccy)
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

    # İlk equity log'u
    try:
        equity = get_total_equity(exchange, equity_ccy)
        logger.info("Initial equity: %.4f %s", equity, equity_ccy)
    except Exception as e:
        logger.warning("Couldn't fetch initial equity: %s", e)

    # State
    state = load_state(STATE_FILE)
    last_signature = state.get("last_signature")

    # Ana döngü
    while True:
        try:
            # En son sinyali çek (tick kontrolünü kaldırdık - gereksiz)
            signal = get_latest_signal(LOG_SOURCE)
            if signal is None:
                time.sleep(POLL_INTERVAL)
                continue

            ts_line, side, symbol, requested_notional, signature = signal

            if signature == last_signature:
                # Yeni sinyal yok
                time.sleep(POLL_INTERVAL)
                continue

            logger.info(
                "NEW SIGNAL: %s %s | requested_notional=%.4f %s",
                side,
                symbol,
                requested_notional,
                equity_ccy,
            )

            # Equity çek
            try:
                equity = get_total_equity(exchange, equity_ccy)
                logger.info("Current equity: %.4f %s", equity, equity_ccy)
            except Exception as e:
                logger.error("Failed to fetch equity: %s", e)
                time.sleep(POLL_INTERVAL)
                continue

            # =========================================================
            # LAB MODE: küçük hesap => emir YOK, sadece log
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
            # GERÇEK EMİR BÖLÜMÜ (SAFE MODE)
            # =========================================================

            max_notional = equity * MAX_EQUITY_UTIL
            effective_notional = max(
                MIN_NOTIONAL,
                min(requested_notional, max_notional)
            )

            logger.info(
                "EFFECTIVE NOTIONAL: requested=%.4f %s, capped=%.4f %s (%.0f%% of equity)",
                requested_notional,
                equity_ccy,
                effective_notional,
                equity_ccy,
                MAX_EQUITY_UTIL * 100,
            )

            okx_symbol = symbol

            # Fiyat çek
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

            amount = effective_notional / price

            # Leverage ayarla - CROSS MARGIN
            try:
                exchange.set_leverage(MAX_LEVERAGE, okx_symbol, params={"mgnMode": "cross"})
                logger.info("Leverage set: %dx for %s (cross margin)", MAX_LEVERAGE, okx_symbol)
            except Exception as e:
                logger.warning("WARN: leverage ayarında sorun (%s): %s", okx_symbol, e)

            # Emir gönder - CROSS MARGIN
            side_lower = side.lower()
            logger.info(
                "PLACING ORDER: %s %s | notional=%.4f %s | price=%.4f | amount=%.8f",
                side,
                okx_symbol,
                effective_notional,
                equity_ccy,
                price,
                amount,
            )

            try:
                order = exchange.create_order(
                    okx_symbol,
                    type="market",
                    side=side_lower,
                    amount=exchange.amount_to_precision(okx_symbol, amount),
                    params={
                        "tdMode": "cross",  # CROSS MARGIN!
                    },
                )
                logger.info(
                    "ORDER SUCCESS: id=%s, status=%s",
                    order.get("id"),
                    order.get("status"),
                )
            except Exception as e:
                logger.error(
                    "ORDER FAILED for %s %s: %s",
                    side,
                    okx_symbol,
                    e,
                )

            # Sinyali işlenmiş olarak işaretle
            last_signature = signature
            save_state(STATE_FILE, {"last_signature": last_signature})

            time.sleep(POLL_INTERVAL)

        except KeyboardInterrupt:
            logger.info("KeyboardInterrupt – executor kapanıyor.")
            break
        except Exception as e:
            logger.exception("UNCAUGHT ERROR in main loop: %s", e)
            time.sleep(5)


if __name__ == "__main__":
    main()