#!/usr/bin/env python3
"""
📡 QUANTUM GENETICS LAB - IBM Quantum Processor Evolution
Evolves DNA using real quantum computers via IBM Quantum Platform
"""

import os
import sys
import time
import json
import redis
from datetime import datetime
from typing import Optional

# Add parent directory to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))

# Try to import quantum modules
try:
    from quantum_genesis.quantum_dna import QuantumDNA, create_population
    from quantum_genesis.quantum_bridge import get_arena, QuantumArena, SimulatorArena
    QUANTUM_AVAILABLE = True
except ImportError as e:
    print(f"[QUANTUM] Import error: {e}")
    QUANTUM_AVAILABLE = False


def run_quantum_evolution(
    redis_host: str = "localhost",
    redis_port: int = 6379,
    redis_pass: Optional[str] = None,
    use_ibm: bool = True,
    generations: int = 1000
):
    """
    Run quantum DNA evolution using IBM Quantum.
    
    The quantum computer's noise acts as natural selection pressure.
    Genomes that survive quantum decoherence are "fitter".
    """
    
    if not QUANTUM_AVAILABLE:
        print("[QUANTUM] ❌ Quantum modules not available. Cannot run evolution.")
        return
    
    print("=" * 60)
    print("  📡 QUANTUM GENETICS LAB")
    print("  Evolving DNA on IBM Quantum Processors")
    print(f"  Redis: {redis_host}:{redis_port}")
    print(f"  IBM Quantum: {'ENABLED' if use_ibm else 'SIMULATOR'}")
    print("=" * 60)
    
    # Redis connection
    try:
        r = redis.Redis(
            host=redis_host,
            port=redis_port,
            password=redis_pass,
            decode_responses=True
        )
        r.ping()
        print("[QUANTUM] Redis connected")
    except Exception as e:
        print(f"[QUANTUM] Redis connection failed: {e}")
        r = None
    
    # Get IBM Quantum token from environment
    ibm_token = os.getenv("IBM_QUANTUM_TOKEN")
    if use_ibm and not ibm_token:
        print("[QUANTUM] ⚠️ IBM_QUANTUM_TOKEN not set - falling back to simulator")
        use_ibm = False
    
    # Get arena (IBM or simulator)
    arena = get_arena(use_ibm=use_ibm, api_token=ibm_token)
    
    # Create initial population
    print("[QUANTUM] Creating primordial soup...")
    population = create_population(size=20, num_qubits=5, gene_count=10)
    
    best_fidelity = 0.0
    best_genome = None
    
    for gen in range(generations):
        start_time = time.time()
        
        # Execute all genomes in quantum arena
        try:
            results = arena.execute_batch(population, target_state="00000")
        except Exception as e:
            print(f"[QUANTUM] Execution error: {e}")
            time.sleep(30)  # Wait before retry
            continue
        
        # Calculate fitness (fidelity = survival in quantum noise)
        fitness_scores = [(r.genome_id, r.fidelity) for r in results]
        fitness_scores.sort(key=lambda x: x[1], reverse=True)
        
        # Track best
        current_best_id, current_best_fidelity = fitness_scores[0]
        current_best_genome = next(g for g in population if g.id == current_best_id)
        
        if current_best_fidelity > best_fidelity:
            best_fidelity = current_best_fidelity
            best_genome = current_best_genome
            
            print(f"\n⚛️ NEW QUANTUM CHAMPION (Gen {gen + 1})")
            print(f"   DNA: {best_genome.dna_sequence()[:50]}...")
            print(f"   Fidelity: {best_fidelity:.4f}")
            
            # Save to Redis
            if r:
                try:
                    r.set("godbrain:quantum:best_dna", json.dumps({
                        "id": best_genome.id,
                        "dna_sequence": best_genome.dna_sequence(),
                        "genes": [g.to_gate_str() for g in best_genome.genes],
                        "fidelity": best_fidelity,
                        "generation": gen + 1,
                        "backend": getattr(arena, 'backend_name', 'simulator'),
                        "timestamp": datetime.now().isoformat()
                    }))
                    r.set("godbrain:quantum:best_meta", json.dumps({
                        "gen": gen + 1,
                        "best_fidelity": best_fidelity,
                        "timestamp": time.time()
                    }))
                except Exception as e:
                    print(f"[QUANTUM] Redis save error: {e}")
        
        # Selection: top 40% survive
        survivors = [next(g for g in population if g.id == fid) 
                     for fid, _ in fitness_scores[:8]]
        
        # Reproduction: crossover + mutation
        new_population = list(survivors)  # Elitism
        
        while len(new_population) < 20:
            # Random parents from survivors
            import random
            p1, p2 = random.sample(survivors, 2)
            child = QuantumDNA.crossover(p1, p2)
            child = child.mutate(mutation_rate=0.15)
            child.generation = gen + 1
            new_population.append(child)
        
        population = new_population
        
        elapsed = time.time() - start_time
        avg_fidelity = sum(f for _, f in fitness_scores) / len(fitness_scores)
        
        print(f"Gen {gen + 1} | Best: {current_best_fidelity:.4f} | Avg: {avg_fidelity:.4f} | {elapsed:.1f}s")
        
        # Save generation stats to Redis
        if r:
            try:
                r.lpush("godbrain:quantum:history", json.dumps({
                    "gen": gen + 1,
                    "best_fidelity": current_best_fidelity,
                    "avg_fidelity": avg_fidelity,
                    "timestamp": time.time()
                }))
                r.ltrim("godbrain:quantum:history", 0, 999)  # Keep last 1000
            except:
                pass


if __name__ == "__main__":
    from config_center import config
    
    # Check if IBM Quantum should be used
    use_ibm = os.getenv("USE_IBM_QUANTUM", "false").lower() == "true"
    
    run_quantum_evolution(
        redis_host=config.REDIS_HOST,
        redis_port=config.REDIS_PORT,
        redis_pass=config.REDIS_PASS,
        use_ibm=use_ibm,
        generations=10000
    )
