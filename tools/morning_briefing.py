#!/usr/bin/env python3
# -*- coding: utf-8 -*-

import os, re
from pathlib import Path
from collections import defaultdict, deque

from dotenv import load_dotenv

ROOT = Path("/mnt/c/godbrain-quantum")
ENV_PATH = ROOT / ".env"
LOG_QUANTUM = Path("/root/.pm2/logs/godbrain-quantum-out.log")
LOG_APEX = Path("/root/.pm2/logs/godmoney-apex-out.log")

# -----------------------------------------------------
# Helpers
# -----------------------------------------------------

def tail(path: Path, max_lines: int = 4000):
    dq = deque(maxlen=max_lines)
    try:
        with open(path, "r", encoding="utf-8", errors="ignore") as f:
            for line in f:
                dq.append(line.rstrip("\n"))
    except FileNotFoundError:
        return []
    return list(dq)

# -----------------------------------------------------
# 1) OKX snapshot
# -----------------------------------------------------

def okx_snapshot():
    print("============================================================")
    print("  🛰  OKX HESAP ÖZETİ")
    print("============================================================")

    load_dotenv(ENV_PATH)

    api_key   = os.getenv("OKX_API_KEY") or os.getenv("OKX_KEY")
    secret    = os.getenv("OKX_SECRET") or os.getenv("OKX_API_SECRET")
    password  = os.getenv("OKX_PASSWORD") or os.getenv("OKX_PASSPHRASE")

    try:
        import ccxt  # type: ignore
    except Exception:
        ccxt = None

    if not (api_key and secret and password and ccxt):
        print("⚠️  OKX veya ccxt konfigürü eksik, sadece log analizi yapılacak.")
        return

    try:
        exchange = ccxt.okx({
            "apiKey": api_key,
            "secret": secret,
            "password": password,
            "enableRateLimit": True,
        })

        balance = exchange.fetch_balance()
        total_usdt = balance.get("total", {}).get("USDT")
        free_usdt  = balance.get("free", {}).get("USDT")
        used_usdt  = balance.get("used", {}).get("USDT")

        print(f"Toplam equity (USDT) : {total_usdt}")
        print(f"Serbest (free)       : {free_usdt}")
        print(f"Kullanımda (used)    : {used_usdt}")
        print("")

        # Swap pozisyonları
        try:
            positions = exchange.fetch_positions()
        except Exception as e:
            print(f"⚠️  Pozisyonlar alınamadı: {e}")
            return

        interesting = []
        for p in positions:
            # ccxt okx unified alanlar
            symbol = p.get("symbol")
            contracts = float(p.get("contracts") or 0)
            notional = float(p.get("notional") or 0)
            side = p.get("side") or "flat"
            if abs(contracts) > 0 and abs(notional) > 1:
                interesting.append((symbol, side, contracts, notional, p))

        if not interesting:
            print("📭 Açık swap pozisyonu yok veya çok küçük.")
        else:
            print("📊 Açık swap pozisyonları:")
            for symbol, side, contracts, notional, _ in interesting:
                print(f"  • {symbol:12} | Side:{side:5} | Contracts:{contracts:.4f} | Notional≈{notional:.2f} USDT")
    except Exception as e:
        print(f"⚠️  OKX snapshot sırasında hata: {e}")

# -----------------------------------------------------
# 2) Quantum log: EXECUTE özet
# -----------------------------------------------------

def quantum_exec_summary():
    print("")
    print("============================================================")
    print("  🧠 GODBRAIN QUANTUM – GECE TRADE ÖZETİ (LOG)")
    print("============================================================")

    lines = tail(LOG_QUANTUM)
    if not lines:
        print(f"⚠️  Log bulunamadı: {LOG_QUANTUM}")
        return

    EXEC_RE = re.compile(r"EXECUTE:\s+(BUY|SELL)\s+(\S+)\s+\|\s+\$(\d+(\.\d+)?)")

    stats = defaultdict(lambda: {
        "net_usd": 0.0,
        "trades": 0,
        "last_side": None,
        "last_line": None,
    })
    total_exec = 0

    for line in lines:
        m = EXEC_RE.search(line)
        if not m:
            continue
        side, symbol, usd_str, _ = m.groups()
        usd = float(usd_str)
        total_exec += 1

        s = stats[symbol]
        if side == "BUY":
            s["net_usd"] += usd
        else:
            s["net_usd"] -= usd
        s["trades"] += 1
        s["last_side"] = side
        s["last_line"] = line.strip()

    if total_exec == 0:
        print("Hiç EXECUTE satırı bulunamadı (son ~4000 satır).")
        return

    print(f"Toplam EXECUTE satırı: {total_exec}")
    print("")
    print("Sembol bazında özet (log tabanlı net USD exposure):")

    # büyükten küçüğe sırala
    items = sorted(stats.items(), key=lambda kv: abs(kv[1]["net_usd"]), reverse=True)
    for symbol, s in items:
        net = s["net_usd"]
        side = "NET LONG" if net > 0 else ("NET SHORT" if net < 0 else "FLAT")
        risk_flag = " → ⚠️ büyük pozisyon" if abs(net) >= 1000 else ""
        print(f"• {symbol:12} | {side:9} ≈ {net:8.2f} USD | Trades: {s['trades']:3d}{risk_flag}")

    # en riskli 3 sembol için son EXECUTE satırı
    top3 = items[:3]
    if top3:
        print("")
        print("Detay için en riskli 3 sembolün son EXECUTE satırı:")
        for symbol, s in top3:
            if not s["last_line"]:
                continue
            print("")
            print(f"--- {symbol} ---")
            print("  " + s["last_line"])

# -----------------------------------------------------
# 3) APEX log: order başarı / hata oranı
# -----------------------------------------------------

def apex_order_summary():
    print("")
    print("============================================================")
    print("  🗡  GODMONEY APEX – EMİR DURUMU (LOG)")
    print("============================================================")

    lines = tail(LOG_APEX)
    if not lines:
        print(f"⚠️  Log bulunamadı: {LOG_APEX}")
        return

    SIGNAL_RE = re.compile(r"SIGNAL\s+→\s+(BUY|SELL)\s+(\S+)\s+\|\s+\$(\d+(\.\d+)?)")
    signals = 0
    orders_ok = 0
    orders_err = 0

    for line in lines:
        if "SIGNAL →" in line:
            if SIGNAL_RE.search(line):
                signals += 1
        if "ORDER SUCCESS" in line or "OKX ORDER OK" in line:
            orders_ok += 1
        if "ORDER ERROR" in line:
            orders_err += 1

    print(f"Gelen sinyal sayısı (log tail): {signals}")
    print(f"Başarılı emir           : {orders_ok}")
    print(f"Hatalı emir             : {orders_err}")
    if orders_ok + orders_err > 0:
        success_rate = orders_ok / (orders_ok + orders_err) * 100.0
        print(f"Başarı oranı (tail)     : {success_rate:.1f}%")

# -----------------------------------------------------
# MAIN
# -----------------------------------------------------

def main():
    print("╔══════════════════════════════════════════════════════╗")
    print("║            GODBRAIN MORNING BRIEFING v1.0           ║")
    print("╚══════════════════════════════════════════════════════╝")
    print("")
    print(f"ROOT        : {ROOT}")
    print(f"QUANTUM LOG : {LOG_QUANTUM}")
    print(f"APEX LOG    : {LOG_APEX}")
    print("")

    okx_snapshot()
    quantum_exec_summary()
    apex_order_summary()

if __name__ == "__main__":
    main()
