# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  GODBRAIN v4.5 - VOLTRAN EDITION                                             ║
║  Multi-Coin Aggregator + Genetic Blackjack DNA + VOLTRAN Fusion              ║
║                                                                              ║
║  🦅 Blackjack (Edge) + 🐺 Roulette (Survival) + 🦁 Chaos (Cosmic) = VOLTRAN  ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import asyncio
import pandas as pd
import time
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path("/mnt/c/godbrain-quantum")
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

# REDIS FOR GENETICS
try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("[INIT] Redis not installed, using FALLBACK_DNA")

# EXCHANGE & ULTIMATE PACK
try:
    import ccxt
    from ultimate_pack.ultimate_connector import UltimateConnector
    from ultimate_pack.filters.signal_filter import SignalFilter
except ImportError as e:
    print(f"[FATAL] Modules missing: {e}")
    sys.exit(1)

# GODLANG PULSE CONSUMER
try:
    from godlang.godlang_pulse import GodlangPulseConsumer
    PULSE_CONSUMER = GodlangPulseConsumer()
    PULSE_ENABLED = True
    print("[INIT] GODLANG Pulse Consumer: ACTIVE")
except Exception as e:
    PULSE_CONSUMER = None
    PULSE_ENABLED = False
    print(f"[INIT] GODLANG Pulse Consumer: DISABLED ({e})")

# CHEAT SIGNAL CONSUMER
try:
    from core.cheat_consumer import get_cheat_override
    CHEAT_ENABLED = True
    print("[INIT] Cheat Signal Consumer: ACTIVE")
except Exception as e:
    CHEAT_ENABLED = False
    get_cheat_override = lambda x: (None, 0, 1.0)
    print(f"[INIT] Cheat Signal Consumer: DISABLED ({e})")

# VOLTRAN BRIDGE
try:
    from genetics.voltran_bridge import get_voltran_snapshot
    VOLTRAN_ENABLED = True
    print("[INIT] VOLTRAN Bridge: ACTIVE 🦅🐺🦁")
except Exception as e:
    VOLTRAN_ENABLED = False
    get_voltran_snapshot = lambda: {"voltran_factor": 1.0, "voltran_score": 50, "rank": "DISABLED"}
    print(f"[INIT] VOLTRAN Bridge: DISABLED ({e})")

LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)
AGG_DECISION_LOG = LOG_DIR / "agg_decisions.log"
APEX_SIGNAL_FILE = LOG_DIR / "apex_signal.json"

TRADING_PAIRS = [
    "DOGE/USDT:USDT",
    "XRP/USDT:USDT",
    "SOL/USDT:USDT",
]

GEN_REDIS_HOST = os.getenv("GENETICS_REDIS_HOST", "127.0.0.1")
GEN_REDIS_PORT = int(os.getenv("GENETICS_REDIS_PORT", "6379"))
GEN_REDIS_DB = int(os.getenv("GENETICS_REDIS_DB", "0"))
GEN_REDIS_PASSWORD = os.getenv("GENETICS_REDIS_PASSWORD", None)

FALLBACK_DNA = [10, 10, 234, 326, 354, 500]  # Gen 206 – Recovery DNA

DNA_KEY = "godbrain:genetics:best_dna"
META_KEY = "godbrain:genetics:best_meta"

ACTIVE_DNA = FALLBACK_DNA.copy()
ACTIVE_META = None
GEN_MULTS = [0.10, 0.10, 2.34, 3.26, 3.54, 5.00]
LAST_DNA_REFRESH = 0
DNA_REFRESH_INTERVAL = 60

VOLTRAN_CACHE = {"data": None, "last_update": 0}
VOLTRAN_REFRESH_INTERVAL = 30


def get_redis_connection():
    if not REDIS_AVAILABLE:
        return None
    try:
        r = redis.Redis(
            host=GEN_REDIS_HOST,
            port=GEN_REDIS_PORT,
            db=GEN_REDIS_DB,
            password=GEN_REDIS_PASSWORD,
            decode_responses=True,
            socket_timeout=5,
            socket_connect_timeout=5,
        )
        r.ping()
        return r
    except Exception:
        return None


def compute_multipliers_from_dna(dna):
    a, b, c, d, e, f = dna
    return [
        0.10,       # <50
        0.10,       # 50-59
        c / 100.0,  # 60-69
        d / 100.0,  # 70-79
        e / 100.0,  # 80-89
        f / 100.0,  # 90+
    ]


