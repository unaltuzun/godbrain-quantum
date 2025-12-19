# -*- coding: utf-8 -*-
"""
🧬 EVOLUTION ENGINE - Natural Selection in the Quantum Realm
Generational evolution of digital organisms.
"""

import json
import random
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

from .quantum_dna import QuantumDNA, create_population
from .quantum_bridge import QuantumArena, SimulatorArena, ExecutionResult


@dataclass
class GenerationStats:
    """Statistics for one generation."""
    generation: int
    population_size: int
    best_fitness: float
    avg_fitness: float
    worst_fitness: float
    alpha_genome_id: str
    alpha_dna_sequence: str
    mutations: int
    crossovers: int
    extinctions: int
    timestamp: datetime


class QuantumEvolution:
    """
    The Evolution Engine - manages generational evolution.
    
    Each generation:
    1. Execute all genomes in quantum arena
    2. Calculate fitness from survival rates
    3. Select strongest individuals
    4. Reproduce (crossover + mutation)
    5. Replace weakest with offspring
    """
    
    def __init__(
        self,
        population_size: int = 20,
        num_qubits: int = 5,
        gene_count: int = 10,
        mutation_rate: float = 0.15,
        elite_count: int = 3,
        arena: Optional[QuantumArena] = None
    ):
        self.population_size = population_size
        self.num_qubits = num_qubits
        self.gene_count = gene_count
        self.mutation_rate = mutation_rate
        self.elite_count = elite_count
        self.arena = arena or SimulatorArena()
        
        self.generation = 0
        self.population: List[QuantumDNA] = []
        self.history: List[GenerationStats] = []
        self.alpha_genome: Optional[QuantumDNA] = None
        
        # State persistence
        self.state_file = Path("quantum_genesis/evolution_state.json")
    
    def initialize(self):
        """Create initial population (primordial soup)."""
        print("🌊 Creating primordial soup...")
        self.population = create_population(
            self.population_size,
            self.num_qubits,
            self.gene_count
        )
        self.generation = 0
        print(f"   {len(self.population)} digital organisms spawned")
    
    def evolve_generation(self) -> GenerationStats:
        """
        Run one generation of evolution.
        
        Returns statistics about the generation.
        """
        self.generation += 1
        print(f"\n{'='*60}")
        print(f"🧬 GENERATION {self.generation}")
        print(f"{'='*60}")
        
        # 1. Execute all genomes in quantum arena
        print("📡 Sending genomes to quantum realm...")
        results = self.arena.execute_batch(self.population)
        
        # 2. Update fitness scores
        for genome, result in zip(self.population, results):
            genome.fitness = result.fidelity
        
        # 3. Sort by fitness (strongest first)
        self.population.sort(key=lambda g: g.fitness, reverse=True)
        
        # 4. Record alpha (strongest genome)
        self.alpha_genome = self.population[0]
        
        # 5. Statistics
        fitnesses = [g.fitness for g in self.population]
        stats = GenerationStats(
            generation=self.generation,
            population_size=len(self.population),
            best_fitness=max(fitnesses),
            avg_fitness=sum(fitnesses) / len(fitnesses),
            worst_fitness=min(fitnesses),
            alpha_genome_id=self.alpha_genome.id,
            alpha_dna_sequence=self.alpha_genome.dna_sequence(),
            mutations=0,
            crossovers=0,
            extinctions=0,
            timestamp=datetime.now()
        )
        
        print(f"🏆 Alpha: {self.alpha_genome.id} (fitness: {self.alpha_genome.fitness:.3f})")
        print(f"📊 Avg fitness: {stats.avg_fitness:.3f}")
        
        # 6. Selection & Reproduction
        new_population = []
        
        # Elite preservation (top performers survive unchanged)
        elites = self.population[:self.elite_count]
        new_population.extend(elites)
        print(f"👑 {len(elites)} elites preserved")
        
        # Reproduction zone
        reproducing = self.population[:len(self.population) // 2]
        
        while len(new_population) < self.population_size:
            # Tournament selection
            parent1 = self._tournament_select(reproducing)
            parent2 = self._tournament_select(reproducing)
            
            if random.random() < 0.7:
                # Crossover
                child = QuantumDNA.crossover(parent1, parent2)
                stats.crossovers += 1
            else:
                # Clone with mutation
                child = parent1.mutate(self.mutation_rate)
                stats.mutations += 1
            
            # Always apply small mutation chance
            if random.random() < self.mutation_rate:
                child = child.mutate(self.mutation_rate / 2)
                stats.mutations += 1
            
            new_population.append(child)
        
        # Count extinctions (genomes that didn't reproduce)
        stats.extinctions = len(self.population) - len(reproducing)
        
        self.population = new_population
        self.history.append(stats)
        
        print(f"🔀 {stats.crossovers} crossovers, ⚡ {stats.mutations} mutations")
        print(f"💀 {stats.extinctions} extinctions")
        
        return stats
    
    def _tournament_select(self, candidates: List[QuantumDNA], 
                           tournament_size: int = 3) -> QuantumDNA:
        """Select genome via tournament selection."""
        tournament = random.sample(candidates, min(tournament_size, len(candidates)))
        return max(tournament, key=lambda g: g.fitness)
    
    def run(self, generations: int = 10) -> QuantumDNA:
        """
        Run evolution for N generations.
        
        Returns the alpha genome (strongest survivor).
        """
        if not self.population:
            self.initialize()
        
        print(f"\n🚀 Starting evolution for {generations} generations")
        print(f"   Population: {self.population_size}")
        print(f"   Qubits: {self.num_qubits}")
        print(f"   Mutation rate: {self.mutation_rate:.1%}")
        
        for _ in range(generations):
            self.evolve_generation()
            self.save_state()
        
        print(f"\n{'='*60}")
        print("🎊 EVOLUTION COMPLETE!")
        print(f"{'='*60}")
        print(f"🧬 Alpha Genome: {self.alpha_genome.id}")
        print(f"   DNA: {self.alpha_genome.dna_sequence()}")
        print(f"   Fitness: {self.alpha_genome.fitness:.4f}")
        print(f"   Generations survived: {self.alpha_genome.generation}")
        
        return self.alpha_genome
    
    def save_state(self):
        """Save evolution state for recovery."""
        state = {
            "generation": self.generation,
            "timestamp": datetime.now().isoformat(),
            "alpha_genome": self.alpha_genome.to_dict() if self.alpha_genome else None,
            "population": [g.to_dict() for g in self.population[:10]],  # Top 10
            "stats_history": [
                {
                    "generation": s.generation,
                    "best_fitness": s.best_fitness,
                    "avg_fitness": s.avg_fitness,
                    "alpha_dna": s.alpha_dna_sequence
                }
                for s in self.history[-20:]  # Last 20 generations
            ]
        }
        
        self.state_file.parent.mkdir(exist_ok=True)
        with open(self.state_file, 'w') as f:
            json.dump(state, f, indent=2)
    
    def load_state(self) -> bool:
        """Load saved evolution state."""
        if not self.state_file.exists():
            return False
        
        try:
            with open(self.state_file) as f:
                state = json.load(f)
            
            self.generation = state.get("generation", 0)
            print(f"🔄 Recovered from generation {self.generation}")
            return True
        except:
            return False
    
    def get_alpha_signal(self) -> Dict:
        """
        Get alpha genome as a trading signal.
        Converts DNA to signal parameters.
        """
        if not self.alpha_genome:
            return {}
        
        # Convert DNA sequence to numeric seed
        dna = self.alpha_genome.dna_sequence()
        seed = sum(ord(c) * (i+1) for i, c in enumerate(dna))
        
        # Generate signal parameters
        random.seed(seed)
        
        return {
            "source": "quantum_genesis",
            "genome_id": self.alpha_genome.id,
            "generation": self.generation,
            "fitness": self.alpha_genome.fitness,
            "dna_sequence": dna,
            "signal_strength": self.alpha_genome.fitness,
            "bias": random.uniform(-0.1, 0.1),
            "confidence": min(0.95, self.alpha_genome.fitness),
            "timestamp": datetime.now().isoformat()
        }


# Test
if __name__ == "__main__":
    print("🧬 QUANTUM EVOLUTION TEST")
    print("=" * 60)
    
    engine = QuantumEvolution(
        population_size=10,
        num_qubits=5,
        gene_count=8
    )
    
    alpha = engine.run(generations=3)
    print(f"\n🏆 Final Alpha: {alpha}")
