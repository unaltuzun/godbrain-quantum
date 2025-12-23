#!/usr/bin/env python3
"""
🧬 DNA AUTO PUSHER - 24/7 Genetic Trading Sync
===============================================
Automatically syncs the best DNA from physics labs to trading system.

Flow:
  Lab DNA → Redis → DNA Pusher → Trading Model → Voltran

Runs continuously, checking every 60 seconds for better DNA.
"""

import os
import sys
import json
import time
import math
import redis
from datetime import datetime
from typing import Dict, Optional, Tuple

# Redis Configuration
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "16379"))
REDIS_PASS = os.getenv("REDIS_PASS", "voltran2024")

# DNA Sources
DNA_SOURCES = {
    "blackjack": {
        "meta_key": "godbrain:genetics:best_meta",
        "dna_key": "godbrain:genetics:best_dna",
        "score_field": "best_profit",
    },
    "roulette": {
        "meta_key": "godbrain:roulette:best_meta",
        "dna_key": "godbrain:roulette:best_dna",
        "score_field": "score",
    },
    "chaos": {
        "meta_key": "godbrain:chaos:best_meta",
        "dna_key": "godbrain:chaos:best_dna",
        "score_field": "cosmic_harmony",
    },
}

# Trading Model Key
TRADING_MODEL_KEY = "godbrain:model:linear"
ACTIVE_DNA_KEY = "godbrain:trading:active_dna"

# Thresholds
MIN_SCORE_THRESHOLD = 70.0  # Minimum score to push to trading
CHECK_INTERVAL = 60  # Seconds between checks


