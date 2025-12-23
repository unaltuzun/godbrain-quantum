import os
import redis
import json
import time
from datetime import datetime

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "16379"))
REDIS_PASS = os.getenv("REDIS_PASS", "voltran2024")

def audit():
    try:
        r = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, password=REDIS_PASS, decode_responses=True)
        r.ping()
        print("✅ REDIS CONNECTED\n")
    except Exception as e:
        print(f"❌ REDIS ERROR: {e}")
        return

    keys = {
        "Blackjack": "godbrain:genetics:best_meta",
        "Roulette": "godbrain:roulette:best_meta",
        "Chaos": "godbrain:chaos:best_meta",
        "Trading Model": "godbrain:model:linear",
        "Active DNA": "godbrain:trading:active_dna"
    }

    print(f"{'LAB':<15} | {'SCORE':<10} | {'GEN':<10} | {'LAST UPDATED'}")
    print("-" * 55)

    for name, key in keys.items():
        val = r.get(key)
        if val:
            data = json.loads(val)
            score = data.get("best_profit", data.get("score", data.get("cosmic_harmony", "N/A")))
            gen = data.get("gen", data.get("generation", "N/A"))
            # Pushed at for Trading Model
            updated = data.get("timestamp", data.get("updated_at", data.get("pushed_at", "Unknown")))
            
            # Format score if numeric
            if isinstance(score, (int, float)):
                score_str = f"{score:.2f}"
            else:
                score_str = str(score)
                
            print(f"{name:<15} | {score_str:<10} | {gen:<10} | {updated}")
        else:
            print(f"{name:<15} | {'MISSING':<10} | {'N/A':<10} | N/A")

if __name__ == "__main__":
    audit()
