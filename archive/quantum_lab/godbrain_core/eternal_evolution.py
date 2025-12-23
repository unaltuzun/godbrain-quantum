# GODBRAIN v0.1 - ETERNAL EVOLUTION DAEMON
# STATUS: CORE INFRASTRUCTURE  
# DESC: Continuous evolution - runs forever, preserves everything.
# NOTE: This is a serious physics experiment. Genomes are immortal.

"""
ETERNAL EVOLUTION DAEMON

This daemon runs continuously, evolving genomes under noise.
Nothing is optimized. Nothing is rushed.
We observe what survives.

Principles:
- Preserve diversity over performance
- Multi-objective survival (Pareto, not scalar)
- Complete lineage tracking
- Noise robustness across sigma levels
- Physical coherence over optimization
"""

import time
import json
import signal
import logging
import argparse
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import List, Optional, Dict, Any

# Setup logging
LOG_DIR = Path(__file__).parent.parent.parent / "logs"
LOG_DIR.mkdir(exist_ok=True)

# Shared state for bridge (decoupled communication)
DATA_DIR = Path(__file__).parent.parent.parent / "data"
DATA_DIR.mkdir(exist_ok=True)
SHARED_STATE_FILE = DATA_DIR / "lab_state.json"

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [GODBRAIN] %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / 'godbrain_evolution.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("godbrain.evolution")

# Import core components
from quantum_lab.godbrain_core.godbrain_v0_1_core import Genome
from quantum_lab.godbrain_core.genome_vault import get_vault, GenomeVault, GenomeRecord


