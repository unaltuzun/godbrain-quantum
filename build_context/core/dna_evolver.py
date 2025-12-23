#!/usr/bin/env python3
"""
DNA EVOLUTION DAEMON
Genomları sürekli evrimleştirir
"""
import sys
import time
import json
from pathlib import Path
from datetime import datetime

sys.path.insert(0, '/mnt/c/godbrain-quantum')
from core.dna_engine_academy import DNAStrategyParams, MarketEnv, DNAEvolutionEngine

GENOME_FILE = Path("/mnt/c/godbrain-quantum/logs/active_genome.json")
EVOLUTION_LOG = Path("/mnt/c/godbrain-quantum/logs/evolution_history.log")
EVOLVE_INTERVAL = 600  # 10 dakika

# Current active genome
current_genome = DNAStrategyParams(
    stop_loss_pct=-2.0,
    take_profit_pct=5.0,
    rsi_buy_level=30,
    rsi_sell_level=70,
    position_size_factor=0.5
)

def load_genome():
    global current_genome
    try:
        if GENOME_FILE.exists():
            with open(GENOME_FILE, 'r') as f:
                data = json.load(f)
            current_genome = DNAStrategyParams(**data['params'])
            print(f"[DNA] Loaded genome: SL={current_genome.stop_loss_pct}% TP={current_genome.take_profit_pct}%")
    except Exception as e:
        print(f"[DNA] Using default genome: {e}")

def save_genome():
    data = {
        "timestamp": datetime.now().isoformat(),
        "params": {
            "stop_loss_pct": current_genome.stop_loss_pct,
            "take_profit_pct": current_genome.take_profit_pct,
            "rsi_buy_level": current_genome.rsi_buy_level,
            "rsi_sell_level": current_genome.rsi_sell_level,
            "position_size_factor": current_genome.position_size_factor
        },
        "generation": getattr(current_genome, 'generation', 1)
    }
    with open(GENOME_FILE, 'w') as f:
        json.dump(data, f, indent=2)

def get_pnl_from_positions():
    """Get current PnL from OKX"""
    try:
        import ccxt
        import os
        from dotenv import load_dotenv
        load_dotenv('/mnt/c/godbrain-quantum/.env')
        
        okx = ccxt.okx({
            'apiKey': os.getenv('OKX_API_KEY'),
            'secret': os.getenv('OKX_SECRET'),
            'password': os.getenv('OKX_PASSWORD')
        })
        
        positions = okx.fetch_positions()
        total_pnl = sum(float(p.get('unrealizedPnl', 0)) for p in positions if float(p.get('contracts', 0)) > 0)
        return total_pnl
    except:
        return 0

def evolve_genome(pnl: float, market_env: MarketEnv):
    """Genom'u PnL'ye göre evrimleştir"""
    global current_genome
    
    # Basit evrim: PnL pozitifse parametreleri güçlendir, negatifse zayıflat
    mutation_rate = 0.1
    
    if pnl > 0:
        # Başarılı - daha agresif ol
        current_genome.position_size_factor = min(1.0, current_genome.position_size_factor * (1 + mutation_rate))
        current_genome.take_profit_pct *= (1 - mutation_rate * 0.5)  # Daha sık kar al
        print(f"[DNA] 🧬 Positive evolution: size_factor → {current_genome.position_size_factor:.2f}")
    elif pnl < -1:
        # Kayıp - daha muhafazakar ol
        current_genome.position_size_factor = max(0.1, current_genome.position_size_factor * (1 - mutation_rate))
        current_genome.stop_loss_pct = max(-5, current_genome.stop_loss_pct * (1 - mutation_rate))  # Daha sıkı SL
        print(f"[DNA] 🧬 Defensive evolution: size_factor → {current_genome.position_size_factor:.2f}")
    else:
        print(f"[DNA] ⚪ No evolution needed (PnL: ${pnl:.2f})")
    
    # Quantum resonance boost
    if market_env.quantum_resonance_active:
        current_genome.position_size_factor = min(1.0, current_genome.position_size_factor * 1.1)
        print(f"[DNA] 🔮 Quantum boost applied")

def main():
    print("=" * 60)
    print("  🧬 DNA EVOLUTION DAEMON STARTING")
    print("  Interval: 10 minutes")
    print("=" * 60)
    
    load_genome()
    generation = 1
    
    while True:
        try:
            print(f"\n[{datetime.now().strftime('%H:%M:%S')}] Generation {generation}")
            
            # Get current state
            pnl = get_pnl_from_positions()
            print(f"[DNA] Current PnL: ${pnl:.2f}")
            
            # Read quantum state from pulse
            try:
                with open('/mnt/c/godbrain-quantum/logs/godlang_pulse_state.json', 'r') as f:
                    pulse = json.load(f)
                quantum_active = pulse.get('quantum_boost_active', False)
            except:
                quantum_active = False
            
            market_env = MarketEnv(
                risk_score=0,
                market_pressure=0.5,
                prometheus_direction="NEUTRAL",
                flow_multiplier=1.0,
                quantum_resonance_active=quantum_active
            )
            
            # Evolve
            evolve_genome(pnl, market_env)
            save_genome()
            
            # Log
            with open(EVOLUTION_LOG, 'a') as f:
                f.write(f"{datetime.now().isoformat()} | Gen:{generation} | PnL:${pnl:.2f} | SL:{current_genome.stop_loss_pct:.1f}% | TP:{current_genome.take_profit_pct:.1f}% | Size:{current_genome.position_size_factor:.2f}\n")
            
            generation += 1
            time.sleep(EVOLVE_INTERVAL)
            
        except KeyboardInterrupt:
            print("\n[DNA] Evolution stopped")
            save_genome()
            break
        except Exception as e:
            print(f"[DNA] Error: {e}")
            time.sleep(60)

if __name__ == "__main__":
    main()