class DNAPusher:
    """Automatically pushes best DNA to trading system."""
    
    def __init__(self):
        self.redis = None
        self.current_dna = None
        self.current_score = 0.0
        self.push_count = 0
        
    def connect(self) -> bool:
        """Connect to Redis."""
        try:
            self.redis = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASS,
                decode_responses=True,
                socket_timeout=10
            )
            self.redis.ping()
            print(f"[DNA-PUSHER] ✅ Connected to Redis {REDIS_HOST}:{REDIS_PORT}")
            return True
        except Exception as e:
            print(f"[DNA-PUSHER] ❌ Redis connection failed: {e}")
            return False
    
    def get_dna_score(self, source: str) -> Tuple[float, int, Optional[Dict]]:
        """Get score and DNA from a source."""
        if not self.redis:
            return 0.0, 0, None
            
        config = DNA_SOURCES.get(source)
        if not config:
            return 0.0, 0, None
        
        try:
            meta_raw = self.redis.get(config["meta_key"])
            dna_raw = self.redis.get(config["dna_key"])
            
            if not meta_raw:
                return 0.0, 0, None
            
            meta = json.loads(meta_raw)
            dna = json.loads(dna_raw) if dna_raw else None
            
            gen = meta.get("gen", 0)
            
            # Calculate normalized score (0-100)
            raw_score = meta.get(config["score_field"], 0)
            
            if source == "blackjack":
                # Profit-based scoring
                score = min(100, 50 + math.log10(max(1, raw_score)) * 10)
            elif source == "chaos":
                # Harmony is already 0-100
                score = raw_score
            else:
                # Default scoring
                score = min(100, raw_score)
            
            return score, gen, dna
            
        except Exception as e:
            print(f"[DNA-PUSHER] Error getting {source} DNA: {e}")
            return 0.0, 0, None
    
    def get_best_dna(self) -> Tuple[str, float, int, Optional[Dict]]:
        """Find the best DNA across all sources."""
        best_source = None
        best_score = 0.0
        best_gen = 0
        best_dna = None
        
        for source in DNA_SOURCES:
            score, gen, dna = self.get_dna_score(source)
            if score > best_score and dna:
                best_source = source
                best_score = score
                best_gen = gen
                best_dna = dna
        
        return best_source, best_score, best_gen, best_dna
    
    def dna_to_trading_model(self, source: str, dna: Dict, score: float) -> Dict:
        """Convert DNA to trading model format."""
        # Extract parameters from DNA based on source
        if source == "blackjack":
            # Blackjack DNA format: [param1, param2, ...]
            if isinstance(dna, list) and len(dna) >= 4:
                return {
                    "version": f"DNA-{source.upper()}-GEN",
                    "source": source,
                    "score": score,
                    "threshold": min(0.99, 0.7 + (score / 500)),
                    "slope": dna[0] / 100000 if dna[0] else 0.0005,
                    "intercept": -dna[1] / 10 if len(dna) > 1 else -48,
                    "leverage_factor": min(2.0, 0.8 + score / 100),
                    "raw_dna": dna,
                    "pushed_at": datetime.now().isoformat(),
                }
        elif source == "chaos":
            # Chaos DNA format: [param1, param2, ...]
            if isinstance(dna, list) and len(dna) >= 4:
                return {
                    "version": f"DNA-{source.upper()}-HARMONY",
                    "source": source,
                    "score": score,
                    "threshold": min(0.98, 0.75 + (score / 400)),
                    "cosmic_factor": dna[0] / 100 if dna[0] else 1.0,
                    "harmony_weight": dna[2] / dna[4] if len(dna) > 4 and dna[4] else 0.5,
                    "raw_dna": dna,
                    "pushed_at": datetime.now().isoformat(),
                }
        elif source == "roulette":
            # Roulette DNA format
            if isinstance(dna, list) and len(dna) >= 3:
                return {
                    "version": f"DNA-{source.upper()}-SPIN",
                    "source": source,
                    "score": score,
                    "threshold": min(0.97, 0.7 + (score / 300)),
                    "bet_factor": dna[0] / dna[1] if len(dna) > 1 and dna[1] else 1.0,
                    "raw_dna": dna,
                    "pushed_at": datetime.now().isoformat(),
                }
        
        # Default fallback
        return {
            "version": f"DNA-UNKNOWN",
            "source": source,
            "score": score,
            "raw_dna": dna,
            "pushed_at": datetime.now().isoformat(),
        }
    
    def push_to_trading(self, source: str, dna: Dict, score: float, gen: int) -> bool:
        """Push DNA to trading model."""
        try:
            model = self.dna_to_trading_model(source, dna, score)
            
            # Update trading model
            self.redis.set(TRADING_MODEL_KEY, json.dumps(model))
            
            # Store active DNA info
            active_info = {
                "source": source,
                "score": score,
                "gen": gen,
                "dna": dna,
                "pushed_at": datetime.now().isoformat(),
                "push_count": self.push_count + 1,
            }
            self.redis.set(ACTIVE_DNA_KEY, json.dumps(active_info))
            
            self.current_dna = dna
            self.current_score = score
            self.push_count += 1
            
            print(f"[DNA-PUSHER] 🚀 PUSHED: {source} DNA (score={score:.1f}, gen={gen})")
            return True
            
        except Exception as e:
            print(f"[DNA-PUSHER] ❌ Push failed: {e}")
            return False
    
    def run_once(self) -> bool:
        """Run one check cycle."""
        source, score, gen, dna = self.get_best_dna()
        
        if not dna:
            print(f"[DNA-PUSHER] ⏳ No valid DNA found, waiting...")
            return False
        
        # Check if we should push
        if score < MIN_SCORE_THRESHOLD:
            print(f"[DNA-PUSHER] ⏳ Best DNA ({source}) score {score:.1f} below threshold {MIN_SCORE_THRESHOLD}")
            return False
        
        # Check if this is better than current
        if score <= self.current_score and dna == self.current_dna:
            print(f"[DNA-PUSHER] ✓ Current DNA still optimal ({source}: {score:.1f})")
            return False
        
        # Push the new DNA
        return self.push_to_trading(source, dna, score, gen)
    
    def run_forever(self):
        """Run the pusher continuously."""
        print("""
╔═══════════════════════════════════════════════════════════╗
║           🧬 DNA AUTO PUSHER - 24/7 ACTIVE                ║
║           Syncing Lab DNA → Trading System                 ║
╚═══════════════════════════════════════════════════════════╝
        """)
        
        if not self.connect():
            print("[DNA-PUSHER] Failed to connect, exiting...")
            sys.exit(1)
        
        print(f"[DNA-PUSHER] Check interval: {CHECK_INTERVAL}s")
        print(f"[DNA-PUSHER] Min score threshold: {MIN_SCORE_THRESHOLD}")
        print(f"[DNA-PUSHER] Sources: {list(DNA_SOURCES.keys())}")
        print()
        
        while True:
            try:
                self.run_once()
            except Exception as e:
                print(f"[DNA-PUSHER] Error in cycle: {e}")
                # Reconnect on error
                self.connect()
            
            time.sleep(CHECK_INTERVAL)


def main():
    pusher = DNAPusher()
    pusher.run_forever()


if __name__ == "__main__":
    main()
