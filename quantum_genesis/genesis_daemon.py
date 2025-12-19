# -*- coding: utf-8 -*-
"""
🧬 GENESIS DAEMON - Continuous Quantum Evolution
7/24 running digital organism evolution.
"""

import os
import sys
import time
import asyncio
from datetime import datetime
from pathlib import Path

# Rich terminal visualization
try:
    from rich.console import Console
    from rich.panel import Panel
    from rich.table import Table
    from rich.live import Live
    from rich.text import Text
    RICH_AVAILABLE = True
except ImportError:
    RICH_AVAILABLE = False

from .quantum_dna import QuantumDNA, create_population
from .quantum_bridge import QuantumArena, SimulatorArena, get_arena
from .evolution_engine import QuantumEvolution
from .harvester import QuantumHarvester


# ═══════════════════════════════════════════════════════════════════════════════
# DNA HELIX VISUALIZATION
# ═══════════════════════════════════════════════════════════════════════════════

def print_dna_helix(sequence: str, fitness: float):
    """Print DNA in helix style."""
    if not RICH_AVAILABLE:
        print(f"🧬 DNA: {sequence} | Fitness: {fitness:.3f}")
        return
    
    console = Console()
    
    # Create helix pattern
    helix = ""
    for i, nucleotide in enumerate(sequence[:20]):  # Limit length
        # Alternating helix pattern
        if i % 4 == 0:
            helix += f"  {nucleotide}─┐\n"
        elif i % 4 == 1:
            helix += f"    │ {nucleotide}\n"
        elif i % 4 == 2:
            helix += f"    {nucleotide} │\n"
        else:
            helix += f"  ┌─{nucleotide}\n"
    
    # Print panel
    panel = Panel(
        helix,
        title=f"[bold green]🧬 Quantum DNA[/bold green] (Fitness: {fitness:.3f})",
        subtitle=sequence,
        border_style="green"
    )
    console.print(panel)


def print_generation_banner(generation: int, best_fitness: float, avg_fitness: float):
    """Print generation banner."""
    if not RICH_AVAILABLE:
        print(f"\n{'='*60}")
        print(f"🧬 GENERATION {generation}")
        print(f"   Best: {best_fitness:.3f} | Avg: {avg_fitness:.3f}")
        print(f"{'='*60}")
        return
    
    console = Console()
    
    table = Table(title=f"🧬 GENERATION {generation}", border_style="cyan")
    table.add_column("Metric", style="cyan")
    table.add_column("Value", style="green")
    
    table.add_row("Best Fitness", f"{best_fitness:.4f}")
    table.add_row("Avg Fitness", f"{avg_fitness:.4f}")
    table.add_row("Progress", "█" * int(best_fitness * 20) + "░" * (20 - int(best_fitness * 20)))
    
    console.print(table)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN DAEMON
# ═══════════════════════════════════════════════════════════════════════════════

