# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN DNA Tracker
Track DNA evolution lineage with MLflow.
═══════════════════════════════════════════════════════════════════════════════
"""

import json
import time
from dataclasses import dataclass, field, asdict
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple

from .mlflow_config import log_dna_run, MLflowConfig


@dataclass
class DNASnapshot:
    """Snapshot of DNA at a point in time."""
    dna: List[int]
    generation: int
    fitness: float
    timestamp: float = field(default_factory=time.time)
    
    # Metrics from backtesting
    sharpe: float = 0.0
    pnl: float = 0.0
    max_dd: float = 0.0
    win_rate: float = 0.0
    trade_count: int = 0
    
    # Lineage
    parent_dna: Optional[List[int]] = None
    mutation_type: str = ""  # "crossover", "mutation", "elite"
    
    # MLflow tracking
    run_id: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "DNASnapshot":
        return cls(**data)


class DNATracker:
    """
    Track DNA evolution across generations.
    
    Features:
    - Log each DNA to MLflow
    - Track lineage (parent → child)
    - Maintain local cache
    - Support DNA regression (rollback to previous version)
    
    Usage:
        tracker = DNATracker()
        
        # Log new DNA
        tracker.log_generation(
            generation=42,
            dna=[10, 10, 242, 331, 354, 500],
            fitness=0.85,
            metrics={"sharpe": 1.5, "pnl": 1234}
        )
        
        # Get evolution history
        history = tracker.get_lineage()
        
        # Rollback if needed
        tracker.rollback_to_generation(40)
    """
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        experiment_name: str = "godbrain-genetics"
    ):
        self.cache_dir = cache_dir or Path(__file__).parent.parent / "data" / "dna_history"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        self.experiment_name = experiment_name
        
        self._history: List[DNASnapshot] = []
        self._load_cache()
    
    def _cache_file(self) -> Path:
        return self.cache_dir / "dna_lineage.json"
    
    def _load_cache(self) -> None:
        """Load history from local cache."""
        cache_file = self._cache_file()
        if cache_file.exists():
            try:
                with open(cache_file, "r") as f:
                    data = json.load(f)
                self._history = [DNASnapshot.from_dict(d) for d in data]
                print(f"[DNA_TRACKER] Loaded {len(self._history)} snapshots from cache")
            except Exception as e:
                print(f"[DNA_TRACKER] Cache load error: {e}")
                self._history = []
    
    def _save_cache(self) -> None:
        """Save history to local cache."""
        try:
            with open(self._cache_file(), "w") as f:
                json.dump([s.to_dict() for s in self._history], f, indent=2)
        except Exception as e:
            print(f"[DNA_TRACKER] Cache save error: {e}")
    
    def log_generation(
        self,
        generation: int,
        dna: List[int],
        fitness: float,
        metrics: Optional[Dict[str, float]] = None,
        parent_dna: Optional[List[int]] = None,
        mutation_type: str = "",
        tags: Optional[Dict[str, str]] = None
    ) -> Optional[str]:
        """
        Log a new DNA generation.
        
        Args:
            generation: Evolution generation number
            dna: DNA values
            fitness: Fitness score
            metrics: Backtest metrics {"sharpe": x, ...}
            parent_dna: Parent DNA for lineage tracking
            mutation_type: How this DNA was created
            tags: Additional MLflow tags
        
        Returns:
            MLflow run ID
        """
        metrics = metrics or {}
        
        # Create snapshot
        snapshot = DNASnapshot(
            dna=dna,
            generation=generation,
            fitness=fitness,
            sharpe=metrics.get("sharpe", 0),
            pnl=metrics.get("pnl", 0),
            max_dd=metrics.get("max_dd", 0),
            win_rate=metrics.get("win_rate", 0),
            trade_count=metrics.get("trade_count", 0),
            parent_dna=parent_dna,
            mutation_type=mutation_type,
        )
        
        # Log to MLflow
        all_tags = {"mutation_type": mutation_type}
        if tags:
            all_tags.update(tags)
        
        run_id = log_dna_run(
            dna=dna,
            metrics={"fitness": fitness, **metrics},
            generation=generation,
            tags=all_tags
        )
        
        snapshot.run_id = run_id
        
        # Add to history
        self._history.append(snapshot)
        self._save_cache()
        
        print(f"[DNA_TRACKER] Gen {generation} logged | Fitness: {fitness:.4f} | DNA: {dna[:3]}...")
        
        return run_id
    
    def get_lineage(self, last_n: int = 20) -> List[DNASnapshot]:
        """Get recent DNA lineage."""
        return self._history[-last_n:]
    
    def get_best_dna(self, metric: str = "fitness") -> Optional[DNASnapshot]:
        """Get best DNA by metric."""
        if not self._history:
            return None
        
        return max(self._history, key=lambda s: getattr(s, metric, 0))
    
    def get_by_generation(self, generation: int) -> Optional[DNASnapshot]:
        """Get DNA snapshot by generation."""
        for snapshot in reversed(self._history):
            if snapshot.generation == generation:
                return snapshot
        return None
    
    def rollback_to_generation(self, generation: int) -> Optional[List[int]]:
        """
        Rollback to a previous generation's DNA.
        
        Returns:
            DNA from that generation or None
        """
        snapshot = self.get_by_generation(generation)
        if snapshot:
            print(f"[DNA_TRACKER] Rolling back to gen {generation}: {snapshot.dna}")
            return snapshot.dna
        return None
    
    def compare_generations(
        self,
        gen1: int,
        gen2: int
    ) -> Optional[Dict[str, Any]]:
        """Compare two generations."""
        snap1 = self.get_by_generation(gen1)
        snap2 = self.get_by_generation(gen2)
        
        if not snap1 or not snap2:
            return None
        
        return {
            "generation_diff": gen2 - gen1,
            "fitness_change": snap2.fitness - snap1.fitness,
            "sharpe_change": snap2.sharpe - snap1.sharpe,
            "pnl_change": snap2.pnl - snap1.pnl,
            "dna_changes": [
                (i, snap1.dna[i], snap2.dna[i])
                for i in range(min(len(snap1.dna), len(snap2.dna)))
                if snap1.dna[i] != snap2.dna[i]
            ],
        }
    
    def get_evolution_curve(self) -> Tuple[List[int], List[float]]:
        """Get evolution curve for plotting."""
        generations = [s.generation for s in self._history]
        fitness_values = [s.fitness for s in self._history]
        return generations, fitness_values
    
    def summary(self) -> str:
        """Print evolution summary."""
        if not self._history:
            return "No DNA history"
        
        best = self.get_best_dna("fitness")
        latest = self._history[-1]
        
        return f"""
