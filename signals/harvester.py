# -*- coding: utf-8 -*-
"""
GODBRAIN SIGNAL HARVESTER
Collects signals from various sources: Redis (Genetics), Godlang (Pulse), and Voltran Bridge.
"""

import os
import json
import time
import redis
from datetime import datetime
from typing import Dict, List, Optional, Tuple

from config_center import config

# Import Voltran Bridge
try:
    from genetics.voltran_bridge import get_voltran_snapshot
    VOLTRAN_ENABLED = True
except ImportError:
    VOLTRAN_ENABLED = False

class SignalHarvester:
    """Consolidates signal harvesting logic."""
    
    def __init__(self):
        self.redis_conn = self._connect_redis()
        self.active_dna = [10, 10, 234, 326, 354, 500]
        self.gen_mults = [0.10, 0.10, 2.34, 3.26, 3.54, 5.00]
        self.active_meta = None
        self.last_dna_refresh = 0.0
        
        self.voltran_cache = {"data": None, "last_update": 0.0}
        
    def _connect_redis(self):
        try:
            r = redis.Redis(
                host=config.REDIS_HOST,
                port=config.REDIS_PORT,
                password=config.REDIS_PASS,
                decode_responses=True,
                socket_timeout=5,
                socket_connect_timeout=5,
            )
            r.ping()
            return r
        except Exception as e:
            print(f"[HARVESTER] ❌ Redis connection failed: {e}")
            return None

    def _compute_multipliers_from_dna(self, dna: List[int]) -> List[float]:
        if not dna or len(dna) < 6:
            return self.gen_mults
        c, d, e, f = dna[2], dna[3], dna[4], dna[5]
        return [
            0.10,       # <50
            0.10,       # 50-59
            c / 100.0,  # 60-69
            d / 100.0,  # 70-79
            e / 100.0,  # 80-89
            f / 100.0,  # 90+
        ]

    def refresh_dna(self, force=False):
        """Fetch latest DNA from Redis. Fail-safe: returns active_dna on error."""
        try:
            now = time.time()
            if not force and (now - self.last_dna_refresh) < config.DNA_REFRESH_INTERVAL:
                return self.active_dna, self.active_meta

            self.last_dna_refresh = now
            if not self.redis_conn:
                self.redis_conn = self._connect_redis()
            
            if not self.redis_conn:
                # Still fail-safe
                return self.active_dna, self.active_meta

            raw_dna = self.redis_conn.get(config.DNA_KEY)
            raw_meta = self.redis_conn.get(config.META_KEY)
            if not raw_dna:
                return self.active_dna, self.active_meta

            dna = json.loads(raw_dna)
            if isinstance(dna, list) and len(dna) == 6:
                if dna != self.active_dna:
                    self.active_dna = dna
                    self.gen_mults = self._compute_multipliers_from_dna(dna)
                    print(f"[{datetime.now().strftime('%H:%M:%S')}] [HARVESTER] 🧬 DNA UPDATED: {dna}")

            if raw_meta:
                try:
                    self.active_meta = json.loads(raw_meta)
                except:
                    pass

            return self.active_dna, self.active_meta
        except Exception as e:
            print(f"[HARVESTER] ⚠️ DNA refresh failed, using cached. Error: {e}")
            return self.active_dna, self.active_meta

    def get_blackjack_multiplier(self, quantum_score: float) -> float:
        """Returns multiplier based on current DNA and signal conviction."""
        try:
            s = max(0.0, min(100.0, float(quantum_score)))
            if s >= 90: return self.gen_mults[5]
            if s >= 80: return self.gen_mults[4]
            if s >= 70: return self.gen_mults[3]
            if s >= 60: return self.gen_mults[2]
            if s >= 50: return self.gen_mults[1]
            return self.gen_mults[0]
        except Exception as e:
            print(f"[HARVESTER] ⚠️ Multiplier calc error: {e}")
            return 0.1 # Absolute safe minimum

    def get_voltran_factor(self, force=False) -> Tuple[float, float, str]:
        """Fetch Voltran ecosystem factor. Fail-safe: returns 1.0 on error."""
        if not VOLTRAN_ENABLED:
            return 1.0, 50.0, "DISABLED"

        try:
            now = time.time()
            if not force and self.voltran_cache["data"] and (now - self.voltran_cache["last_update"]) < config.VOLTRAN_REFRESH_INTERVAL:
                d = self.voltran_cache["data"]
                return d.get("voltran_factor", 1.0), d.get("voltran_score", 50), d.get("rank", "?")

            snap = get_voltran_snapshot()
            self.voltran_cache["data"] = snap
            self.voltran_cache["last_update"] = now
            return snap.get("voltran_factor", 1.0), snap.get("voltran_score", 50), snap.get("rank", "?")
        except Exception as e:
            print(f"[HARVESTER] ⚠️ Voltran fetch error: {e}")
            return 1.0, 50.0, "ERROR"

if __name__ == "__main__":
    harvester = SignalHarvester()
    dna, meta = harvester.refresh_dna(force=True)
    vf, vs, rank = harvester.get_voltran_factor(force=True)
    print(f"DNA: {dna}")
    print(f"Voltran: {rank} (Score: {vs:.1f}, Factor: {vf:.2f}x)")