class GenesisDaemon:
    """
    The Genesis Daemon - continuous quantum evolution.
    
    Runs 7/24, evolving digital organisms and feeding
    the strongest survivors to GODBRAIN.
    """
    
    def __init__(
        self,
        api_token: str = None,
        use_ibm: bool = True,
        population_size: int = 20,
        num_qubits: int = 5,
        generations_per_epoch: int = 10
    ):
        self.api_token = api_token or os.getenv("IBM_QUANTUM_TOKEN")
        self.use_ibm = use_ibm and self.api_token
        self.population_size = population_size
        self.num_qubits = num_qubits
        self.generations_per_epoch = generations_per_epoch
        
        self.arena = None
        self.evolution = None
        self.harvester = QuantumHarvester()
        
        self.epoch = 0
        self.total_generations = 0
        self.running = False
    
    def initialize(self):
        """Initialize the quantum realm."""
        print("╔══════════════════════════════════════════════════════════════════╗")
        print("║       🧬 QUANTUM GENESIS LAB - DIGITAL LIFE SIMULATOR            ║")
        print("║                 Evolving Quantum Organisms 7/24                  ║")
        print("╚══════════════════════════════════════════════════════════════════╝")
        
        # Connect to quantum realm
        if self.use_ibm:
            print("\n📡 Connecting to IBM Quantum...")
            self.arena = get_arena(use_ibm=True, api_token=self.api_token)
        else:
            print("\n📟 Using local quantum simulator...")
            self.arena = SimulatorArena()
        
        # Initialize evolution engine
        self.evolution = QuantumEvolution(
            population_size=self.population_size,
            num_qubits=self.num_qubits,
            arena=self.arena
        )
        
        # Try to recover previous state
        if self.evolution.load_state():
            print(f"🔄 Recovered from generation {self.evolution.generation}")
            self.total_generations = self.evolution.generation
        else:
            print("🌊 Creating primordial soup...")
            self.evolution.initialize()
    
    def run_epoch(self):
        """Run one evolution epoch."""
        self.epoch += 1
        print(f"\n{'═'*60}")
        print(f"🌌 EPOCH {self.epoch}")
        print(f"{'═'*60}")
        
        print(f"🧬 GENOME BATCH {self.epoch} sent to Quantum Realm...")
        
        for i in range(self.generations_per_epoch):
            stats = self.evolution.evolve_generation()
            self.total_generations += 1
            
            # Visualize
            print_generation_banner(
                stats.generation,
                stats.best_fitness,
                stats.avg_fitness
            )
            
            # Show alpha DNA
            if self.evolution.alpha_genome:
                print_dna_helix(
                    self.evolution.alpha_genome.dna_sequence(),
                    self.evolution.alpha_genome.fitness
                )
        
        # Harvest alpha genome
        if self.evolution.alpha_genome:
            alpha = self.evolution.alpha_genome
            
            if alpha.fitness > 0.8:
                print(f"\n⚠️ ANOMALY DETECTED: Genome {alpha.id} survived with {alpha.fitness:.1%} fidelity!")
            
            anomaly = self.harvester.harvest(alpha)
            self.harvester.export_for_godbrain()
            
            # Try Redis injection
            try:
                self.harvester.inject_to_redis()
            except:
                pass
        
        return self.evolution.alpha_genome
    
    def run(self, epochs: int = None):
        """
        Run continuous evolution.
        
        Args:
            epochs: Number of epochs (None for infinite)
        """
        self.initialize()
        self.running = True
        
        epoch_count = 0
        
        try:
            while self.running:
                self.run_epoch()
                epoch_count += 1
                
                if epochs and epoch_count >= epochs:
                    break
                
                # Wait between epochs (to respect IBM rate limits)
                print(f"\n⏳ Waiting 60s before next epoch...")
                time.sleep(60)
                
        except KeyboardInterrupt:
            print("\n\n🛑 Genesis Lab stopped by user")
            self.running = False
        
        # Final report
        print("\n" + "═" * 60)
        print("🧬 QUANTUM GENESIS FINAL REPORT")
        print("═" * 60)
        print(f"   Total Epochs: {self.epoch}")
        print(f"   Total Generations: {self.total_generations}")
        if self.evolution.alpha_genome:
            print(f"   Final Alpha: {self.evolution.alpha_genome.id}")
            print(f"   Alpha Fitness: {self.evolution.alpha_genome.fitness:.4f}")
            print(f"   Alpha DNA: {self.evolution.alpha_genome.dna_sequence()}")


# ═══════════════════════════════════════════════════════════════════════════════
# ENTRY POINTS
# ═══════════════════════════════════════════════════════════════════════════════

def main():
    """Main entry point."""
    import argparse
    
    parser = argparse.ArgumentParser(description="Quantum Genesis Lab")
    parser.add_argument("--epochs", type=int, default=None, help="Number of epochs (default: infinite)")
    parser.add_argument("--population", type=int, default=20, help="Population size")
    parser.add_argument("--qubits", type=int, default=5, help="Number of qubits")
    parser.add_argument("--simulator", action="store_true", help="Use local simulator")
    parser.add_argument("--token", type=str, default=None, help="IBM Quantum API token")
    
    args = parser.parse_args()
    
    daemon = GenesisDaemon(
        api_token=args.token,
        use_ibm=not args.simulator,
        population_size=args.population,
        num_qubits=args.qubits
    )
    
    daemon.run(epochs=args.epochs)


if __name__ == "__main__":
    main()
