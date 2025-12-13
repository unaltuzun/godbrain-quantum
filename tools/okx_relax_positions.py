#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
🧯 GODMONEY POSITION RELAXER – OKX SWAP

- OKX açık pozisyonlarını doğrudan borsadan okur (swap)
- Her sembol için belirlediğin USD notional limitinin üstünü
  reduceOnly MARKET emirleriyle küçültür.
- .env içindeki OKX key isimlerini esnek okur:
    OKX_API_KEY  / OKX_KEY
    OKX_API_SECRET / OKX_SECRET
    OKX_PASSWORD / OKX_PASSPHRASE
- DRY_RUN=True iken sadece planı yazdırır, emir göndermez.
"""

import os
import sys
from pathlib import Path
from typing import Dict, Any, List

import ccxt
from dotenv import load_dotenv

# =============================================================================
# AYARLAR
# =============================================================================

BASE_DIR = Path(__file__).resolve().parent.parent  # /mnt/c/godbrain-quantum
ENV_PATH = BASE_DIR / ".env"

# Maksimum izin verilen notional (USD) / sembol
MAX_NOTIONAL_PER_SYMBOL = float(os.getenv("RELAX_MAX_NOTIONAL", "600"))

# Güvenlik: önce DRY-RUN ile plan gör, sonra False yap
DRY_RUN = os.getenv("RELAX_DRY_RUN", "true").lower() in ("1", "true", "yes")

# =============================================================================
# ENV / OKX CLIENT
# =============================================================================

def hard_load_env() -> None:
    """
    .env'yi hem dotenv ile hem de manuel parse ederek yükler.
    Özellikle OKX_* satırlarını os.environ'a zorla yazar.
    """
    print(f"[RELAX] ENV_PATH: {ENV_PATH} (exists={ENV_PATH.exists()})")

    if ENV_PATH.exists():
        # 1) Normal dotenv yükle
        load_dotenv(ENV_PATH)

        # 2) Ekstra: dosyayı satır satır oku, OKX_* ile başlayanları elle bas
        okx_lines: List[str] = []
        with ENV_PATH.open("r", encoding="utf-8") as f:
            for line in f:
                raw = line.strip()
                if not raw or raw.startswith("#"):
                    continue
                if raw.upper().startswith("OKX_"):
                    okx_lines.append(raw)
                    if "=" in raw:
                        k, v = raw.split("=", 1)
                        os.environ.setdefault(k.strip(), v.strip())

        if okx_lines:
            print("[RELAX] .env içindeki OKX_* satırları:")
            for l in okx_lines:
                # Değerleri göstermeyelim, sadece key
                k = l.split("=", 1)[0].strip()
                print(f"    - {k}=***")
        else:
            print("[RELAX] .env içinde hiç OKX_* satırı bulunamadı.")
    else:
        print(f"⚠️ .env bulunamadı: {ENV_PATH}", file=sys.stderr)


def get_okx_client() -> ccxt.okx:
    """OKX swap client oluştur (fallback ile)."""
    # Birden fazla isim desteği:
    api_key = (
        os.getenv("OKX_API_KEY")
        or os.getenv("OKX_KEY")
    )
    api_secret = (
        os.getenv("OKX_API_SECRET")
        or os.getenv("OKX_SECRET")
    )
    password = (
        os.getenv("OKX_PASSWORD")
        or os.getenv("OKX_PASSPHRASE")
    )

    # Debug: neleri görüyoruz?
    seen = {
        "OKX_API_KEY": bool(os.getenv("OKX_API_KEY")),
        "OKX_KEY": bool(os.getenv("OKX_KEY")),
        "OKX_API_SECRET": bool(os.getenv("OKX_API_SECRET")),
        "OKX_SECRET": bool(os.getenv("OKX_SECRET")),
        "OKX_PASSWORD": bool(os.getenv("OKX_PASSWORD")),
        "OKX_PASSPHRASE": bool(os.getenv("OKX_PASSPHRASE")),
    }
    print("[RELAX] OKX env görünürlüğü:")
    for k, v in seen.items():
        print(f"    {k:16s} → {'SET' if v else 'MISSING'}")

    if not api_key or not api_secret or not password:
        print("❌ OKX env eksik (api_key / api_secret / password türevi isimler bulunamadı).", file=sys.stderr)
        sys.exit(1)

    exchange = ccxt.okx({
        "apiKey": api_key,
        "secret": api_secret,
        "password": password,
        "enableRateLimit": True,
        "options": {
            "defaultType": "swap"  # USDT-M argined perpetual
        },
    })

    return exchange

# =============================================================================
# POZİSYON OKUMA & HESAPLAMA
# =============================================================================

def fetch_open_positions(exchange: ccxt.okx):
    """OKX'ten aktif swap pozisyonlarını çek."""
    positions = exchange.fetch_positions()
    active = []

    for p in positions:
        info: Dict[str, Any] = p.get("info", {})
        inst_id = info.get("instId")
        pos_side = (info.get("posSide") or p.get("side") or "").lower()

        # Sadece USDT-margined perpetual
        if not inst_id or not inst_id.endswith("-USDT-SWAP"):
            continue

        # Notional hesabı
        notional_str = info.get("notionalUsd") or "0"
        try:
            notional = abs(float(notional_str))
        except Exception:
            contracts = float(info.get("pos", "0") or 0)
            last = float(info.get("last", p.get("entryPrice") or 0) or 0)
            notional = abs(contracts * last)

        if notional <= 0:
            continue

        active.append({
            "symbol": p["symbol"],          # "DOGE/USDT:USDT"
            "instId": inst_id,              # "DOGE-USDT-SWAP"
            "side": pos_side,               # long/short
            "notional": notional,
            "entryPrice": float(p.get("entryPrice") or 0),
            "raw": p,
        })

    return active

