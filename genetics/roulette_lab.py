#!/usr/bin/env python3
"""
🐺 ROULETTE SURVIVAL LAB - Zero Edge Universe
Tests DNA survival in pure random environment
"""

import random
import json
import time
from concurrent.futures import ProcessPoolExecutor
from typing import List, Tuple

try:
    import redis
    REDIS_AVAILABLE = True
except ImportError:
    REDIS_AVAILABLE = False

POPULATION_SIZE = 50
SPINS_PER_EVAL = 10000
STARTING_BANKROLL = 10000
MIN_BET, MAX_BET = 10, 500

ROULETTE_DNA_KEY = "godbrain:roulette:best_dna"
ROULETTE_META_KEY = "godbrain:roulette:best_meta"

WIN_PROB = 18 / 37  # European roulette red/black

class RouletteWheel:
    def __init__(self):
        self.consecutive_losses = 0
        self.max_losses = 0
    
    def spin_red(self, bet: float) -> float:
        if random.random() < WIN_PROB:
            self.consecutive_losses = 0
            return bet
        else:
            self.consecutive_losses += 1
            self.max_losses = max(self.max_losses, self.consecutive_losses)
            return -bet

def evaluate_survival(dna: List[int]) -> Tuple[int, float, float, float]:
    """Returns: (spins_survived, final_bankroll, max_drawdown, score)"""
    wheel = RouletteWheel()
    bankroll = STARTING_BANKROLL
    peak = bankroll
    max_dd = 0
    
    for spin in range(SPINS_PER_EVAL):
        if bankroll < MIN_BET:
            break
        
        # DNA: bet size based on loss streak
        streak = min(5, wheel.consecutive_losses)
        bet = min(MAX_BET, min(bankroll * 0.5, dna[streak]))
        bet = max(MIN_BET, bet)
        
        bankroll += wheel.spin_red(bet)
        
        if bankroll > peak:
            peak = bankroll
        dd = (peak - bankroll) / peak if peak > 0 else 0
        max_dd = max(max_dd, dd)
    
    spins = spin + 1
    longevity = (spins / SPINS_PER_EVAL) * 100
    preservation = min(100, (bankroll / STARTING_BANKROLL) * 100)
    stability = max(0, 100 - max_dd * 200)
    score = longevity * 0.4 + preservation * 0.3 + stability * 0.3
    
    return spins, bankroll, max_dd, score

def create_dna() -> List[int]:
    """Create survival-oriented DNA (decreasing bets on streaks)"""
    base = random.randint(30, 80)
    return [
        base + random.randint(0, 30),      # 0-1 losses: normal
        base + random.randint(0, 20),      # 2 losses
        base + random.randint(0, 10),      # 3 losses
        max(MIN_BET, base - random.randint(0, 10)),  # 4 losses: reduce
        max(MIN_BET, base - random.randint(5, 20)),  # 5 losses: reduce more
        max(MIN_BET, base - random.randint(10, 30)), # 6+ losses: minimum
    ]

def mutate(dna: List[int]) -> List[int]:
    new = dna.copy()
    idx = random.randint(0, 5)
    mutation = random.randint(-20, 20)
    new[idx] = max(MIN_BET, min(MAX_BET, new[idx] + mutation))
    return new

def crossover(p1: List[int], p2: List[int]) -> List[int]:
    split = random.randint(1, 5)
    return p1[:split] + p2[split:]

def eval_wrapper(dna):
    _, _, _, score = evaluate_survival(dna)
    return dna, score

def run_evolution(redis_host="127.0.0.1", redis_port=6379):
    print("=" * 60)
    print("  🐺 ROULETTE SURVIVAL LAB")
    print("  Testing DNA in zero-edge universe")
    print("=" * 60)
    
    r = None
    if REDIS_AVAILABLE:
        try:
            r = redis.Redis(host=redis_host, port=redis_port, decode_responses=True)
            r.ping()
            print("[ROULETTE] Redis connected")
        except:
            r = None
    
    # Initialize population
    population = [create_dna() for _ in range(POPULATION_SIZE)]
    best_ever_dna = [60, 50, 40, 35, 25, 15]
    best_ever_score = 0
    gen = 1
    
    while True:
        start_t = time.time()
        
        with ProcessPoolExecutor(max_workers=8) as ex:
            results = list(ex.map(eval_wrapper, population))
        
        results.sort(key=lambda x: x[1], reverse=True)
        best_dna, best_score = results[0]
        avg_score = sum(r[1] for r in results) / len(results)
        
        if best_score > best_ever_score:
            best_ever_score = best_score
            best_ever_dna = best_dna
            
            print(f"\n🏆 NEW SURVIVAL CHAMPION (Gen {gen})")
            print(f"   DNA: {best_dna}")
            print(f"   Score: {best_score:.1f}")
            
            if r:
                try:
                    r.set(ROULETTE_DNA_KEY, json.dumps(best_dna))
                    r.set(ROULETTE_META_KEY, json.dumps({
                        "gen": gen, "score": best_score, "timestamp": time.time()
                    }))
                except Exception as e:
                    print(f"[REDIS] Error: {e}")
        
        print(f"Gen {gen} | Best: {best_score:.1f} | Avg: {avg_score:.1f} | {time.time()-start_t:.1f}s")
        
        # Next generation
        next_gen = [r[0] for r in results[:10]]  # Top 20% elite
        
        while len(next_gen) < POPULATION_SIZE:
            p1 = random.choice(results[:20])[0]
            p2 = random.choice(results[:20])[0]
            child = crossover(p1, p2)
            if random.random() < 0.15:
                child = mutate(child)
            next_gen.append(child)
        
        population = next_gen
        gen += 1

if __name__ == "__main__":
    import argparse
    parser = argparse.ArgumentParser()
    parser.add_argument("--redis-host", default="127.0.0.1")
    parser.add_argument("--redis-port", type=int, default=6379)
    args = parser.parse_args()
    run_evolution(args.redis_host, args.redis_port)
