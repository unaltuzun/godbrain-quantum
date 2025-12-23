#!/usr/bin/env python3
"""
CHEAT CODE SCANNER - Continuous universe monitoring
"""
import sys
import time
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/mnt/c/godbrain-quantum')
from core.cheat_code import CheatCodeEngine

SIGNAL_FILE = Path("/mnt/c/godbrain-quantum/logs/cheat_signals.json")
SCAN_INTERVAL = 300  # 5 dakika

def main():
    print("=" * 60)
    print("  🎮 CHEAT CODE SCANNER STARTING")
    print("  Interval: 5 minutes")
    print("=" * 60)
    
    engine = CheatCodeEngine()
    
    symbols = [
        'BTC/USDT:USDT', 'ETH/USDT:USDT', 'SOL/USDT:USDT',
        'XRP/USDT:USDT', 'DOGE/USDT:USDT', 'PEPE/USDT:USDT',
        'SHIB/USDT:USDT', 'FLOKI/USDT:USDT', 'BONK/USDT:USDT'
    ]
    
    while True:
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Scanning universe...")
            signals = engine.scan_universe(symbols)
            
            # Save to file for AGG to read
            signal_data = {
                "timestamp": datetime.now().isoformat(),
                "signals": [s.to_dict() for s in signals],
                "universe": {
                    "coherence": engine.read_universe_state().coherence,
                    "quantum_active": engine.read_universe_state().quantum_active,
                    "flow_multiplier": engine.read_universe_state().flow_multiplier
                }
            }
            
            with open(SIGNAL_FILE, 'w') as f:
                json.dump(signal_data, f, indent=2)
            
            if signals:
                print(f"[CHEAT] 🎯 {len(signals)} signals found!")
                for s in signals[:3]:
                    print(f"  → {s.symbol}: {s.action} @ {s.confidence:.1%}")
            else:
                print("[CHEAT] ⚪ No opportunities")
            
            time.sleep(SCAN_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n[CHEAT] Scanner stopped")
            break
        except Exception as e:
            print(f"[CHEAT] Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
