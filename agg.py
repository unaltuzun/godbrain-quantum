# -*- coding: utf-8 -*-
"""
GODBRAIN v5.0 - UNIFIED ORCHESTRATOR
🦅 Blackjack + 🐺 Roulette + 🦁 Chaos = VOLTRAN
Simple is Great. Stability is Alpha.
"""

import asyncio
import time
from datetime import datetime
import pandas as pd
import ccxt

from config_center import config
from signals.harvester import SignalHarvester
from execution.executor import GodbrainExecutor
from engines.decision_engine import DecisionEngine
from ultimate_pack.ultimate_connector import UltimateConnector
from ultimate_pack.filters.signal_filter import SignalFilter

# Initialize Components
harvester = SignalHarvester()
ultimate_brain = UltimateConnector()
signal_filters = {symbol: SignalFilter() for symbol in config.TRADING_PAIRS}

# Exchange Setup
okx = ccxt.okx({
    "apiKey": config.OKX_KEY,
    "secret": config.OKX_SECRET,
    "password": config.OKX_PASS,
    "enableRateLimit": True,
    "options": {"defaultType": "swap"}
}) if config.OKX_KEY else None

executor = GodbrainExecutor(okx)

# Edge AI Integration
def get_edge_ai_enrichment(payload: dict) -> dict:
    """Fail-safe Edge AI observer enrichment."""
    if not config.EDGE_AI_ENABLED: return payload
    try:
        from edge_ai.inference import EdgeInferenceClient
        client = EdgeInferenceClient(str(config.EDGE_AI_CONFIG))
        if getattr(client, "enabled", False):
            return client.enrich_decision(payload)
    except: pass
    return payload

from aiohttp import web

# Health Metrics
HEARTBEAT = {
    "status": "STARTING",
    "boot_time": time.time(),
    "last_success": 0.0,
    "error_count": 0,
    "total_loops": 0
}

async def health_check(request):
    uptime = time.time() - HEARTBEAT["boot_time"]
    data = {
        "status": HEARTBEAT["status"],
        "uptime_sec": int(uptime),
        "last_success_ts": HEARTBEAT["last_success"],
        "error_count": HEARTBEAT["error_count"],
        "total_loops": HEARTBEAT["total_loops"],
        "version": "5.0-Stabilized"
    }
    return web.json_response(data)

async def start_health_server():
    app = web.Application()
    app.router.add_get('/health', health_check)
    runner = web.AppRunner(app)
    await runner.setup()
    site = web.TCPSite(runner, '0.0.0.0', 8080)
    await site.start()
    print("[HEALTH] Server active on port 8080")

async def main_loop():
    print(f"🚀 GODBRAIN ORCHESTRATOR ACTIVE | Mode: {'LIVE' if config.APEX_LIVE else 'Sim'}")
    
    # Start health server in background
    await start_health_server()
    
    # Initialize Ultimate Pack
    await ultimate_brain.initialize()
    
    # Decision Engine Config
    decision_engine = DecisionEngine(
        ultimate_brain=ultimate_brain,
        blackjack_multiplier_fn=harvester.get_blackjack_multiplier,
        cheat_enabled=False
    )

# Initialize Redis Connection
    import redis
    redis_client = None
    try:
        redis_client = redis.Redis(
            host=config.REDIS_HOST,
            port=config.REDIS_PORT,
            password=config.REDIS_PASS,
            decode_responses=True,
            socket_timeout=5
        )
        print(f"[INIT] Redis connected: {config.REDIS_HOST}:{config.REDIS_PORT}")
    except Exception as re:
        print(f"[INIT] Redis connection failed: {re}")

    HEARTBEAT["status"] = "OK"

    while True:
        loop_start = time.time()
        HEARTBEAT["total_loops"] += 1
        try:
            # 1) Refresh Signals
            harvester.refresh_dna()
            voltran_factor, voltran_score, rank = harvester.get_voltran_factor()
            
            # 2) Fetch Balance & Equity
            equity_usd = 1000.0 # Fallback
            per_coin_equity = 1000.0
            if okx:
                try:
                    balance = okx.fetch_balance()
                    equity_usd = float(balance["total"].get("USDT", 1000.0))
                    free_usdt = float(balance["free"].get("USDT", 0))
                    
                    # CRITICAL: Divide equity among trading pairs to avoid margin conflicts
                    num_pairs = len(config.TRADING_PAIRS) or 1
                    per_coin_equity = equity_usd / num_pairs
                    print(f"[LOOP] 💰 Equity Split: ${equity_usd:.0f} / {num_pairs} pairs = ${per_coin_equity:.0f}/coin")
                    
                    # 2.1) Persist to Redis for Mobile App
                    if redis_client:
                        try:
                            import json
                            snapshot = {
                                "equity": equity_usd,
                                "pnl": per_coin_equity, # Simplified P&L tracking
                                "voltran_score": voltran_score,
                                "dna_generation": 7060, # Fallback until real genetics link is confirmed
                                "timestamp": time.time(),
                                "status": HEARTBEAT["status"]
                            }
                            redis_client.set("state:voltran:snapshot", json.dumps(snapshot))
                            redis_client.set("state:equity:live", str(equity_usd))
                        except Exception as rex:
                            print(f"[LOOP] Redis write error: {rex}")
                        
                except Exception as be:
                    print(f"[LOOP] ⚠️ Balance fetch error: {be}")
                    HEARTBEAT["error_count"] += 1

            # 3) Process Symbols
            for symbol in config.TRADING_PAIRS:
                try:
                    # Fetch OHLCV
                    ohlcv_raw = []
                    if okx:
                        try:
                            ohlcv_raw = okx.fetch_ohlcv(symbol, "1h", limit=100)
                        except Exception as oe:
                            print(f"[{symbol}] ⚠️ OHLCV fetch error: {oe}")
                            HEARTBEAT["error_count"] += 1
                            continue
                            
                    if not ohlcv_raw: continue
                    
                    df = pd.DataFrame(ohlcv_raw, columns=["timestamp", "open", "high", "low", "close", "vol"])
                    
                    # Run Decision Engine
                    result = await decision_engine.run_symbol_cycle(
                        symbol=symbol,
                        equity_usd=equity_usd,
                        per_coin_equity=per_coin_equity,
                        ohlcv=df,
                        voltran_factor=voltran_factor,
                        voltran_score=voltran_score,
                        signal_filter=signal_filters[symbol]
                    )

                    if not result: continue

                    # Log & Execution
                    if result["type"] == "execute":
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] {result['status_line']}\n  {result['log_msg']}")
                        
                        # Edge AI Enrichment
                        enriched_payload = get_edge_ai_enrichment(result.get("extras", {}))
                        
                        # Live Trade
                        await executor.execute_trade(symbol, result["raw_action"], result["size_usd"])

                except Exception as sym_e:
                    print(f"[{symbol}] ❌ Symbol Processing Error: {sym_e}")
                    HEARTBEAT["error_count"] += 1

            HEARTBEAT["last_success"] = time.time()

        except Exception as e:
            print(f"[LOOP] 💀 CRITICAL GLOBAL ERROR: {e}")
            HEARTBEAT["error_count"] += 1
            HEARTBEAT["status"] = "DEGRADED"
        
        # Fixed interval sleep (adjusting for processing time)
        elapsed = time.time() - loop_start
        wait_time = max(5, 60 - elapsed)
        await asyncio.sleep(wait_time)

if __name__ == "__main__":
    try:
        asyncio.run(main_loop())
    except KeyboardInterrupt:
        print("\n[BYE] Godbrain resting.")