def load_dna_from_redis(force=False):
    global ACTIVE_DNA, ACTIVE_META, GEN_MULTS, LAST_DNA_REFRESH

    now = time.time()
    if not force and (now - LAST_DNA_REFRESH) < DNA_REFRESH_INTERVAL:
        return ACTIVE_DNA, ACTIVE_META

    LAST_DNA_REFRESH = now
    r = get_redis_connection()
    if not r:
        return ACTIVE_DNA, ACTIVE_META

    try:
        raw_dna = r.get(DNA_KEY)
        raw_meta = r.get(META_KEY)
        if not raw_dna:
            return ACTIVE_DNA, ACTIVE_META

        dna = json.loads(raw_dna)
        if not isinstance(dna, list) or len(dna) != 6:
            return ACTIVE_DNA, ACTIVE_META

        if dna != ACTIVE_DNA:
            ACTIVE_DNA = dna
            GEN_MULTS = compute_multipliers_from_dna(dna)
            print(f"[GENETICS] 🧬 DNA UPDATED: {dna} -> MULTS: {GEN_MULTS}")

        if raw_meta:
            try:
                ACTIVE_META = json.loads(raw_meta)
            except Exception:
                pass

        return ACTIVE_DNA, ACTIVE_META
    except Exception as e:
        print(f"[GENETICS] Redis error: {e}")
        return ACTIVE_DNA, ACTIVE_META


def blackjack_multiplier(quantum_score: float) -> float:
    s = max(0.0, min(100.0, float(quantum_score)))
    if s >= 90:
        return GEN_MULTS[5]
    if s >= 80:
        return GEN_MULTS[4]
    if s >= 70:
        return GEN_MULTS[3]
    if s >= 60:
        return GEN_MULTS[2]
    if s >= 50:
        return GEN_MULTS[1]
    return GEN_MULTS[0]


def get_voltran_factor():
    global VOLTRAN_CACHE

    if not VOLTRAN_ENABLED:
        return 1.0, 50.0, "DISABLED"

    now = time.time()
    if VOLTRAN_CACHE["data"] and (now - VOLTRAN_CACHE["last_update"]) < VOLTRAN_REFRESH_INTERVAL:
        d = VOLTRAN_CACHE["data"]
        return d.get("voltran_factor", 1.0), d.get("voltran_score", 50), d.get("rank", "?")

    try:
        snap = get_voltran_snapshot()
        VOLTRAN_CACHE["data"] = snap
        VOLTRAN_CACHE["last_update"] = now
        return snap.get("voltran_factor", 1.0), snap.get("voltran_score", 50), snap.get("rank", "?")
    except Exception as e:
        print(f"[VOLTRAN] Error: {e}")
        return 1.0, 50.0, "ERROR"


print("[INIT] Loading Blackjack Genetics DNA...")
load_dna_from_redis(force=True)
print(f"[INIT] Blackjack Genetics: ACTIVE | DNA={ACTIVE_DNA}")
print(f"[INIT] DNA Multipliers: {GEN_MULTS}")


def send_signal_to_apex(symbol: str, action: str, size_usd: float, regime: str, extras: dict = None):
    signal = {
        "timestamp": datetime.now().isoformat(),
        "symbol": symbol,
        "action": action,
        "size_usd": size_usd,
        "regime": regime,
        "extras": extras or {},
    }
    try:
        with open(APEX_SIGNAL_FILE, "w") as f:
            json.dump(signal, f)
    except Exception as e:
        print(f"[APEX-SIGNAL] Write error: {e}")


