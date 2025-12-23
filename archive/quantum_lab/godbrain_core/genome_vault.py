# GODBRAIN v0.1 - GENOME VAULT
# STATUS: CORE INFRASTRUCTURE
# DESC: Immortal genome storage - nothing dies, everything persists.
# NOTE: Every genome is eternal. Lineage is sacred.

import json
import hashlib
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
import logging

# Import core
from quantum_lab.godbrain_core.godbrain_v0_1_core import (
    Genome, simulate, evaluate_genome, DIM, SIGMA_LEVELS
)

logger = logging.getLogger("godbrain.vault")

# Vault location - sacred ground
VAULT_DIR = Path(__file__).parent / "vault"
VAULT_DIR.mkdir(exist_ok=True)

GENOME_ARCHIVE = VAULT_DIR / "genome_archive.json"
LINEAGE_TREE = VAULT_DIR / "lineage_tree.json"
PARETO_FRONT = VAULT_DIR / "pareto_front.json"
EVOLUTION_LOG = VAULT_DIR / "evolution_log.jsonl"


@dataclass
class GenomeRecord:
    """Immortal genome record."""
    genome_id: str
    generation: int
    parent_id: Optional[str]
    birth_time: str
    
    # Genome data (serialized)
    A: List[List[float]]
    alpha: List[List[float]]
    beta: List[List[List[float]]]
    b: List[float]
    
    # Survival metrics
    alive: bool
    f_stab: Optional[float] = None
    f_energy: Optional[float] = None
    
    # Noise robustness (tested across sigma levels)
    noise_survival: Dict[str, bool] = field(default_factory=dict)
    
    # Lineage depth
    lineage_depth: int = 0
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_genome(cls, genome: Genome, parent_id: Optional[str] = None, 
                    generation: int = 0, lineage_depth: int = 0) -> "GenomeRecord":
        """Create record from live genome."""
        genome_id = cls._generate_id(genome)
        
        return cls(
            genome_id=genome_id,
            generation=generation,
            parent_id=parent_id,
            birth_time=datetime.now().isoformat(),
            A=genome.A.tolist(),
            alpha=genome.alpha.tolist(),
            beta=genome.beta.tolist(),
            b=genome.b.tolist(),
            alive=False,  # Set after evaluation
            lineage_depth=lineage_depth,
        )
    
    @staticmethod
    def _generate_id(genome: Genome) -> str:
        """Generate unique genome ID from its structure."""
        data = (
            genome.A.tobytes() + 
            genome.alpha.tobytes() + 
            genome.beta.tobytes() + 
            genome.b.tobytes()
        )
        return hashlib.sha256(data).hexdigest()[:16]
    
    def to_genome(self) -> Genome:
        """Resurrect genome from record."""
        genome = Genome.__new__(Genome)
        genome.A = np.array(self.A)
        genome.alpha = np.array(self.alpha)
        genome.beta = np.array(self.beta)
        genome.b = np.array(self.b)
        return genome