╔══════════════════════════════════════════════════════════════════╗
║                      DNA EVOLUTION SUMMARY                       ║
╠══════════════════════════════════════════════════════════════════╣
║ Total Generations: {len(self._history):>4}                                      
║ First: Gen {self._history[0].generation}  |  Latest: Gen {latest.generation}                     
║                                                                  ║
║ BEST DNA (by fitness)                                            ║
║   Generation: {best.generation}                                             
║   Fitness: {best.fitness:.4f}                                          
║   Sharpe: {best.sharpe:.2f}  |  PnL: ${best.pnl:,.2f}                      
║   DNA: {best.dna}                                                
║                                                                  ║
║ LATEST DNA                                                       ║
║   Fitness: {latest.fitness:.4f}  |  Sharpe: {latest.sharpe:.2f}                      
║   DNA: {latest.dna}                                              
╚══════════════════════════════════════════════════════════════════╝
"""


# Global tracker instance
_tracker: Optional[DNATracker] = None


def get_dna_tracker() -> DNATracker:
    """Get or create global DNA tracker."""
    global _tracker
    if _tracker is None:
        _tracker = DNATracker()
    return _tracker


if __name__ == "__main__":
    print("DNA Tracker Demo")
    print("=" * 50)
    
    tracker = DNATracker()
    
    # Simulate evolution
    import random
    
    dna = [10, 10, 234, 326, 354, 500]
    
    for gen in range(1, 6):
        # Mutate
        new_dna = [g + random.randint(-10, 10) for g in dna]
        fitness = random.uniform(0.5, 1.0)
        
        tracker.log_generation(
            generation=gen,
            dna=new_dna,
            fitness=fitness,
            metrics={"sharpe": fitness * 2, "pnl": fitness * 1000},
            parent_dna=dna,
            mutation_type="mutation"
        )
        
        dna = new_dna
    
    print(tracker.summary())