async def run_fleet():
    print("=" * 70)
    print("   🌌 GODBRAIN v4.5 - VOLTRAN EDITION")
    print("   Coins: DOGE, XRP, SOL")
    print("   Features: Anti-Whipsaw, GODLANG Pulse, Cheat Code, Blackjack DNA")
    print("   VOLTRAN: 🦅 Blackjack + 🐺 Roulette + 🦁 Chaos = FUSION")
    print("=" * 70)

    api_key = os.getenv("OKX_API_KEY")
    secret = os.getenv("OKX_SECRET")
    passphrase = os.getenv("OKX_PASSWORD") or os.getenv("OKX_PASSPHRASE")

    try:
        okx = ccxt.okx({"apiKey": api_key, "secret": secret, "password": passphrase})
        if os.getenv("OKX_USE_SANDBOX") == "true":
            okx.set_sandbox_mode(True)
        okx.load_markets()
    except Exception as e:
        print(f"[FATAL] OKX init failed: {e}")
        okx = None

    signal_filters = {pair: SignalFilter() for pair in TRADING_PAIRS}

    print("[INIT] Starting Ultimate Brain...")
    ultimate_brain = UltimateConnector()
    await ultimate_brain.initialize()
    print("[INIT] Ready.")
    print(f"[INIT] Trading pairs: {', '.join(TRADING_PAIRS)}")

    if VOLTRAN_ENABLED:
        vf, vs, vr = get_voltran_factor()
        print(f"[INIT] VOLTRAN: Score={vs:.1f} | Factor={vf:.2f}x | {vr}")

    equity_usd = 23.0
    loop_count = 0

    while True:
        try:
            loop_count += 1

            if loop_count % 6 == 0:
                load_dna_from_redis()

            voltran_factor, voltran_score, voltran_rank = get_voltran_factor()

            if okx:
                try:
                    balance = okx.fetch_balance()
                    equity_usd = float(balance["total"].get("USDT", equity_usd))
                except Exception:
                    pass

            per_coin_equity = equity_usd / len(TRADING_PAIRS)

            for symbol in TRADING_PAIRS:
                try:
                    ohlcv = pd.DataFrame()
                    if okx:
                        try:
                            ohlcv_raw = okx.fetch_ohlcv(symbol, "1h", limit=200)
                            if ohlcv_raw:
                                ohlcv = pd.DataFrame(
                                    ohlcv_raw,
                                    columns=["timestamp", "open", "high", "low", "close", "vol"],
                                )
                        except Exception as e:
                            print(f"[{symbol}] OHLCV error: {e}")
                            continue

                    if ohlcv.empty:
                        continue

                    decision = await ultimate_brain.get_signal(symbol, per_coin_equity, ohlcv)

                    raw_action = "HOLD"
                    if decision.action in ["BUY", "STRONG_BUY"]:
                        raw_action = "BUY"
                    elif decision.action in ["SELL", "STRONG_SELL"]:
                        raw_action = "SELL"

                    filtered = signal_filters[symbol].filter(raw_action, decision.conviction)

                    ts = datetime.now().strftime("%H:%M:%S")
                    coin_short = symbol.split("/")[0]

                    if filtered.should_execute and raw_action != "HOLD":
                        pulse = PULSE_CONSUMER.get_latest_pulse() if PULSE_ENABLED and PULSE_CONSUMER else {}
                        flow_mult = pulse.get("flow_multiplier", 1.0)
                        quantum_active = pulse.get("quantum_boost_active", False)

                        if CHEAT_ENABLED:
                            cheat_action, cheat_boost, cheat_mult = get_cheat_override(symbol)
                        else:
                            cheat_action, cheat_boost, cheat_mult = (None, 0, 1.0)

                        if cheat_action and cheat_action == raw_action:
                            flow_mult *= cheat_mult
                            print(
                                f"  🎮 CHEAT BOOST: {cheat_action} +{cheat_boost:.0%} conf, {cheat_mult:.1f}x size"
                            )

                        quantum_resonance_score = max(
                            0.0, min(100.0, float(decision.conviction) * 100.0)
                        )
                        dna_mult = blackjack_multiplier(quantum_resonance_score)

                        total_mult = dna_mult * voltran_factor

                        base_size_usd = per_coin_equity * 0.9 * flow_mult
                        size_usd = max(5, base_size_usd * total_mult)
                        size_usd = min(size_usd, equity_usd * 0.5)

                        print(
                            f"[{ts}] {coin_short} | Eq:${per_coin_equity:.0f} | "
                            f"{decision.regime} | {raw_action} "
                            f"(Conv:{decision.conviction:.2f}, QScore:{quantum_resonance_score:.1f}, "
                            f"DNAx:{dna_mult:.2f}, VOL:{voltran_factor:.2f})"
                        )

                        quantum_flag = " 🔮" if quantum_active else ""
                        voltran_flag = " 🦅🐺🦁" if voltran_factor > 1.0 else ""

                        log_msg = (
                            f"  >>> EXECUTE: {raw_action} {symbol} | ${size_usd:.0f} | "
                            f"Regime:{decision.regime} | Flow:{flow_mult:.2f}x | "
                            f"QScore:{quantum_resonance_score:.1f} | DNAx:{dna_mult:.2f} | "
                            f"VOL:{voltran_factor:.2f}{quantum_flag}{voltran_flag}"
                        )
                        print(log_msg)

                        with open(AGG_DECISION_LOG, "a") as f:
                            f.write(f"{datetime.now().isoformat()} | {log_msg}\n")

                        send_signal_to_apex(
                            symbol,
                            raw_action,
                            size_usd,
                            decision.regime,
                            {
                                "conviction": decision.conviction,
                                "quantum_score": quantum_resonance_score,
                                "dna_mult": dna_mult,
                                "voltran_factor": voltran_factor,
                                "voltran_score": voltran_score,
                                "flow_mult": flow_mult,
                                "quantum_active": quantum_active,
                            },
                        )

                        signal_filters[symbol].record_trade(raw_action)
                    elif raw_action != "HOLD":
                        print(
                            f"[{ts}] {coin_short} 🛡️ BLOCKED: {raw_action} -> {filtered.filter_reason}"
                        )
                except Exception as e:
                    print(f"[{symbol}] Error: {e}")
                    continue
        except Exception as e:
            print(f"[ERR] Loop: {e}")

        await asyncio.sleep(10)


if __name__ == "__main__":
    print("\n" + "🦅🐺🦁" * 20 + "\n")
    try:
        asyncio.run(run_fleet())
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] VOLTRAN offline. Goodbye!")
        sys.exit(0)
