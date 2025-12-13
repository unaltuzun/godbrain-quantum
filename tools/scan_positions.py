#!/usr/bin/env python3
"""
GODBRAIN / GODMONEY - Basit Pozisyon Scanner (2.0)
--------------------------------------------------
pm2 log çıktısından EXECUTE satırlarını okuyup,
her sembol için net yön / notional / son işlem zamanını özetler.

Kullanım örnekleri:
  pm2 logs godbrain-quantum --lines 800 --nostream | python tools/scan_positions.py
  pm2 logs godmoney-apex   --lines 800 --nostream | python tools/scan_positions.py
  python tools/scan_positions.py /root/.pm2/logs/godmoney-apex-out.log
"""

import sys
import re
from collections import defaultdict

# Satırlardan zaman bilgisini yakala: [00:35:10]
TIME_RE = re.compile(r"\[(\d{2}:\d{2}:\d{2})\]")

# EXECUTE satırı tipik olarak ikinci satır:
#   >>> EXECUTE: BUY DOGE/USDT:USDT | $17 | ...
EXEC_RE = re.compile(
    r">>>\s+EXECUTE:\s+"
    r"(?P<side>BUY|SELL)\s+"
    r"(?P<symbol>[A-Z0-9\-_/:\.]+)\s*\|\s*\$(?P<notional>\d+(\.\d+)?)"
)

def iter_lines():
    if len(sys.argv) > 1:
        path = sys.argv[1]
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                yield line.rstrip("\n")
    else:
        for line in sys.stdin:
            yield line.rstrip("\n")


def main():
    positions = defaultdict(lambda: {
        "net_notional": 0.0,
        "last_side": None,
        "last_time": None,
        "trades": 0,
        "last_line": None,
    })

    total_trades = 0
    last_time = "??:??:??"

    for line in iter_lines():
        # Önce bu satırda zaman varsa güncelle
        tm = TIME_RE.search(line)
        if tm:
            last_time = tm.group(1)

        m = EXEC_RE.search(line)
        if not m:
            continue

        side = m.group("side")
        symbol = m.group("symbol")
        notional = float(m.group("notional"))

        data = positions[symbol]
        # BUY = +, SELL = -
        if side == "BUY":
            data["net_notional"] += notional
        else:
            data["net_notional"] -= notional

        data["last_side"] = side
        data["last_time"] = last_time
        data["trades"] += 1
        data["last_line"] = line
        total_trades += 1

    if not positions:
        print("⚠️ Hiç EXECUTE satırı bulunamadı (log penceresinde trade yok olabilir).")
        sys.exit(0)

    print("\n================ POZİSYON ÖZETİ (LOG TABANLI) ================\n")
    print(f"Toplam EXECUTE satırı: {total_trades}\n")

    items = sorted(
        positions.items(),
        key=lambda kv: abs(kv[1]["net_notional"]),
        reverse=True,
    )

    for symbol, data in items:
        net = data["net_notional"]
        if abs(net) < 1e-6:
            status = "FLAT / dengeli"
        elif net > 0:
            status = f"Net LONG ~${net:,.2f}"
        else:
            status = f"Net SHORT ~${abs(net):,.2f}"

        flag = ""
        if 0 < abs(net) <= 5:
            flag = "  → 💧 toz / kapatılabilir"
        elif abs(net) >= 30:
            flag = "  → ⚠️ büyük pozisyon (sermayeyi sıkıştırıyor olabilir)"

        print(
            f"• {symbol:16s} | {status:30s} "
            f"| Son: {data['last_side']} @ {data['last_time']} | Trades: {data['trades']}{flag}"
        )

    print("\nDetay için en riskli 3 sembolün son EXECUTE satırı:\n")
    for symbol, data in items[:3]:
        print(f"--- {symbol} ---")
        print(data["last_line"])
        print()

if __name__ == "__main__":
    main()