class EternalEvolution:
    """
    ETERNAL EVOLUTION
    
    The process that never ends.
    Genomes live, mutate, and propagate.
    We watch. We record. We do not interfere.
    """
    
    def __init__(self, population_size: int = 20):
        self.vault = get_vault()
        self.population_size = population_size
        self.running = False
        self.generation = 0
        
        logger.info("=" * 60)
        logger.info("GODBRAIN v0.1 ETERNAL EVOLUTION")
        logger.info("=" * 60)
        logger.info(f"Vault contains {len(self.vault.genomes)} immortal genomes")
        logger.info(f"Population size: {population_size}")
    
    def initialize_population(self) -> List[str]:
        """Initialize or restore population."""
        alive = self.vault.get_alive()
        
        if len(alive) >= self.population_size:
            # Use existing survivors
            logger.info(f"Restoring {len(alive)} survivors from vault")
            return [g.genome_id for g in alive[:self.population_size]]
        
        # Create new genomes to fill population
        population = [g.genome_id for g in alive]
        needed = self.population_size - len(population)
        
        logger.info(f"Creating {needed} new genomes...")
        
        created = 0
        attempts = 0
        max_attempts = needed * 10
        
        while created < needed and attempts < max_attempts:
            genome = Genome()
            record = self.vault.store(genome)
            attempts += 1
            
            if record.alive:
                population.append(record.genome_id)
                created += 1
                logger.info(f"  Born: {record.genome_id[:8]} (f_stab={record.f_stab:.4f}, f_energy={record.f_energy:.4f})")
        
        logger.info(f"Population initialized: {len(population)} alive genomes")
        self.vault.save()
        
        return population
    
    def select_parents(self, population: List[str]) -> List[str]:
        """
        Select parents for next generation.
        Uses tournament selection with Pareto preference.
        """
        # Prefer Pareto front members
        pareto = set(self.vault.pareto_front)
        
        # Tournament selection
        selected = []
        for _ in range(self.population_size):
            # Pick 3 random candidates
            candidates = np.random.choice(population, size=min(3, len(population)), replace=False)
            
            # Prefer Pareto members
            pareto_candidates = [c for c in candidates if c in pareto]
            if pareto_candidates:
                selected.append(np.random.choice(pareto_candidates))
            else:
                selected.append(np.random.choice(candidates))
        
        return selected
    
    def reproduce(self, parent_id: str) -> Optional[str]:
        """
        Create offspring from parent.
        The child inherits and mutates.
        """
        parent = self.vault.resurrect(parent_id)
        if parent is None:
            return None
        
        # Create child (copy and mutate)
        child = Genome.__new__(Genome)
        child.A = parent.A.copy()
        child.alpha = parent.alpha.copy()
        child.beta = parent.beta.copy()
        child.b = parent.b.copy()
        
        # Mutate
        child.mutate(p_struct=0.01)
        
        # Store in vault (evaluation happens inside)
        record = self.vault.store(child, parent_id=parent_id)
        
        return record.genome_id if record.alive else None
    
    def run_generation(self, population: List[str]) -> List[str]:
        """
        Run one generation of evolution.
        """
        self.generation += 1
        self.vault.increment_generation()
        
        logger.info(f"--- Generation {self.generation} ---")
        
        # Select parents
        parents = self.select_parents(population)
        
        # Reproduce
        new_population = []
        for parent_id in parents:
            child_id = self.reproduce(parent_id)
            if child_id:
                new_population.append(child_id)
        
        # Keep best from old population if new is too small
        while len(new_population) < self.population_size:
            alive = self.vault.get_alive()
            if alive:
                # Add random survivor
                survivor = np.random.choice([g.genome_id for g in alive])
                if survivor not in new_population:
                    new_population.append(survivor)
            else:
                # Emergency: create new genome
                genome = Genome()
                record = self.vault.store(genome)
                if record.alive:
                    new_population.append(record.genome_id)
        
        # Log statistics
        stats = self.vault.get_statistics()
        logger.info(f"  Alive: {stats['alive_genomes']} | Pareto: {stats['pareto_front_size']} | Total: {stats['total_genomes']}")
        logger.info(f"  Max lineage: {stats['max_lineage_depth']} | Avg f_stab: {stats['avg_f_stab']:.4f}")
        
        # Save vault
        self.vault.save()
        
        # Export shared state for bridge
        self._export_shared_state(stats)
        
        return new_population[:self.population_size]
    
    def _export_shared_state(self, stats: Dict[str, Any]):
        """
        Export current state to shared file for bridge access.
        This enables decoupled communication with trading system.
        """
        try:
            # Get alive genomes for noise robustness calculation
            alive = self.vault.get_alive()
            high_noise_survivors = sum(1 for g in alive if g.noise_survival and g.noise_survival.get("0.3", False))
            noise_robustness = high_noise_survivors / len(alive) if alive else 0.0
            
            # Get Pareto front details
            pareto = self.vault.get_pareto_genomes()
            pareto_details = [
                {
                    "genome_id": g.genome_id[:8],
                    "f_stab": g.f_stab,
                    "f_energy": g.f_energy,
                    "lineage_depth": g.lineage_depth,
                }
                for g in pareto[:10]
            ]
            
            shared_state = {
                "timestamp": datetime.now().isoformat(),
                "generation": self.generation,
                
                # Core statistics
                "total_genomes": stats["total_genomes"],
                "alive_genomes": stats["alive_genomes"],
                "pareto_front_size": stats["pareto_front_size"],
                "max_lineage_depth": stats["max_lineage_depth"],
                
                # Stability metrics
                "avg_f_stab": float(stats["avg_f_stab"]),
                "avg_f_energy": float(stats["avg_f_energy"]),
                "noise_robustness": float(noise_robustness),
                
                # Trading suggestions
                "suggested_dd_tolerance": min(0.5, 0.1 + noise_robustness * 0.4),
                "regime_stability": 1.0 - min(1.0, float(stats["avg_f_stab"])),
                
                # Pareto front
                "pareto_front": pareto_details,
            }
            
            SHARED_STATE_FILE.write_text(
                json.dumps(shared_state, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            
        except Exception as e:
            logger.warning(f"Failed to export shared state: {e}")
    
    def run(self, interval_seconds: int = 60, max_generations: int = None):
        """
        Run eternal evolution.
        
        This process is designed to run forever.
        """
        self.running = True
        
        # Signal handling
        def signal_handler(signum, frame):
            logger.info("Shutdown signal received - saving vault...")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        logger.info("Starting eternal evolution...")
        logger.info(f"Interval: {interval_seconds}s between generations")
        
        # Initialize population
        population = self.initialize_population()
        
        # Main loop - runs forever
        while self.running:
            try:
                population = self.run_generation(population)
            except Exception as e:
                logger.exception(f"Generation error: {e}")
            
            # Check max generations
            if max_generations and self.generation >= max_generations:
                logger.info(f"Reached {max_generations} generations - stopping")
                break
            
            # Wait for next generation
            logger.info(f"Sleeping {interval_seconds}s...")
            for _ in range(interval_seconds):
                if not self.running:
                    break
                time.sleep(1)
        
        # Final save
        self.vault.save()
        
        logger.info("=" * 60)
        logger.info("ETERNAL EVOLUTION PAUSED")
        logger.info(f"Final statistics: {self.vault.get_statistics()}")
        logger.info("Vault saved. All genomes are immortal.")
        logger.info("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="GODBRAIN Eternal Evolution")
    parser.add_argument("--population", type=int, default=20, help="Population size")
    parser.add_argument("--interval", type=int, default=60, help="Seconds between generations")
    parser.add_argument("--generations", type=int, help="Max generations (default: infinite)")
    parser.add_argument("--stats", action="store_true", help="Show vault statistics and exit")
    
    args = parser.parse_args()
    
    if args.stats:
        vault = get_vault()
        stats = vault.get_statistics()
        print("\n=== GODBRAIN VAULT STATISTICS ===")
        for k, v in stats.items():
            print(f"  {k}: {v}")
        print(f"\nPareto front: {len(vault.pareto_front)} genomes")
        for gid in vault.pareto_front[:5]:
            if gid in vault.genomes:
                g = vault.genomes[gid]
                print(f"  {gid[:8]}: f_stab={g.f_stab:.4f}, f_energy={g.f_energy:.4f}")
        return
    
    evolution = EternalEvolution(population_size=args.population)
    evolution.run(interval_seconds=args.interval, max_generations=args.generations)


if __name__ == "__main__":
    main()
