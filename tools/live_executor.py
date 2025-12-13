#!/usr/bin/env python3
"""
GODBRAIN APEX LIVE EXECUTOR
- Tails: /root/.pm2/logs/godbrain-quantum-out.log
- Her '>>> EXECUTE' satırını OKX market order'a çevirir
- .env dosyasını kendisi yükler, çeşitli OKX key isimlerini otomatik dener
"""

import os
import re
import time
import subprocess
import sys

LOG_PATH = "/root/.pm2/logs/godbrain-quantum-out.log"
ENV_PATH = "/mnt/c/godbrain-quantum/.env"

try:
    import ccxt
except Exception as e:
    ccxt = None


def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[APEX {ts}] {msg}", flush=True)


def load_env_file(path: str = ENV_PATH):
    """Basit .env parser – key=value satırlarını os.environ'a ekler."""
    if not os.path.exists(path):
        log(f"⚠️ .env bulunamadı: {path}")
        return

    try:
        with open(path, "r", encoding="utf-8") as f:
            for line in f:
                line = line.strip()
                if not line or line.startswith("#") or "=" not in line:
                    continue
                k, v = line.split("=", 1)
                k = k.strip()
                v = v.strip().strip('"').strip("'")
                if k and k not in os.environ:
                    os.environ[k] = v
        log(f"✅ .env yüklendi: {path}")
    except Exception as e:
        log(f"⚠️ .env okunamadı ({path}): {e}")


def resolve_okx_credentials():
    """
    Farklı isimlendirmeleri otomatik dener:
    - OKX_API_KEY / OKX_API_SECRET / OKX_PASSWORD
    - OKX_KEY / OKX_SECRET / OKX_PASSPHRASE
    - EXCHANGE_API_KEY / EXCHANGE_API_SECRET / EXCHANGE_API_PASSPHRASE
    """
    key = (
        os.getenv("OKX_API_KEY")
        or os.getenv("OKX_KEY")
        or os.getenv("EXCHANGE_API_KEY")
    )
    secret = (
        os.getenv("OKX_API_SECRET")
        or os.getenv("OKX_SECRET")
        or os.getenv("EXCHANGE_API_SECRET")
    )
    password = (
        os.getenv("OKX_PASSWORD")
        or os.getenv("OKX_PASSPHRASE")
        or os.getenv("EXCHANGE_API_PASSPHRASE")
    )
    return key, secret, password


def build_okx_client():
    if ccxt is None:
        log("⚠️ ccxt import edilemedi, DRY-RUN.")
        return None

    key, secret, password = resolve_okx_credentials()

    if not (key and secret and password):
        log("⚠️ OKX credentials eksik (KEY/SECRET/PASSWORD). DRY-RUN.")
        return None

    try:
        client = ccxt.okx(
            {
                "apiKey": key,
                "secret": secret,
                "password": password,
                "enableRateLimit": True,
                "options": {
                    "defaultType": "swap",
                },
            }
        )
        log("✅ OKX client initialized (swap mode).")
        return client
    except Exception as e:
        log(f"❌ OKX client init hatası: {e}")
        return None


def map_symbol(raw_symbol: str) -> str:
    """
    'DOGE/USDT:USDT' -> 'DOGE-USDT-SWAP'
    """
    base = raw_symbol.split(":")[0]  # DOGE/USDT
    pair = base.replace("/", "-")   # DOGE-USDT
    return f"{pair}-SWAP"


EXEC_RE = re.compile(r"EXECUTE:\s+(BUY|SELL)\s+([A-Z0-9/:\-]+)\s+\|\s+\$(\d+(?:\.\d+)?)")


def tail_exec_lines(path: str):
    """
    tail -n 0 -F /root/.pm2/logs/godbrain-quantum-out.log
    ve sadece EXECUTE satırlarını yield eder
    """
    cmd = ["tail", "-n", "0", "-F", path]
    proc = subprocess.Popen(
        cmd, stdout=subprocess.PIPE, stderr=subprocess.STDOUT, text=True
    )
    log(f"📜 Tailing EXECUTE lines from: {path}")
    try:
        for line in proc.stdout:
            if "EXECUTE:" not in line:
                continue
            yield line.rstrip("\n")
    finally:
        try:
            proc.terminate()
        except Exception:
            pass


def get_amount_from_usd(client, market_symbol: str, side: str, usd_size: float) -> float:
    """
    usd_size -> amount
    """
    try:
        ticker = client.fetch_ticker(market_symbol)
        price = ticker.get("last") or ticker.get("close")
        if not price or price <= 0:
            raise ValueError("No valid price.")
        amount = usd_size / float(price)
        amount = float(f"{amount:.6f}")
        return max(amount, 0.0)
    except Exception as e:
        log(f"⚠️ {market_symbol} amount hesaplanamadı: {e}")
        return 0.0


def main():
    # 1) .env yükle
    load_env_file()

    # 2) APEX_LIVE flag'i .env sonrası okunuyor
    apex_live = os.getenv("APEX_LIVE", "false").lower() == "true"

    log("════════════════════════════════════════════")
    log("  GODBRAIN APEX LIVE EXECUTOR STARTED")
    log(f"  APEX_LIVE={apex_live}")
    log("  Source log: " + LOG_PATH)
    log("════════════════════════════════════════════")

    client = build_okx_client() if apex_live else None

    if apex_live and not client:
        log("⚠️ APEX_LIVE=true ama OKX client yok. DRY-RUN moduna düşüyorum.")
        live_mode = False
    else:
        live_mode = apex_live

    last_set_leverage = {}

    for line in tail_exec_lines(LOG_PATH):
        m = EXEC_RE.search(line)
        if not m:
            continue

        side = m.group(1).upper()            # BUY / SELL
        raw_symbol = m.group(2)              # DOGE/USDT:USDT
        usd_size = float(m.group(3))         # 16.0 gibi

        market_symbol = map_symbol(raw_symbol)

        log(f"🛰  SIGNAL → {side} {raw_symbol} | ${usd_size} → {market_symbol}")

        if not live_mode:
            log("💤 DRY-RUN: Order gönderilmiyor (live_mode=false).")
            continue

        if client is None:
            log("❌ OKX client yok; order atlanıyor.")
            continue

        # Leverage 10x’e setle (bir kere)
        try:
            if market_symbol not in last_set_leverage:
                client.set_leverage(10, market_symbol)
                last_set_leverage[market_symbol] = time.time()
                log(f"⚙️ Set leverage 10x for {market_symbol}")
        except Exception as e:
            log(f"⚠️ set_leverage hatası {market_symbol}: {e}")

        amount = get_amount_from_usd(client, market_symbol, side, usd_size)
        if amount <= 0:
            log(f"❌ Skipping, amount <= 0 for {market_symbol}")
            continue

        try:
            order = client.create_order(
                market_symbol,
                type="market",
                side=side.lower(),
                amount=amount,
            )
            log(
                f"✅ ORDER SENT: {side} {market_symbol} | amount={amount} | usd≈{usd_size} | id={order.get('id')}"
            )
        except Exception as e:
            log(f"❌ ORDER ERROR {market_symbol}: {e}")


if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("⏹ Stopped by user.")
        sys.exit(0)
