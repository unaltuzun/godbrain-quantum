#!/usr/bin/env python3
"""
🦅 BLACKJACK GENETICS LAB - Edge Hunter
Evolves DNA for card counting advantage
"""

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
HANDS_PER_GEN = 50000
MIN_BET, MAX_BET = 10, 500

DNA_KEY = "godbrain:genetics:best_dna"
META_KEY = "godbrain:genetics:best_meta"

COUNT_VALUES = {2:1, 3:1, 4:1, 5:1, 6:1, 7:0, 8:0, 9:0, 10:-1, 11:-1}

class Shoe:
    def __init__(self, num_decks=6):
        self.num_decks = num_decks
        self.reset()
    
    def reset(self):
        deck = [2,3,4,5,6,7,8,9,10,10,10,10,11] * 4
        self.cards = deck * self.num_decks
        random.shuffle(self.cards)
        self.running_count = 0
    
    def draw(self):
        if len(self.cards) < 20:
            self.reset()
        card = self.cards.pop()
        self.running_count += COUNT_VALUES.get(card, 0)
        return card
    
    def get_true_count(self):
        decks = max(1, len(self.cards) / 52.0)
        return self.running_count / decks

def get_move(player_sum, dealer_card, soft, can_double):
    if not soft:
        if player_sum >= 17: return 'S'
        if player_sum <= 8: return 'H'
        if player_sum == 11: return 'D' if can_double else 'H'
        if player_sum == 10: return 'D' if dealer_card <= 9 and can_double else 'H'
        if player_sum == 9: return 'D' if 3 <= dealer_card <= 6 and can_double else 'H'
        if player_sum == 12: return 'S' if 4 <= dealer_card <= 6 else 'H'
        if 13 <= player_sum <= 16: return 'S' if dealer_card <= 6 else 'H'
    else:
        if player_sum >= 20: return 'S'
        if player_sum == 19: return 'D' if dealer_card == 6 and can_double else 'S'
        if player_sum == 18:
            if 2 <= dealer_card <= 6 and can_double: return 'D'
            if dealer_card <= 8: return 'S'
            return 'H'
        if player_sum == 17: return 'D' if 3 <= dealer_card <= 6 and can_double else 'H'
        if 15 <= player_sum <= 16: return 'D' if 4 <= dealer_card <= 6 and can_double else 'H'
        if 13 <= player_sum <= 14: return 'D' if 5 <= dealer_card <= 6 and can_double else 'H'
    return 'H'

def get_bet(dna, true_count):
    tc = int(max(0, min(5, true_count)))
    return dna[tc]

def evaluate_agent(dna: List[int]) -> float:
    shoe = Shoe()
    balance = 0
    
    for _ in range(HANDS_PER_GEN):
        tc = shoe.get_true_count()
        bet = get_bet(dna, tc)
        
        p1, p2 = shoe.draw(), shoe.draw()
        d_card, hidden = shoe.draw(), shoe.draw()
        
        if p1 + p2 == 21:
            if d_card + hidden == 21:
                continue
            balance += bet * 1.5
            continue
        
        if d_card + hidden == 21:
            balance -= bet
            continue
        
        player_sum = p1 + p2
        soft = (p1 == 11 or p2 == 11)
        if player_sum > 21 and soft:
            player_sum -= 10
            soft = False
        
        first = True
        while True:
            move = get_move(player_sum, d_card, soft, first)
            if move == 'S':
                break
            elif move == 'H':
                c = shoe.draw()
                player_sum += c
                if c == 11: soft = True
                if player_sum > 21 and soft:
                    player_sum -= 10
                    soft = False
                if player_sum > 21:
                    balance -= bet
                    break
                first = False
            elif move == 'D':
                bet *= 2
                c = shoe.draw()
                player_sum += c
                if c == 11: soft = True
                if player_sum > 21 and soft:
                    player_sum -= 10
                    soft = False
                if player_sum > 21:
                    balance -= bet
                break
        
        if player_sum > 21:
            continue
        
        dealer_sum = d_card + hidden
        d_soft = (d_card == 11 or hidden == 11)
        if dealer_sum > 21 and d_soft:
            dealer_sum -= 10
            d_soft = False
        
        while dealer_sum < 17:
            c = shoe.draw()
            dealer_sum += c
            if c == 11: d_soft = True
            if dealer_sum > 21 and d_soft:
                dealer_sum -= 10
                d_soft = False
        
        if dealer_sum > 21:
            balance += bet
        elif player_sum > dealer_sum:
            balance += bet
        elif dealer_sum > player_sum:
            balance -= bet
    
    return balance

def create_dna() -> List[int]:
    return sorted([
        random.randint(MIN_BET, MIN_BET * 2),
        random.randint(MIN_BET, 100),
        random.randint(50, 200),
        random.randint(100, 300),
        random.randint(200, 400),
        random.randint(300, MAX_BET),
    ])

def mutate(dna: List[int]) -> List[int]:
    new = dna.copy()
    idx = random.randint(0, 5)
    new[idx] = max(MIN_BET, min(MAX_BET, new[idx] + random.randint(-50, 50)))
    return sorted(new)

def eval_wrapper(dna):
    return dna, evaluate_agent(dna)

def run_evolution(redis_host=None, redis_port=None, redis_pass=None):
    # Use environment variables if not provided
    redis_host = redis_host or REDIS_HOST
    redis_port = redis_port or REDIS_PORT
    redis_pass = redis_pass or REDIS_PASS
    
    print("=" * 60)
    print("  🦅 BLACKJACK GENETICS LAB")
    print("  Evolving edge-hunting DNA")
    print(f"  Redis: {redis_host}:{redis_port}")
    print("=" * 60)
    
    r = None
    if REDIS_AVAILABLE:
        try:
            r = redis.Redis(host=redis_host, port=redis_port, password=redis_pass, decode_responses=True)
            r.ping()
            print("[BLACKJACK] Redis connected")
            
            # Recovery check
            existing = r.get(DNA_KEY)
            if existing:
                meta = r.get(META_KEY)
                if meta:
                    m = json.loads(meta)
                    print(f"[RECOVERY] Found Gen {m.get('gen')} | Profit: {m.get('best_profit', 0):.0f}")
        except:
            r = None
    
    population = [create_dna() for _ in range(POPULATION_SIZE)]
    best_ever_dna = [10, 10, 234, 326, 354, 500]
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
            
            print(f"\n🌟 NEW CHAMPION (Gen {gen})")
            print(f"   DNA: {best_dna}")
            print(f"   Profit: {best_score:.0f}")
            
            if r:
                try:
                    r.set(DNA_KEY, json.dumps(best_dna))
                    r.set(META_KEY, json.dumps({
                        "gen": gen, "best_profit": best_score, "timestamp": time.time()
                    }))
                except:
                    pass
        
        print(f"Gen {gen} | Best: {best_score:.0f} | Avg: {avg_score:.0f} | {time.time()-start_t:.1f}s")
        
        next_gen = [r[0] for r in results[:10]]
        while len(next_gen) < POPULATION_SIZE:
            p1 = random.choice(results[:20])[0]
            p2 = random.choice(results[:20])[0]
            split = random.randint(1, 5)
            child = sorted(p1[:split] + p2[split:])
            if random.random() < 0.1:
                child = mutate(child)
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
    run_evolution(args.redis_host, args.redis_port, args.redis_pass)