class GenomeVault:
    """
    IMMORTAL GENOME VAULT
    
    Every genome that ever exists is stored here forever.
    Nothing is temporary. Everything persists.
    
    Features:
    - Persistent storage across restarts
    - Complete lineage tracking
    - Pareto front maintenance
    - Multi-noise-level survival testing
    """
    
    def __init__(self):
        self.genomes: Dict[str, GenomeRecord] = {}
        self.pareto_front: List[str] = []
        self.total_generations = 0
        
        self._load()
        logger.info(f"Vault opened: {len(self.genomes)} immortal genomes")
    
    def _load(self):
        """Load vault from disk."""
        if GENOME_ARCHIVE.exists():
            try:
                data = json.loads(GENOME_ARCHIVE.read_text(encoding='utf-8'))
                for g in data.get("genomes", []):
                    record = GenomeRecord(**g)
                    self.genomes[record.genome_id] = record
                self.total_generations = data.get("total_generations", 0)
            except Exception as e:
                logger.error(f"Vault load error: {e}")
        
        if PARETO_FRONT.exists():
            try:
                self.pareto_front = json.loads(PARETO_FRONT.read_text(encoding='utf-8'))
            except:
                pass
    
    def _save(self):
        """Persist vault to disk."""
        try:
            data = {
                "genomes": [g.to_dict() for g in self.genomes.values()],
                "total_generations": self.total_generations,
                "last_saved": datetime.now().isoformat(),
            }
            GENOME_ARCHIVE.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
            
            PARETO_FRONT.write_text(
                json.dumps(self.pareto_front, indent=2),
                encoding='utf-8'
            )
        except Exception as e:
            logger.error(f"Vault save error: {e}")
    
    def store(self, genome: Genome, parent_id: Optional[str] = None) -> GenomeRecord:
        """
        Store a genome in the vault forever.
        Evaluates survival and updates Pareto front.
        """
        # Get parent's lineage depth
        lineage_depth = 0
        if parent_id and parent_id in self.genomes:
            lineage_depth = self.genomes[parent_id].lineage_depth + 1
        
        # Create record
        record = GenomeRecord.from_genome(
            genome, 
            parent_id=parent_id,
            generation=self.total_generations,
            lineage_depth=lineage_depth,
        )
        
        # Evaluate survival
        result = evaluate_genome(genome)
        if result:
            record.alive = True
            record.f_stab, record.f_energy = result
            
            # Test across noise levels
            for sigma in SIGMA_LEVELS:
                _, _, valid = simulate(genome, sigma)
                record.noise_survival[str(sigma)] = valid
        
        # Store
        self.genomes[record.genome_id] = record
        
        # Update Pareto front if alive
        if record.alive:
            self._update_pareto(record)
        
        # Log
        self._log_event("STORE", record)
        
        return record
    
    def _update_pareto(self, new_record: GenomeRecord):
        """Update Pareto front with new genome."""
        if not new_record.alive:
            return
        
        # Check if dominated by any existing
        dominated = False
        to_remove = []
        
        for gid in self.pareto_front:
            if gid not in self.genomes:
                continue
            existing = self.genomes[gid]
            
            # Pareto dominance check (minimize both objectives)
            new_dominates = (
                new_record.f_stab <= existing.f_stab and 
                new_record.f_energy <= existing.f_energy and
                (new_record.f_stab < existing.f_stab or new_record.f_energy < existing.f_energy)
            )
            existing_dominates = (
                existing.f_stab <= new_record.f_stab and 
                existing.f_energy <= new_record.f_energy and
                (existing.f_stab < new_record.f_stab or existing.f_energy < new_record.f_energy)
            )
            
            if existing_dominates:
                dominated = True
                break
            if new_dominates:
                to_remove.append(gid)
        
        if not dominated:
            for gid in to_remove:
                self.pareto_front.remove(gid)
            self.pareto_front.append(new_record.genome_id)
    
    def _log_event(self, event: str, record: GenomeRecord):
        """Append to evolution log (JSONL - never overwritten)."""
        try:
            with open(EVOLUTION_LOG, 'a', encoding='utf-8') as f:
                log_entry = {
                    "event": event,
                    "genome_id": record.genome_id,
                    "generation": record.generation,
                    "alive": record.alive,
                    "f_stab": record.f_stab,
                    "f_energy": record.f_energy,
                    "parent_id": record.parent_id,
                    "lineage_depth": record.lineage_depth,
                    "timestamp": datetime.now().isoformat(),
                }
                f.write(json.dumps(log_entry) + "\n")
        except Exception as e:
            logger.error(f"Log error: {e}")
    
    def get_alive(self) -> List[GenomeRecord]:
        """Get all living genomes."""
        return [g for g in self.genomes.values() if g.alive]
    
    def get_pareto_genomes(self) -> List[GenomeRecord]:
        """Get genomes on the Pareto front."""
        return [self.genomes[gid] for gid in self.pareto_front if gid in self.genomes]
    
    def resurrect(self, genome_id: str) -> Optional[Genome]:
        """Bring a genome back to life from the vault."""
        if genome_id in self.genomes:
            return self.genomes[genome_id].to_genome()
        return None
    
    def get_lineage(self, genome_id: str) -> List[str]:
        """Trace complete lineage back to origin."""
        lineage = []
        current_id = genome_id
        
        while current_id:
            lineage.append(current_id)
            if current_id in self.genomes:
                current_id = self.genomes[current_id].parent_id
            else:
                break
        
        return lineage
    
    def get_statistics(self) -> Dict[str, Any]:
        """Get vault statistics."""
        alive = self.get_alive()
        return {
            "total_genomes": len(self.genomes),
            "alive_genomes": len(alive),
            "pareto_front_size": len(self.pareto_front),
            "total_generations": self.total_generations,
            "max_lineage_depth": max((g.lineage_depth for g in self.genomes.values()), default=0),
            "avg_f_stab": np.mean([g.f_stab for g in alive if g.f_stab]) if alive else 0,
            "avg_f_energy": np.mean([g.f_energy for g in alive if g.f_energy]) if alive else 0,
        }
    
    def save(self):
        """Explicitly save vault to disk."""
        self._save()
    
    def increment_generation(self):
        """Mark a new generation."""
        self.total_generations += 1


# Global vault instance
_vault: Optional[GenomeVault] = None


def get_vault() -> GenomeVault:
    """Get the immortal vault."""
    global _vault
    if _vault is None:
        _vault = GenomeVault()
    return _vault


if __name__ == "__main__":
    print("=== GENOME VAULT TEST ===")
    vault = GenomeVault()
    
    # Create and store a genome
    genome = Genome()
    record = vault.store(genome)
    
    print(f"Stored: {record.genome_id}")
    print(f"Alive: {record.alive}")
    print(f"Metrics: f_stab={record.f_stab}, f_energy={record.f_energy}")
    
    vault.save()
    print(f"\nVault stats: {vault.get_statistics()}")
