# -*- coding: utf-8 -*-
"""
GODBRAIN v4.4 - MULTI-COIN ANTI-WHIPSAW AGGREGATOR
Trades: DOGE, XRP, SOL (low minimum coins)
"""
import os
import sys
import asyncio
import pandas as pd
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path("/mnt/c/godbrain-quantum")
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

try:
    import ccxt
    from ultimate_pack.ultimate_connector import UltimateConnector
    from ultimate_pack.filters.signal_filter import SignalFilter
except ImportError as e:
    print(f"[FATAL] Modules missing: {e}")
    sys.exit(1)

LOG_DIR = ROOT / "logs"
AGG_DECISION_LOG = LOG_DIR / "agg_decisions.log"

# Multi-coin config
TRADING_PAIRS = [
    "DOGE/USDT:USDT",
    "XRP/USDT:USDT",
    "SOL/USDT:USDT",
]

async def run_fleet():
    print("=" * 60)
    print("   🌌 GODBRAIN v4.4 (MULTI-COIN EDITION)")
    print("   Coins: DOGE, XRP, SOL")
    print("   Anti-Whipsaw: ACTIVE")
    print("=" * 60)

    api_key = os.getenv('OKX_API_KEY')
    secret = os.getenv('OKX_SECRET')
    passphrase = os.getenv('OKX_PASSWORD') or os.getenv('OKX_PASSPHRASE')
    
    try:
        okx = ccxt.okx({'apiKey': api_key, 'secret': secret, 'password': passphrase})
        if os.getenv("OKX_USE_SANDBOX") == "true":
            okx.set_sandbox_mode(True)
        okx.load_markets()
    except Exception as e:
        print(f"[FATAL] OKX init failed: {e}")
        okx = None
    
    # Per-coin signal filters (separate cooldowns)
    signal_filters = {pair: SignalFilter() for pair in TRADING_PAIRS}
    
    print("[INIT] Starting Ultimate Brain...")
    ultimate_brain = UltimateConnector()
    await ultimate_brain.initialize()
    print("[INIT] Ready.")
    print(f"[INIT] Trading pairs: {', '.join(TRADING_PAIRS)}")
    
    equity_usd = 23.0
    
    while True:
        try:
            # Fetch equity
            if okx:
                try:
                    balance = okx.fetch_balance()
                    equity_usd = float(balance['total'].get('USDT', equity_usd))
                except:
                    pass
            
            # Per-coin allocation
            per_coin_equity = equity_usd / len(TRADING_PAIRS)
            
            # Process each coin
            for symbol in TRADING_PAIRS:
                try:
                    # Fetch OHLCV
                    ohlcv = pd.DataFrame()
                    if okx:
                        try:
                            ohlcv_raw = okx.fetch_ohlcv(symbol, "1h", limit=200)
                            if ohlcv_raw:
                                ohlcv = pd.DataFrame(ohlcv_raw, columns=['timestamp','open','high','low','close','vol'])
                        except Exception as e:
                            print(f"[{symbol}] OHLCV error: {e}")
                            continue
                    
                    if ohlcv.empty:
                        continue
                    
                    # Get signal
                    decision = await ultimate_brain.get_signal(symbol, per_coin_equity, ohlcv)
                    
                    # Determine action
                    raw_action = "HOLD"
                    if decision.action in ["BUY", "STRONG_BUY"]:
                        raw_action = "BUY"
                    elif decision.action in ["SELL", "STRONG_SELL"]:
                        raw_action = "SELL"
                    
                    # Apply filter (per-coin cooldown)
                    filtered = signal_filters[symbol].filter(raw_action, decision.conviction)
                    
                    ts = datetime.now().strftime('%H:%M:%S')
                    coin_short = symbol.split('/')[0]
                    
                    if filtered.should_execute and raw_action != "HOLD":
                        size_usd = max(2, decision.position_size_usd)  # Min $2
                        
                        print(f"[{ts}] {coin_short} | Eq:${per_coin_equity:.0f} | {decision.regime} | {raw_action} (Conv:{decision.conviction:.2f})")
                        
                        log_msg = f"  >>> EXECUTE: {raw_action} {symbol} | ${size_usd:.0f} | Regime:{decision.regime}"
                        print(log_msg)
                        
                        with open(AGG_DECISION_LOG, "a") as f:
                            f.write(log_msg + "\n")
                        
                        signal_filters[symbol].record_trade(raw_action)
                    
                    elif raw_action != "HOLD":
                        print(f"[{ts}] {coin_short} 🛡️ BLOCKED: {raw_action} -> {filtered.filter_reason}")
                
                except Exception as e:
                    print(f"[{symbol}] Error: {e}")
                    continue
            
        except Exception as e:
            print(f"[ERR] Loop: {e}")
        
        await asyncio.sleep(10)

if __name__ == "__main__":
    try:
        asyncio.run(run_fleet())
    except KeyboardInterrupt:
        print("\n[SHUTDOWN] Goodbye!")
        sys.exit(0)