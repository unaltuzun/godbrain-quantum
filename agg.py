# -*- coding: utf-8 -*-
"""
╔══════════════════════════════════════════════════════════════════════════════╗
║  GODBRAIN v4.6 - VOLTRAN + EDGE AI OBSERVER                                  ║
║  Multi-Coin Aggregator + Genetic Blackjack DNA + VOLTRAN Fusion + Edge AI    ║
║                                                                              ║
║  🦅 Blackjack (Edge) + 🐺 Roulette (Survival) + 🦁 Chaos (Cosmic) = VOLTRAN  ║
║  + FAZ3.1 Edge AI (Observer) -> extras.edge_ai enrichment (fail-safe)        ║
╚══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import asyncio
import time
from datetime import datetime
from pathlib import Path

import pandas as pd
from dotenv import load_dotenv

# -----------------------------------------------------------------------------
# ROOT / ENV
# -----------------------------------------------------------------------------
THIS_FILE = Path(__file__).resolve()
ROOT = Path(os.getenv("GODBRAIN_ROOT", str(THIS_FILE.parent))).resolve()

# Ensure root is on import path (repo-local imports)
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

load_dotenv(ROOT / ".env")

LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(parents=True, exist_ok=True)

AGG_DECISION_LOG = LOG_DIR / "agg_decisions.log"
APEX_SIGNAL_FILE = LOG_DIR / "apex_signal.json"

print(f"[INIT] ROOT={ROOT}")
print(f"[INIT] LOG_DIR={LOG_DIR}")

# -----------------------------------------------------------------------------
# DecisionEngine (FAZ 1)
# -----------------------------------------------------------------------------
from engines.decision_engine import DecisionEngine

# -----------------------------------------------------------------------------
# REDIS FOR GENETICS
# -----------------------------------------------------------------------------
try:
    import redis  # type: ignore
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False
    print("[INIT] Redis not installed, using FALLBACK_DNA")

# -----------------------------------------------------------------------------
# EXCHANGE & ULTIMATE PACK
# -----------------------------------------------------------------------------
try:
    import ccxt  # type: ignore
    from ultimate_pack.ultimate_connector import UltimateConnector
    from ultimate_pack.filters.signal_filter import SignalFilter
except ImportError as e:
    print(f"[FATAL] Modules missing: {e}")
    raise SystemExit(1)

# -----------------------------------------------------------------------------
# GODLANG PULSE CONSUMER
# -----------------------------------------------------------------------------
try:
    from godlang.godlang_pulse import GodlangPulseConsumer
    PULSE_CONSUMER = GodlangPulseConsumer()
    PULSE_ENABLED = True
    print("[INIT] GODLANG Pulse Consumer: ACTIVE")
except Exception as e:
    PULSE_CONSUMER = None
    PULSE_ENABLED = False
    print(f"[INIT] GODLANG Pulse Consumer: DISABLED ({e})")

# -----------------------------------------------------------------------------
# CHEAT SIGNAL CONSUMER
# -----------------------------------------------------------------------------
try:
    from core.cheat_consumer import get_cheat_override
    CHEAT_ENABLED = True
    print("[INIT] Cheat Signal Consumer: ACTIVE")
except Exception as e:
    CHEAT_ENABLED = False
    get_cheat_override = lambda x: (None, 0, 1.0)  # type: ignore
    print(f"[INIT] Cheat Signal Consumer: DISABLED ({e})")

# -----------------------------------------------------------------------------
# VOLTRAN BRIDGE
# -----------------------------------------------------------------------------
try:
    from genetics.voltran_bridge import get_voltran_snapshot
    VOLTRAN_ENABLED = True
    print("[INIT] VOLTRAN Bridge: ACTIVE 🦅🐺🦁")
except Exception as e:
    VOLTRAN_ENABLED = False
    get_voltran_snapshot = lambda: {"voltran_factor": 1.0, "voltran_score": 50, "rank": "DISABLED"}  # type: ignore
    print(f"[INIT] VOLTRAN Bridge: DISABLED ({e})")

# -----------------------------------------------------------------------------
# C++ EXECUTION CORE (Zero-Latency)
# -----------------------------------------------------------------------------
try:
    # Ensure build dir is in path if necessary, but wrapper handles it
    from core_engine.python_wrapper import GodbrainEngine
    CPP_ENGINE = GodbrainEngine()
    print(f"[INIT] C++ CORE ENGINE: ACTIVE (v{CPP_ENGINE.version}) 🚀")
    CPP_ENABLED = True
except Exception as e:
    print(f"[INIT] C++ CORE ENGINE: DISABLED (Build missing? {e})")
    CPP_ENGINE = None
    CPP_ENABLED = False

# -----------------------------------------------------------------------------
# FAZ 3.1 EDGE AI (Observer) - fail-safe enrichment
# -----------------------------------------------------------------------------
EDGE_AI_ENABLED = os.getenv("EDGE_AI_ENABLED", "true").lower() in ("1", "true", "yes", "on")
_EDGE_AI_CLIENT = None

def _init_edge_ai():
    """
    Initializes EdgeInferenceClient once. Fail-safe:
    - If torch / models / config missing -> disabled automatically
    """
    global _EDGE_AI_CLIENT
    if not EDGE_AI_ENABLED:
        print("[INIT] EDGE AI: DISABLED by env EDGE_AI_ENABLED")
        _EDGE_AI_CLIENT = None
        return None

    if _EDGE_AI_CLIENT is not None:
        return _EDGE_AI_CLIENT

    try:
        from edge_ai.inference import EdgeInferenceClient
        client = EdgeInferenceClient(str(ROOT / "config" / "edge_ai_config.json"))
        if getattr(client, "enabled", False):
            print("[INIT] EDGE AI: ACTIVE (FAZ3.1 observer)")
            _EDGE_AI_CLIENT = client
            return client
        print("[INIT] EDGE AI: NOT ENABLED (config/models missing or load failed)")
        _EDGE_AI_CLIENT = None
        return None
    except Exception as e:
        print(f"[INIT] EDGE AI: DISABLED ({e})")
        _EDGE_AI_CLIENT = None
        return None

def edge_ai_enrich_payload(payload: dict) -> dict:
    """
    Adds extras.edge_ai block to payload.
    Never raises; never blocks trading logic.
    """
    try:
        client = _EDGE_AI_CLIENT or _init_edge_ai()
        if client and getattr(client, "enabled", False):
            return client.enrich_decision(payload)
    except Exception as e:
        payload.setdefault("extras", {})["edge_ai_error"] = str(e)
    return payload

# -----------------------------------------------------------------------------
# CONFIG / PAIRS
# -----------------------------------------------------------------------------
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
LAST_DNA_REFRESH = 0.0
DNA_REFRESH_INTERVAL = 60

VOLTRAN_CACHE = {"data": None, "last_update": 0.0}
VOLTRAN_REFRESH_INTERVAL = 30


# -----------------------------------------------------------------------------
# UTILS
# -----------------------------------------------------------------------------
def utc_now_iso() -> str:
    return datetime.utcnow().replace(microsecond=0).isoformat() + "Z"


def atomic_write_json(path: Path, obj: dict) -> None:
    """
    Prevents APEX reading half-written JSON.
    """
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(obj, ensure_ascii=False), encoding="utf-8")
    os.replace(tmp, path)


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

# Initialize Edge AI once at boot (fail-safe)
_init_edge_ai()


def send_signal_to_apex(symbol: str, action: str, size_usd: float, regime: str, extras: dict | None = None):
    signal = {
        "timestamp": datetime.now().isoformat(),
        "symbol": symbol,
        "action": action,
        "size_usd": float(size_usd),
        "regime": regime,
        "extras": extras or {},
    }

    # FAZ3.1 Edge AI observer enrichment (no behavior change)
    signal = edge_ai_enrich_payload(signal)

    try:
        atomic_write_json(APEX_SIGNAL_FILE, signal)
    except Exception as e:
        print(f"[APEX-SIGNAL] Write error: {e}")


# -----------------------------------------------------------------------------
# MAIN LOOP
# -----------------------------------------------------------------------------
async def run_fleet():
    print("=" * 70)
    print("   🌌 GODBRAIN v4.6 - VOLTRAN + EDGE AI OBSERVER")
    print("   Coins: DOGE, XRP, SOL")
    print("   Features: Anti-Whipsaw, GODLANG Pulse, Cheat Code, Blackjack DNA")
    print("   VOLTRAN: 🦅 Blackjack + 🐺 Roulette + 🦁 Chaos = FUSION")
    print("   EDGE AI: FAZ3.1 observer -> extras.edge_ai enrichment (fail-safe)")
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

    decision_engine = DecisionEngine(
        ultimate_brain=ultimate_brain,
        blackjack_multiplier_fn=blackjack_multiplier,
        pulse_consumer=PULSE_CONSUMER if PULSE_ENABLED and PULSE_CONSUMER else None,
        cheat_enabled=CHEAT_ENABLED,
        cheat_fn=get_cheat_override if CHEAT_ENABLED else None,
    )

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

                    result = await decision_engine.run_symbol_cycle(
                        symbol=symbol,
                        equity_usd=equity_usd,
                        per_coin_equity=per_coin_equity,
                        ohlcv=ohlcv,
                        voltran_factor=voltran_factor,
                        voltran_score=voltran_score,
                        signal_filter=signal_filters[symbol],
                    )

                    if not result:
                        continue

                    if result["type"] == "execute":
                        cheat_log = result.get("cheat_log")
                        if cheat_log:
                            print(cheat_log)

                        print(result["status_line"])
                        print(result["log_msg"])

                        # Persist decision log
                        try:
                            with open(AGG_DECISION_LOG, "a", encoding="utf-8") as f:
                                f.write(f"{datetime.now().isoformat()} | {result['log_msg']}\n")
                        except Exception as e:
                            print(f"[LOG] agg_decisions.log write error: {e}")

                        # Send APEX signal (includes EdgeAI enrichment)
                        send_signal_to_apex(
                            result["symbol"],
                            result["raw_action"],
                            result["size_usd"],
                            result["regime"],
                            result.get("extras", {}),
                        )

                        signal_filters[symbol].record_trade(result["raw_action"])

                    elif result["type"] == "blocked":
                        print(result["blocked_msg"])

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
        raise SystemExit(0)