# =============================================================================
# PLAN / EMİR
# =============================================================================

def print_header():
    print("\n============================================================")
    print("  🧯 GODMONEY POSITION RELAXER – OKX SWAP")
    print("============================================================")
    print(f"[RELAX] MAX_NOTIONAL_PER_SYMBOL: {MAX_NOTIONAL_PER_SYMBOL:.2f} USD")
    print(f"[RELAX] DRY_RUN: {DRY_RUN}")
    print("------------------------------------------------------------")


def build_relax_plan(positions):
    """Hangi sembolde ne kadar küçültme yapılacağını hesapla."""
    plan = []

    for pos in positions:
        excess = pos["notional"] - MAX_NOTIONAL_PER_SYMBOL
        if excess <= 0:
            continue

        symbol = pos["symbol"]
        inst_id = pos["instId"]
        side = pos["side"]
        entry = pos["entryPrice"] or 0.0

        if entry <= 0:
            # entryPrice yoksa keskin hesap riskli, atla
            continue

        amount_to_close = excess / entry  # ≈ kaç coin kapatılacak?

        if side == "long":
            close_side = "sell"
        else:
            close_side = "buy"

        plan.append({
            "symbol": symbol,
            "instId": inst_id,
            "current_notional": pos["notional"],
            "excess_notional": excess,
            "close_side": close_side,
            "amount": amount_to_close,
        })

    return plan


def print_plan(plan):
    if not plan:
        print("[RELAX] Tüm pozisyonlar zaten limitin altında, işlem yok.")
        return

    print("[RELAX] Rahatlatılacak pozisyonlar (OKX gerçek verisi):")
    for item in plan:
        print(
            f"  • {item['symbol']:15s} | Mevcut ≈ {item['current_notional']:.2f} USD "
            f"| Fazla ≈ {item['excess_notional']:.2f} USD "
            f"| Aksiyon: {item['close_side'].upper()} {item['amount']:.6f} ({item['instId']})"
        )


def execute_plan(exchange, plan):
    if DRY_RUN:
        print("\n[RELAX] DRY-RUN aktif, emir gönderilmeyecek. Sadece plan gösterildi.")
        return

    print("\n[RELAX] EXECUTE MODU – reduceOnly MARKET emirleri gönderiliyor...\n")

    for item in plan:
        try:
            params = {
                "reduceOnly": True
            }
            print(f"[RELAX] → {item['instId']} | {item['close_side'].upper()} {item['amount']:.6f} (reduceOnly)")
            order = exchange.create_order(
                symbol=item["instId"],      # Örn: DOGE-USDT-SWAP
                type="market",
                side=item["close_side"],
                amount=item["amount"],
                params=params,
            )
            print(f"[RELAX]   OKX ORDER OK: id={order.get('id')}")
        except Exception as e:
            print(f"[RELAX]   ❌ ORDER ERROR {item['instId']}: {e}")


def main():
    hard_load_env()
    print_header()

    exchange = get_okx_client()
    print("[RELAX] OKX client hazır (swap). Açık pozisyonlar çekiliyor...")

    positions = fetch_open_positions(exchange)

    if not positions:
        print("[RELAX] Aktif swap pozisyonu bulunamadı.")
        return

    print("\n[RELAX] Mevcut açık pozisyonlar (özet):")
    for p in positions:
        print(f"  • {p['symbol']:15s} | Side: {p['side']:<5s} | Notional ≈ {p['notional']:.2f} USD")

    plan = build_relax_plan(positions)
    print()
    print_plan(plan)
    execute_plan(exchange, plan)


if __name__ == "__main__":
    main()
