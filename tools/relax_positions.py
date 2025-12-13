#!/usr/bin/env python3
"""
🧯 GODMONEY APEX – POSITION RELAXER

- Quantum logundan EXECUTE satırlarını okur.
- Her sembol için net USD pozisyonunu hesaplar (BUY = +, SELL = -).
- max_notional eşiğini aşan semboller için rahatlatma planı çıkarır.
- --mode execute ile OKX'e reduceOnly market emirleri gönderir.

Kullanım:
  python tools/relax_positions.py \
      --log /root/.pm2/logs/godbrain-quantum-out.log \
      --max-notional 150 \
      --mode plan

  python tools/relax_positions.py \
      --log /root/.pm2/logs/godbrain-quantum-out.log \
      --max-notional 150 \
      --mode execute
"""

import os
import sys
import re
import math
import argparse
from collections import defaultdict

# ----------------- Basit .env loader ----------------- #

def load_env(path: str = ".env") -> None:
    if not os.path.exists(path):
        print(f"[RELAX] .env bulunamadı: {path} (devam ediyorum, sadece ortam değişkenlerini kullanırım)")
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
        print(f"[RELAX] .env yüklendi: {path}")
    except Exception as e:
        print(f"[RELAX] .env okunamadı ({path}): {e}")


# ----------------- Log Parser ----------------- #

EXECUTE_RE = re.compile(
    r"EXECUTE:\s+(BUY|SELL)\s+([A-Z0-9\/:]+)\s+\|\s+\$(\d+(\.\d+)?)"
)

def parse_positions_from_log(log_path: str):
    """
    Quantum logundan net USD bazlı pozisyonları parse eder.
    BUY  -> +usd
    SELL -> -usd
    """
    if not os.path.exists(log_path):
        print(f"[RELAX] Log bulunamadı: {log_path}")
        sys.exit(1)

    pos = defaultdict(float)
    trades = defaultdict(int)
    last_line_for = {}

    with open(log_path, "r", encoding="utf-8", errors="ignore") as f:
        for line in f:
            m = EXECUTE_RE.search(line)
            if not m:
                continue
            side = m.group(1)
            symbol = m.group(2)
            usd = float(m.group(3))

            sign = 1.0 if side == "BUY" else -1.0
            pos[symbol] += sign * usd
            trades[symbol] += 1
            last_line_for[symbol] = line.strip()

    return pos, trades, last_line_for


# ----------------- OKX Bağlantısı ----------------- #

def get_okx():
    try:
        import ccxt  # type: ignore
    except ImportError:
        print("[RELAX] HATA: ccxt yüklü değil. Önce şunu çalıştır:")
        print("  pip install ccxt")
        sys.exit(1)

    api_key = os.getenv("OKX_API_KEY")
    secret = os.getenv("OKX_API_SECRET")
    password = os.getenv("OKX_PASSWORD") or os.getenv("OKX_API_PASSWORD")

    if not api_key or not secret or not password:
        print("[RELAX] HATA: OKX env eksik (OKX_API_KEY / OKX_API_SECRET / OKX_PASSWORD).")
        print("       .env dosyanı kontrol et.")
        sys.exit(1)

    exchange = ccxt.okx({
        "apiKey": api_key,
        "secret": secret,
        "password": password,
        "enableRateLimit": True,
        "options": {
            "defaultType": "swap",  # DOGE-USDT-SWAP vb.
        },
    })
    return exchange


