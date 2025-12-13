# -*- coding: utf-8 -*-
"""
GODBRAIN v4.3 - ANTI-WHIPSAW AGGREGATOR
Integrates: Signal Filter + Regime Cooldown + Ultimate Pack
"""
import os
import sys
import asyncio
import traceback
import pandas as pd
from datetime import datetime
from pathlib import Path
from dotenv import load_dotenv

ROOT = Path("/mnt/c/godbrain-quantum")
sys.path.insert(0, str(ROOT))
load_dotenv(ROOT / ".env")

try:
    import ccxt
    from execution.slippage_model import DynamicSlippageModel
    from risk.correlation_sizer import CorrelationAwarePositionSizer
    from ultimate_pack.ultimate_connector import UltimateConnector
    from ultimate_pack.filters.signal_filter import SignalFilter
except ImportError as e:
    print(f"[FATAL] Modules missing: {e}")
    sys.exit(1)

LOG_DIR = ROOT / "logs"
AGG_DECISION_LOG = LOG_DIR / "agg_decisions.log"
NEURAL_STREAM_LOG = LOG_DIR / "neural_stream.log"

async def run_fleet():
    print("==================================================")
    print("   🌌 GODBRAIN v4.3 (ANTI-WHIPSAW ACTIVE)        ")
    print("   Status: Cooldowns & Hysteresis Enabled         ")
    print("==================================================")

    api_key = os.getenv('OKX_API_KEY')
    secret = os.getenv('OKX_SECRET')
    passphrase = os.getenv('OKX_PASSWORD') or os.getenv('OKX_PASSPHRASE')
    
    try:
        okx = ccxt.okx({'apiKey': api_key, 'secret': secret, 'password': passphrase})
        if os.getenv("OKX_USE_SANDBOX") == "true": okx.set_sandbox_mode(True)
    except: okx = None
    
    slippage_model = DynamicSlippageModel()
    correlation_sizer = CorrelationAwarePositionSizer()
    signal_filter = SignalFilter()  # NEW: Anti-Whipsaw Filter
    
    print("[INIT] Starting Data Hub...")
    ultimate_brain = UltimateConnector()
    await ultimate_brain.initialize()
    print("[INIT] Ready.")
    
    equity_usd = 10000.0
    portfolio_risk_sum = 0.0
    
    def get_chronos_state():
        try:
            if NEURAL_STREAM_LOG.exists():
                with open(NEURAL_STREAM_LOG, 'rb') as f:
                    try: f.seek(-1024, 2); 
                    except: f.seek(0)
                    lines = f.readlines()
                    if lines and "QUANTUM_RESONANCE" in lines[-1].decode(): return True
        except: pass
        return False

    while True:
        try:
            if okx:
                try: equity_usd = float(okx.fetch_balance()['total'].get('USDT', equity_usd))
                except: pass

            is_quantum = get_chronos_state()
            
            ohlcv = pd.DataFrame()
            if okx:
                try:
                    ohlcv_raw = okx.fetch_ohlcv("BTC/USDT", "1h", limit=200)
                    if ohlcv_raw:
                        ohlcv = pd.DataFrame(ohlcv_raw, columns=['timestamp','open','high','low','close','vol'])
                        ohlcv = ohlcv.drop_duplicates(subset=['timestamp'], keep='last')
                except: pass

            if not ohlcv.empty:
                decision = await ultimate_brain.get_signal("BTC/USDT", equity_usd, ohlcv)
                
                # --- ANTI-WHIPSAW FILTERING ---
                raw_action = "HOLD"
                if decision.action in ["BUY", "STRONG_BUY"]: raw_action = "BUY"
                elif decision.action in ["SELL", "STRONG_SELL"]: raw_action = "SELL"
                
                filtered = signal_filter.filter(raw_action, decision.conviction)
                
                # Quantum Override Bypass (If Time Dilation, ignore cooldowns)
                if is_quantum:
                    filtered.should_execute = True
                    decision.reasoning += " [QUANTUM_OVERRIDE]"
                    print("  ⚡ QUANTUM RESONANCE: Bypassing Filters")

                if filtered.should_execute and raw_action != "HOLD":
                    symbol = "BTC/USDT"
                    side = "buy" if raw_action == "BUY" else "sell"
                    size_usd = decision.position_size_usd
                    
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] Eq:${equity_usd:.0f} | {decision.regime} | {raw_action} (Conv:{decision.conviction:.2f})")
                    
                    # Execution Logic
                    if okx:
                        try:
                            ob = okx.fetch_order_book(symbol, limit=20)
                            slip = slippage_model.estimate_slippage(symbol, side, size_usd, ob)
                            if slip.total_slippage_pct > 0.015:
                                print(f"  🛑 SLIPPAGE REJECT: {slip.total_slippage_pct*100:.2f}%")
                                size_usd = 0
                        except: pass
                    
                    size_usd = correlation_sizer.adjust_size(symbol, size_usd, portfolio_risk_sum)
                    
                    if size_usd > 0:
                        log_msg = f"  >>> EXECUTE: {side.upper()} {symbol} | ${size_usd:.0f} | {decision.reasoning}"
                        print(log_msg)
                        with open(AGG_DECISION_LOG, "a") as f: f.write(log_msg + "\n")
                        portfolio_risk_sum += size_usd 
                        signal_filter.record_trade(raw_action) # Record for next cooldown
                else:
                    # Log blocked signals to show filter is working
                    if raw_action != "HOLD":
                        print(f"[{datetime.now().strftime('%H:%M:%S')}] 🛡️ BLOCKED: {raw_action} -> {filtered.filter_reason}")

            else:
                print(f"[{datetime.now().strftime('%H:%M:%S')}] Waiting for market data...")

        except Exception as e:
            print(f"[ERR] Loop: {e}")
        
        await asyncio.sleep(10)

if __name__ == "__main__":
    try: asyncio.run(run_fleet())
    except KeyboardInterrupt: sys.exit(0)
