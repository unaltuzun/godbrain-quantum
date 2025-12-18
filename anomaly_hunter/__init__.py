# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN ANOMALY HUNTER - CONTINUOUS EDITION
═══════════════════════════════════════════════════════════════════════════════

NOT limited to any generation count.
Continuously monitors evolving lab data in real-time.
Hunts for Nobel-worthy anomalies as they EMERGE.

7/24 EVOLUTION = 7/24 ANOMALY HUNTING

Usage:
    from anomaly_hunter import AnomalyHunter
    hunter = AnomalyHunter()
    anomalies = hunter.scan()
"""

import numpy as np
import pandas as pd
from datetime import datetime
from pathlib import Path
from typing import List, Dict, Optional, Tuple, Generator
from dataclasses import dataclass, field
from enum import Enum
from scipy import stats
from scipy.signal import find_peaks
import json
import asyncio
import warnings
import os

warnings.filterwarnings('ignore')

# Redis configuration
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.getenv('REDIS_PORT', '16379'))
REDIS_PASS = os.getenv('REDIS_PASS', 'voltran2024')

try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False


# ═══════════════════════════════════════════════════════════════════════════════
# DATA CLASSES
# ═══════════════════════════════════════════════════════════════════════════════

class AnomalyType(Enum):
    """Types of anomalies we're hunting."""
    UNIVERSAL_ATTRACTOR = "universal_attractor"
    PHASE_TRANSITION = "phase_transition"
    NONLOCAL_CORRELATION = "nonlocal_correlation"
    SYMMETRY_BREAKING = "symmetry_breaking"
    POWER_LAW = "power_law"
    EMERGENT_COMPUTATION = "emergent_computation"
    QUANTUM_SIGNATURE = "quantum_signature"
    TEMPORAL_ANOMALY = "temporal_anomaly"
    ENTROPY_REVERSAL = "entropy_reversal"
    UNKNOWN = "unknown"


class NobelPotential(Enum):
    """Nobel prize potential rating."""
    NONE = 0
    LOW = 1
    MEDIUM = 2
    HIGH = 3
    VERY_HIGH = 4
    NOBEL_WORTHY = 5


@dataclass
class Anomaly:
    """Represents a detected anomaly."""
    
    id: str
    type: AnomalyType
    timestamp: datetime
    title: str
    description: str
    confidence: float
    significance: float
    nobel_potential: NobelPotential
    generation_range: Tuple[int, int]
    affected_genomes: int
    raw_data: Dict = field(default_factory=dict)
    is_reproducible: bool = False
    reproduction_count: int = 0
    evidence: List[str] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "type": self.type.value,
            "timestamp": self.timestamp.isoformat(),
            "title": self.title,
            "description": self.description,
            "confidence": self.confidence,
            "significance": self.significance,
            "nobel_potential": self.nobel_potential.value,
            "generation_range": self.generation_range,
            "affected_genomes": self.affected_genomes,
            "evidence": self.evidence,
        }
    
    def __str__(self) -> str:
        stars = "⭐" * self.nobel_potential.value
        conf_str = f"{self.confidence:.1%}"
        return f"""
╔══════════════════════════════════════════════════════════════════╗
║  🔬 ANOMALY: {self.title[:50]:<50} ║
╠══════════════════════════════════════════════════════════════════╣
║  Type:           {self.type.value:<45} ║
║  Confidence:     {conf_str:<45} ║
║  Nobel Potential: {stars:<44} ║
║  Generations:    {str(self.generation_range):<45} ║
╚══════════════════════════════════════════════════════════════════╝
"""


# ═══════════════════════════════════════════════════════════════════════════════
# CONTINUOUS LAB DATA INTERFACE
# ═══════════════════════════════════════════════════════════════════════════════