def relax_symbol(exchange, symbol_ccxt: str, net_usd: float, target_max_usd: float, dry_run: bool):
    """
    Bir sembol için net_usd pozisyonunu target_max_usd seviyesine çeker.
    net_usd > 0  => net LONG, azaltmak için SELL reduceOnly
    net_usd < 0  => net SHORT, azaltmak için BUY reduceOnly
    """
    direction = "LONG" if net_usd > 0 else "SHORT"
    abs_usd = abs(net_usd)

    if abs_usd <= target_max_usd:
        return None  # işlem gerek yok

    reduce_usd = abs_usd - target_max_usd
    side = "sell" if net_usd > 0 else "buy"   # LONG -> SELL, SHORT -> BUY

    # Fiyat çek
    ticker = exchange.fetch_ticker(symbol_ccxt)
    last = ticker.get("last") or ticker.get("close")
    if not last or last <= 0:
        raise RuntimeError(f"{symbol_ccxt} için geçersiz fiyat: {last}")

    raw_amount = reduce_usd / last

    market = exchange.market(symbol_ccxt)
    amount_prec = market.get("precision", {}).get("amount", None)

    if amount_prec is not None:
        # ccxt amount_to_precision kullanmak daha güvenli
        amount = float(exchange.amount_to_precision(symbol_ccxt, raw_amount))
    else:
        # yedek
        amount = float(f"{raw_amount:.6f}")

    if amount <= 0:
        return None

    print(f"\n[RELAX] {symbol_ccxt} | Net: {direction} ~${abs_usd:.2f} → hedef max ${target_max_usd:.2f}")
    print(f"[RELAX] Kapatılacak yaklaşık: ${reduce_usd:.2f} | Side={side.upper()} | Amount≈{amount}")

    if dry_run:
        print("[RELAX] (PLAN MODU) Emir GÖNDERİLMİYOR, sadece öneri.")
        return {
            "symbol": symbol_ccxt,
            "side": side,
            "amount": amount,
            "mode": "plan",
        }

    # Gerçek emir
    params = {"reduceOnly": True}
    try:
        order = exchange.create_order(
            symbol_ccxt,
            type="market",
            side=side,
            amount=amount,
            price=None,
            params=params,
        )
        print(f"[RELAX] ✅ ORDER SENT: {side.upper()} {amount} {symbol_ccxt} (reduceOnly)")
        return {
            "symbol": symbol_ccxt,
            "side": side,
            "amount": amount,
            "mode": "execute",
            "order_id": order.get("id"),
            "info": order.get("info"),
        }
    except Exception as e:
        print(f"[RELAX] ❌ ORDER ERROR {symbol_ccxt}: {e}")
        return {
            "symbol": symbol_ccxt,
            "side": side,
            "amount": amount,
            "mode": "execute",
            "error": str(e),
        }


# ----------------- MAIN ----------------- #

def main():
    parser = argparse.ArgumentParser(description="GODMONEY Position Relaxer")
    parser.add_argument("--log", required=True, help="Quantum log path (örn: /root/.pm2/logs/godbrain-quantum-out.log)")
    parser.add_argument("--max-notional", type=float, default=150.0,
                        help="Her sembol için izin verilen max net notional (USD). Varsayılan: 150")
    parser.add_argument("--mode", choices=["plan", "execute"], default="plan",
                        help="'plan' = sadece öneri, 'execute' = OKX'e reduceOnly emir gönder.")
    parser.add_argument("--env", default=".env", help=".env yolu (varsayılan: .env)")
    args = parser.parse_args()

    print("============================================================")
    print("  🧯 GODMONEY POSITION RELAXER")
    print("============================================================")
    print(f"[RELAX] Log: {args.log}")
    print(f"[RELAX] Mode: {args.mode}")
    print(f"[RELAX] Max notional per symbol: ${args.max_notional:.2f}")
    print("------------------------------------------------------------")

    load_env(args.env)

    pos, trades, last_line_for = parse_positions_from_log(args.log)

    if not pos:
        print("[RELAX] Logta EXECUTE satırı bulunamadı. Çıkıyorum.")
        sys.exit(0)

    print("\n[RELAX] Mevcut net pozisyonlar (log bazlı):")
    sorted_syms = sorted(pos.items(), key=lambda x: abs(x[1]), reverse=True)
    for sym, usd in sorted_syms:
        print(f"  • {sym:15s} | Net ≈ {usd:8.2f} USD | Trades: {trades.get(sym,0)}")

    # Sadece hedefi aşan sembolleri işleme al
    heavy = [(s, v) for s, v in sorted_syms if abs(v) > args.max_notional]

    if not heavy:
        print("\n[RELAX] Hiçbir sembol max_notional eşiğini aşmıyor. İşlem yok.")
        sys.exit(0)

    print("\n[RELAX] Rahatlatılacak semboller:")
    for sym, v in heavy:
        print(f"  → {sym:15s} | Net ≈ {v:8.2f} USD")

    if args.mode == "plan":
        print("\n[RELAX] PLAN MODU – emir yok, sadece öneri çıkaracağım.")
        # OKX bağlantısı sadece hesaplamak için yine açılabilir ama istersen kapatılabilir.
        exchange = get_okx()
        for sym, net_usd in heavy:
            # ccxt sembol formatı repo içinde zaten EXECUTE satırında kullanılan format: XRP/USDT:USDT
            relax_symbol(exchange, sym, net_usd, args.max_notional, dry_run=True)
    else:
        print("\n[RELAX] EXECUTE MODU – OKX'e reduceOnly MARKET emirleri gidecek.")
        exchange = get_okx()
        results = []
        for sym, net_usd in heavy:
            res = relax_symbol(exchange, sym, net_usd, args.max_notional, dry_run=False)
            results.append(res)

        print("\n[RELAX] ÖZET:")
        for r in results:
            if not r:
                continue
            if r.get("error"):
                print(f"  ❌ {r['symbol']} | {r['side']} {r['amount']} ERROR: {r['error']}")
            else:
                print(f"  ✅ {r['symbol']} | {r['side']} {r['amount']} (mode={r['mode']})")

    print("\n[RELAX] Bitti.")


if __name__ == "__main__":
    main()

