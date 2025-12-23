#!/usr/bin/env python3
"""
🦅🐺🦁 VOLTRAN GENETICS - All Labs Runner
Runs Blackjack, Roulette, and Chaos Labs in parallel threads
"""

import os
import sys
import threading
import time

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

from config_center import config

def run_blackjack():
    from genetics.blackjack_lab import run_evolution
    try:
        run_evolution(
            redis_host=config.REDIS_HOST,
            redis_port=config.REDIS_PORT,
            redis_pass=config.REDIS_PASS
        )
    except Exception as e:
        print(f"[BLACKJACK] Error: {e}")

def run_roulette():
    from genetics.roulette_lab import run_evolution
    try:
        run_evolution(
            redis_host=config.REDIS_HOST,
            redis_port=config.REDIS_PORT,
            redis_pass=config.REDIS_PASS
        )
    except Exception as e:
        print(f"[ROULETTE] Error: {e}")

def run_chaos():
    from genetics.chaos_lab import run_cosmic_evolution
    try:
        run_cosmic_evolution(
            redis_host=config.REDIS_HOST,
            redis_port=config.REDIS_PORT,
            redis_pass=config.REDIS_PASS
        )
    except Exception as e:
        print(f"[CHAOS] Error: {e}")

if __name__ == "__main__":
    print("=" * 60)
    print("  🦅🐺🦁 VOLTRAN GENETICS LABS")
    print("  Starting all evolution engines...")
    print("=" * 60)
    
    threads = [
        threading.Thread(target=run_blackjack, name="Blackjack", daemon=True),
        threading.Thread(target=run_roulette, name="Roulette", daemon=True),
        threading.Thread(target=run_chaos, name="Chaos", daemon=True),
    ]
    
    for t in threads:
        print(f"[LAUNCHER] Starting {t.name} Lab...")
        t.start()
        time.sleep(2)  # Stagger start
    
    print("\n[LAUNCHER] All labs running. Press Ctrl+C to stop.")
    
    try:
        while True:
            time.sleep(60)
    except KeyboardInterrupt:
        print("\n[LAUNCHER] Shutting down...")