class ContinuousLabInterface:
    """
    Real-time interface to Physics Lab.
    Streams data as evolution continues 7/24.
    """
    
    def __init__(self):
        self.redis = None
        if HAS_REDIS:
            try:
                self.redis = redis.Redis(
                    host=REDIS_HOST, 
                    port=REDIS_PORT,
                    password=REDIS_PASS,
                    decode_responses=True
                )
                self.redis.ping()
            except:
                self.redis = None
        
        # Path detection
        self.root = Path(__file__).parent.parent
        self.lab_state_path = self.root / "data" / "lab_state.json"
        self.vault_path = self.root / "quantum_lab" / "godbrain_core" / "vault"
        self.wisdom_path = self.root / "quantum_lab" / "wisdom"
        self._last_generation = 0
    
    def get_current_generation(self) -> int:
        """Get current generation count from live lab."""
        try:
            # Try Redis first
            if self.redis:
                gen = self.redis.get("godbrain:genetics:generation")
                if gen:
                    return int(gen)
            
            # Try engine_state.json
            engine_state = self.wisdom_path / "engine_state.json"
            if engine_state.exists():
                with open(engine_state, encoding='utf-8') as f:
                    state = json.load(f)
                    return state.get("epoch", 0)
            
            # Fallback to lab_state.json
            if self.lab_state_path.exists():
                with open(self.lab_state_path, encoding='utf-8') as f:
                    state = json.load(f)
                    return state.get("generation", 0)
        except:
            pass
        return 0
    
    def get_latest_genomes(self, n: int = 100) -> List[Dict]:
        """Get latest N genomes from vault."""
        genomes = []
        
        if self.vault_path.exists():
            files = sorted(self.vault_path.glob("genome_*.json"), reverse=True)[:n]
            for f in files:
                try:
                    with open(f, encoding='utf-8') as fp:
                        genomes.append(json.load(fp))
                except:
                    continue
        
        return genomes
    
    def stream_genomes(self, batch_size: int = 10) -> Generator[List[Dict], None, None]:
        """Stream genomes as they are created."""
        import time
        while True:
            current_gen = self.get_current_generation()
            
            if current_gen > self._last_generation:
                new_genomes = self.get_genomes_range(
                    self._last_generation, 
                    current_gen
                )
                self._last_generation = current_gen
                
                for i in range(0, len(new_genomes), batch_size):
                    yield new_genomes[i:i+batch_size]
            
            time.sleep(1)
    
    def get_genomes_range(self, start_gen: int, end_gen: int) -> List[Dict]:
        """Get genomes in generation range."""
        genomes = []
        
        if self.vault_path.exists():
            for f in self.vault_path.glob("genome_*.json"):
                try:
                    with open(f, encoding='utf-8') as fp:
                        g = json.load(fp)
                        gen = g.get("generation", 0)
                        if start_gen <= gen <= end_gen:
                            genomes.append(g)
                except:
                    continue
        
        return sorted(genomes, key=lambda x: x.get("generation", 0))
    
    def get_all_metrics(self) -> pd.DataFrame:
        """Get all metrics from all genomes as DataFrame."""
        genomes = []
        
        # Read from evolution_log.jsonl
        evolution_log = self.vault_path / "evolution_log.jsonl"
        if evolution_log.exists():
            try:
                with open(evolution_log, encoding='utf-8') as f:
                    for line in f:
                        try:
                            g = json.loads(line.strip())
                            genomes.append({
                                "generation": g.get("generation", 0),
                                "f_stab": g.get("f_stab", 0),
                                "f_energy": g.get("f_energy", 0),
                                "lineage_depth": g.get("lineage_depth", 0),
                                "timestamp": g.get("timestamp", ""),
                                "alive": g.get("alive", True),
                            })
                        except:
                            continue
            except:
                pass
        
        # Also try individual genome files
        if self.vault_path.exists():
            for f in self.vault_path.glob("genome_*.json"):
                try:
                    with open(f, encoding='utf-8') as fp:
                        g = json.load(fp)
                        genomes.append({
                            "generation": g.get("generation", 0),
                            "f_stab": g.get("f_stab", g.get("fitness", {}).get("f_stab", 0)),
                            "f_energy": g.get("f_energy", g.get("fitness", {}).get("f_energy", 0)),
                            "lineage_depth": g.get("lineage_depth", 0),
                            "timestamp": g.get("timestamp", ""),
                        })
                except:
                    continue
        
        if not genomes:
            return pd.DataFrame(columns=["generation", "f_stab", "f_energy", "lineage_depth"])
        
        return pd.DataFrame(genomes).sort_values("generation")


# Import AnomalyHunter for convenient access
from .hunter import AnomalyHunter

__all__ = ['AnomalyType', 'NobelPotential', 'Anomaly', 'ContinuousLabInterface', 'AnomalyHunter']
