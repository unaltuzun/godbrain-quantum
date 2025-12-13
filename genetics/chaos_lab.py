#!/usr/bin/env python3
"""
🦁 CHAOS LAB - Cosmic Entropy Evolution
Tests DNA against Lorenz, Logistic Map, Fibonacci resonance
"""

import math
import random
import json
import time
from concurrent.futures import ProcessPoolExecutor
from typing import List, Tuple

import os

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

# Environment-aware Redis config
# Default port 16379 matches main system (god_dashboard, market_feed)
# Docker overrides with REDIS_PORT=6379 from docker-compose.yml
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.getenv('REDIS_PORT', '16379'))
REDIS_PASS = os.getenv('REDIS_PASS', 'voltran2024')

POPULATION_SIZE = 50
ITERATIONS = 5000
STARTING_CAPITAL = 10000

CHAOS_DNA_KEY = "godbrain:chaos:best_dna"
CHAOS_META_KEY = "godbrain:chaos:best_meta"

PHI = (1 + math.sqrt(5)) / 2

class ChaosUniverse:
    def __init__(self):
        self.lx, self.ly, self.lz = 1.0, 1.0, 1.0
        self.logistic_x = 0.5
        self.t = 0
    
    def step(self) -> float:
        self.t += 1
        
        # Lorenz
        dt = 0.01
        dx = 10 * (self.ly - self.lx) * dt
        dy = (self.lx * (28 - self.lz) - self.ly) * dt
        dz = (self.lx * self.ly - 8/3 * self.lz) * dt
        self.lx += dx
        self.ly += dy
        self.lz += dz
        lorenz = (self.lx + self.ly) / 50.0
        
        # Logistic
        self.logistic_x = 3.9 * self.logistic_x * (1 - self.logistic_x)
        logistic = (self.logistic_x - 0.5) * 2
        
        # Combine
        combined = lorenz * 0.4 + logistic * 0.4 + random.gauss(0, 0.1) * 0.2
        return combined * 0.05
    
    def get_regime(self) -> int:
        if self.lx > 0:
            return 0 if self.ly > 0 else 1
        return 2 if self.ly < 0 else 3
    
    def get_chaos_level(self) -> float:
        x = self.logistic_x
        lyap = abs(math.log(abs(3.9 * (1 - 2*x)) + 0.001))
        return min(1.0, lyap / 2.0)

def evaluate_cosmic(dna: List[int]) -> Tuple[float, float, float, float]:
    """Returns: (final_capital, max_dd, sharpe, cosmic_harmony)"""
    universe = ChaosUniverse()
    capital = STARTING_CAPITAL
    peak = capital
    max_dd = 0
    returns = []
    
    for _ in range(ITERATIONS):
        regime = universe.get_regime()
        chaos = universe.get_chaos_level()
        
        # Risk mult from DNA
        regime_mult = dna[regime] / 100.0
        chaos_mult = dna[4 if chaos < 0.3 else 5] / 100.0
        risk_mult = math.sqrt(regime_mult * chaos_mult)
        risk_mult = max(0.05, min(2.0, risk_mult))
        
        price_change = universe.step()
        position = capital * 0.1 * risk_mult
        pnl = position * price_change
        capital += pnl
        
        if capital > 0:
            returns.append(pnl / capital)
        
        if capital > peak:
            peak = capital
        dd = (peak - capital) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)
        
        if capital <= 0:
            break
    
    # Sharpe
    if len(returns) > 1:
        avg = sum(returns) / len(returns)
        std = math.sqrt(sum((r-avg)**2 for r in returns) / len(returns))
        sharpe = (avg / std) * math.sqrt(252) if std > 0 else 0
    else:
        sharpe = 0
    
    # Cosmic harmony
    phi_scores = []
    for i in range(5):
        if dna[i] > 0:
            ratio = dna[i+1] / dna[i]
            phi_scores.append(max(0, 1 - abs(ratio - PHI) / PHI))
    phi_align = sum(phi_scores) / len(phi_scores) if phi_scores else 0
    
    survival = 1.0 if capital > STARTING_CAPITAL * 0.5 else 0.5
    dd_pen = max(0, 1 - max_dd * 2)
    sharpe_bon = min(1, max(0, sharpe / 2))
    
    harmony = (phi_align * 0.3 + (survival + dd_pen + sharpe_bon) / 3 * 0.7) * 100
    
    return capital, max_dd, sharpe, harmony

