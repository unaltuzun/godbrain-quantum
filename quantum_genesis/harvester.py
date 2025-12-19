# -*- coding: utf-8 -*-
"""
🧬 HARVESTER - Extract Quantum Anomalies for GODBRAIN
Converts evolved quantum DNA into trading signals.
"""

import json
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional
from dataclasses import dataclass

from .quantum_dna import QuantumDNA


@dataclass
class QuantumAnomaly:
    """A quantum-born anomaly ready for GODBRAIN."""
    id: str
    genome_id: str
    generation: int
    fitness: float
    dna_sequence: str
    bitstring_seed: str
    signal_modifier: float
    confidence: float
    source: str
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        return {
            "id": self.id,
            "genome_id": self.genome_id,
            "generation": self.generation,
            "fitness": self.fitness,
            "dna_sequence": self.dna_sequence,
            "bitstring_seed": self.bitstring_seed,
            "signal_modifier": self.signal_modifier,
            "confidence": self.confidence,
            "source": self.source,
            "timestamp": self.timestamp.isoformat()
        }


class QuantumHarvester:
    """
    Harvests evolved genomes and converts them to GODBRAIN signals.
    
    The surviving genomes from quantum evolution are "alien data" -
    patterns that survived the harsh quantum realm.
    """
    
    def __init__(self, output_dir: Optional[Path] = None):
        self.output_dir = output_dir or Path("quantum_genesis/anomalies")
        self.output_dir.mkdir(parents=True, exist_ok=True)
        
        self.anomalies_file = self.output_dir / "quantum_anomalies.json"
        self.anomalies: List[QuantumAnomaly] = []
    
    def harvest(self, genome: QuantumDNA, result: Optional[Dict] = None) -> QuantumAnomaly:
        """
        Convert a quantum genome to a GODBRAIN anomaly.
        
        Args:
            genome: The evolved QuantumDNA
            result: Optional execution result with bitstring data
        """
        # Generate bitstring seed from DNA
        dna = genome.dna_sequence()
        bitstring = self._dna_to_bitstring(dna)
        
        # Calculate signal modifier (-1 to 1)
        signal = self._bitstring_to_signal(bitstring)
        
        anomaly = QuantumAnomaly(
            id=f"QA_{genome.id}_{datetime.now().strftime('%Y%m%d%H%M%S')}",
            genome_id=genome.id,
            generation=genome.generation,
            fitness=genome.fitness,
            dna_sequence=dna,
            bitstring_seed=bitstring,
            signal_modifier=signal,
            confidence=min(0.95, genome.fitness),
            source="quantum_genesis",
            timestamp=datetime.now()
        )
        
        self.anomalies.append(anomaly)
        return anomaly
    
    def _dna_to_bitstring(self, dna: str) -> str:
        """Convert DNA sequence to binary bitstring."""
        # Map: A=00, T=01, G=10, C=11
        mapping = {'A': '00', 'T': '01', 'G': '10', 'C': '11'}
        return ''.join(mapping.get(n, '00') for n in dna)
    
    def _bitstring_to_signal(self, bitstring: str) -> float:
        """Convert bitstring to signal modifier (-1 to 1)."""
        if not bitstring:
            return 0.0
        
        # Count 1s vs 0s
        ones = bitstring.count('1')
        zeros = len(bitstring) - ones
        
        # Ratio gives signal direction and strength
        total = len(bitstring)
        signal = (ones - zeros) / total
        
        return signal
    
    def export_for_godbrain(self) -> Dict:
        """
        Export anomalies in GODBRAIN-compatible format.
        """
        if not self.anomalies:
            return {"anomalies": [], "timestamp": datetime.now().isoformat()}
        
        # Get strongest anomaly
        strongest = max(self.anomalies, key=lambda a: a.fitness)
        
        export_data = {
            "source": "quantum_genesis",
            "timestamp": datetime.now().isoformat(),
            "total_anomalies": len(self.anomalies),
            "alpha_anomaly": strongest.to_dict(),
            "signal": {
                "direction": "long" if strongest.signal_modifier > 0 else "short",
                "strength": abs(strongest.signal_modifier),
                "confidence": strongest.confidence,
                "source": "quantum_evolution"
            },
            "recent_anomalies": [a.to_dict() for a in self.anomalies[-10:]]
        }
        
        # Save to file
        with open(self.anomalies_file, 'w') as f:
            json.dump(export_data, f, indent=2)
        
        print(f"💾 Injecting Quantum DNA into GODBRAIN core...")
        print(f"   File: {self.anomalies_file}")
        
        return export_data
    
    def inject_to_redis(self, redis_client=None):
        """
        Inject anomalies directly to Redis for real-time consumption.
        """
        if not redis_client:
            try:
                import redis
                redis_client = redis.Redis(
                    host='localhost',
                    port=16379,
                    password='voltran2024'
                )
            except:
                print("⚠️ Redis not available, using file export only")
                return
        
        if not self.anomalies:
            return
        
        strongest = max(self.anomalies, key=lambda a: a.fitness)
        
        # Write to Redis
        redis_client.hset("quantum_genesis:alpha", mapping={
            "genome_id": strongest.genome_id,
            "fitness": str(strongest.fitness),
            "dna": strongest.dna_sequence,
            "signal": str(strongest.signal_modifier),
            "confidence": str(strongest.confidence),
            "timestamp": datetime.now().isoformat()
        })
        
        redis_client.set(
            "quantum_genesis:signal",
            json.dumps(self.export_for_godbrain())
        )
        
        print(f"📡 Quantum signal injected to Redis")


# Test
if __name__ == "__main__":
    from .quantum_dna import QuantumDNA
    
    # Create test genome
    genome = QuantumDNA.random(5, 10)
    genome.fitness = 0.85
    
    harvester = QuantumHarvester()
    anomaly = harvester.harvest(genome)
    
    print(f"🧬 Harvested: {anomaly.id}")
    print(f"   DNA: {anomaly.dna_sequence}")
    print(f"   Signal: {anomaly.signal_modifier:+.3f}")
    print(f"   Confidence: {anomaly.confidence:.1%}")
    
    harvester.export_for_godbrain()
