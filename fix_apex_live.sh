#!/usr/bin/env bash
set -e

echo "→ [FIX_APEX] Switching to /mnt/c/godbrain-quantum ..."
cd /mnt/c/godbrain-quantum

echo "→ [FIX_APEX] Activating venv ..."
source .venv/bin/activate

mkdir -p tools

echo "→ [FIX_APEX] Ensuring ccxt is installed ..."
pip install --upgrade ccxt >/dev/null

echo "→ [FIX_APEX] Writing tools/live_executor.py ..."
cat > tools/live_executor.py << 'PYEOF'
#!/usr/bin/env python3
"""
GODBRAIN APEX LIVE EXECUTOR
- Tail: /root/.pm2/logs/godbrain-quantum-out.log
- Her '>>> EXECUTE' satırını OKX market order'a çevirir
- Control flag: APEX_LIVE=true -> gerçek trade, aksi halde dry-run
"""

import os
import re
import time
import math
import subprocess
import sys

import ccxt

LOG_PATH = "/root/.pm2/logs/godbrain-quantum-out.log"

APEX_LIVE = os.getenv("APEX_LIVE", "false").lower() == "true"

OKX_API_KEY = os.getenv("OKX_API_KEY")
OKX_API_SECRET = os.getenv("OKX_API_SECRET")
OKX_PASSWORD = os.getenv("OKX_PASSWORD")

def log(msg: str):
    ts = time.strftime("%Y-%m-%d %H:%M:%S")
    print(f"[APEX {ts}] {msg}", flush=True)

def build_okx_client():
    if not (OKX_API_KEY and OKX_API_SECRET and OKX_PASSWORD):
        log("⚠️ OKX credentials missing (OKX_API_KEY / OKX_API_SECRET / OKX_PASSWORD). Running in DRY-RUN.")
        return None

    try:
        client = ccxt.okx({
            "apiKey": OKX_API_KEY,
            "secret": OKX_API_SECRET,
            "password": OKX_PASSWORD,
            "enableRateLimit": True,
            "options": {
                "defaultType": "swap",
            },
        })
        log("✅ OKX client initialized (swap mode).")
        return client
    except Exception as e:
        log(f"❌ Failed to init OKX client: {e}")
        return None

def map_symbol(raw_symbol: str) -> str:
    """
    'DOGE/USDT:USDT' -> 'DOGE-USDT-SWAP'
    """
    base = raw_symbol.split(":")[0]  # DOGE/USDT
    pair = base.replace("/", "-")   # DOGE-USDT
    return f"{pair}-SWAP"

EXEC_RE = re.compile(
    r"EXECUTE:\s+(BUY|SELL)\s+([A-Z0-9/:\-]+)\s+\|\s+\$(\d+(?:\.\d+)?)"
)

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
        # OKX min-step’e göre hafif yuvarlayalım
        amount = float(f"{amount:.6f}")
        return max(amount, 0.0)
    except Exception as e:
        log(f"⚠️ Failed to compute amount for {market_symbol}: {e}")
        return 0.0

def main():
    log("════════════════════════════════════════════")
    log("  GODBRAIN APEX LIVE EXECUTOR STARTED")
    log(f"  APEX_LIVE={APEX_LIVE}")
    log("  Source log: " + LOG_PATH)
    log("════════════════════════════════════════════")

    client = build_okx_client() if APEX_LIVE else None

    if APEX_LIVE and not client:
        log("⚠️ APEX_LIVE=true ama OKX client yok. DRY-RUN moduna düşüyorum.")
        global APEX_LIVE
        APEX_LIVE = False

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

        if not APEX_LIVE:
            log("💤 DRY-RUN: Order NOT sent (APEX_LIVE=false).")
            continue

        if client is None:
            log("❌ No OKX client; skipping order.")
            continue

        # Leverage 10x’e setle (bir kere)
        try:
            if market_symbol not in last_set_leverage:
                client.set_leverage(10, market_symbol)
                last_set_leverage[market_symbol] = time.time()
                log(f"⚙️ Set leverage 10x for {market_symbol}")
        except Exception as e:
            log(f"⚠️ set_leverage failed for {market_symbol}: {e}")

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
            log(f"✅ ORDER SENT: {side} {market_symbol} | amount={amount} | usd≈{usd_size} | id={order.get('id')}")
        except Exception as e:
            log(f"❌ ORDER ERROR for {market_symbol}: {e}")
            # Burada istersen ileride dead-letter queue ya da alarm ekleriz

if __name__ == "__main__":
    try:
        main()
    except KeyboardInterrupt:
        log("⏹ Stopped by user.")
        sys.exit(0)
PYEOF

echo "→ [FIX_APEX] Ensuring APEX_LIVE=true in .env ..."
grep -q "^APEX_LIVE=" .env || echo "APEX_LIVE=true" >> .env

echo "→ [FIX_APEX] Exporting .env into current shell for pm2 ..."
set -a
source .env
set +a

echo "→ [FIX_APEX] Restarting godmoney-apex via pm2 ..."
pm2 delete godmoney-apex >/dev/null 2>&1 || true
pm2 start python --name godmoney-apex -- tools/live_executor.py

echo "→ [FIX_APEX] godmoney-apex logs:"
pm2 logs godmoney-apex --lines 10