def create_cosmic_dna() -> List[int]:
    base = random.randint(50, 150)
    return [
        base,
        int(base * PHI),
        int(base * PHI * PHI),
        int(base / PHI),
        base,
        int(base * (1 + 1/PHI))
    ]

def mutate_cosmic(dna: List[int]) -> List[int]:
    new = dna.copy()
    idx = random.randint(0, 5)
    if random.random() < 0.5:
        new[idx] = int(new[idx] * (PHI if random.random() > 0.5 else 1/PHI))
    else:
        new[idx] += random.randint(-30, 30)
    new[idx] = max(10, min(500, new[idx]))
    return new

def eval_wrapper(dna):
    _, _, _, harmony = evaluate_cosmic(dna)
    return dna, harmony

def run_cosmic_evolution(redis_host=None, redis_port=None, redis_pass=None):
    # Use environment variables if not provided
    redis_host = redis_host or REDIS_HOST
    redis_port = redis_port or REDIS_PORT
    redis_pass = redis_pass or REDIS_PASS
    
    print("=" * 60)
    print("  🦁 CHAOS LAB - COSMIC ENTROPY EVOLUTION")
    print("  Testing DNA against Lorenz, Logistic, Fibonacci")
    print(f"  Redis: {redis_host}:{redis_port}")
    print("=" * 60)
    
    r = None
    if REDIS_AVAILABLE:
        try:
            r = redis.Redis(host=redis_host, port=redis_port, password=redis_pass, decode_responses=True)
            r.ping()
            print("[CHAOS] Redis connected")
        except:
            r = None
    
    population = [create_cosmic_dna() for _ in range(POPULATION_SIZE)]
    best_ever_dna = population[0]
    best_ever_score = 0
    gen = 1
    
    while True:
        start_t = time.time()
        
        with ProcessPoolExecutor() as ex:
            results = list(ex.map(eval_wrapper, population))
        
        results.sort(key=lambda x: x[1], reverse=True)
        best_dna, best_score = results[0]
        avg_score = sum(r[1] for r in results) / len(results)
        
        if best_score > best_ever_score:
            best_ever_score = best_score
            best_ever_dna = best_dna
            
            print(f"\n🦁 NEW COSMIC CHAMPION (Gen {gen})")
            print(f"   DNA: {best_dna}")
            print(f"   Cosmic Harmony: {best_score:.1f}")
            
            if r:
                try:
                    r.set(CHAOS_DNA_KEY, json.dumps(best_dna))
                    r.set(CHAOS_META_KEY, json.dumps({
                        "gen": gen, "score": best_score,
                        "cosmic_harmony": best_score, "timestamp": time.time()
                    }))
                except:
                    pass
        
        print(f"Gen {gen} | Harmony: {best_score:.1f} | Avg: {avg_score:.1f} | {time.time()-start_t:.1f}s")
        
        # Next gen
        next_gen = [r[0] for r in results[:10]]
        while len(next_gen) < POPULATION_SIZE:
            p1 = random.choice(results[:20])[0]
            p2 = random.choice(results[:20])[0]
            split = random.randint(1, 5)
            child = p1[:split] + p2[split:]
            if random.random() < 0.2:
                child = mutate_cosmic(child)
            next_gen.append(child)
        
        population = next_gen
        gen += 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--redis-host", default=None)
    parser.add_argument("--redis-port", type=int, default=None)
    parser.add_argument("--redis-pass", default=None)
    args = parser.parse_args()
    run_cosmic_evolution(args.redis_host, args.redis_port, args.redis_pass)
