# -*- coding: utf-8 -*-
"""
📡 QUANTUM BRIDGE - IBM Quantum Processor Connection
Sends digital organisms to the quantum realm for survival testing.
"""

import os
import asyncio
from datetime import datetime
from typing import List, Dict, Optional, Tuple
from dataclasses import dataclass

try:
    from qiskit_ibm_runtime import QiskitRuntimeService, SamplerV2 as Sampler
    from qiskit.transpiler.preset_passmanagers import generate_preset_pass_manager
    IBM_AVAILABLE = True
except ImportError:
    IBM_AVAILABLE = False

from .quantum_dna import QuantumDNA


@dataclass
class ExecutionResult:
    """Result of quantum execution for a genome."""
    genome_id: str
    counts: Dict[str, int]
    total_shots: int
    target_state: str
    target_probability: float
    fidelity: float
    execution_time: float
    backend_name: str


class QuantumArena:
    """
    The Quantum Arena - where genomes fight for survival.
    
    Connects to IBM Quantum and sends genome circuits for execution.
    The noisy quantum environment acts as natural selection pressure.
    """
    
    def __init__(self, api_token: Optional[str] = None, use_simulator: bool = False):
        self.api_token = api_token or os.getenv("IBM_QUANTUM_TOKEN")
        self.use_simulator = use_simulator
        self.service: Optional['QiskitRuntimeService'] = None
        self.backend = None
        self.shots = 1024
        
    def connect(self) -> bool:
        """Connect to IBM Quantum."""
        if not IBM_AVAILABLE:
            print("⚠️ IBM Runtime not available. Install: pip install qiskit-ibm-runtime")
            return False
        
        try:
            self.service = QiskitRuntimeService(
                channel="ibm_quantum_platform",
                token=self.api_token
            )
            
            if self.use_simulator:
                # Use simulator for testing
                self.backend = self.service.least_busy(simulator=True)
            else:
                # Get real quantum processor
                self.backend = self.service.least_busy(
                    operational=True,
                    min_num_qubits=5
                )
            
            print(f"🔌 Connected to IBM Quantum: {self.backend.name}")
            return True
            
        except Exception as e:
            print(f"❌ Connection failed: {e}")
            return False
    
    def execute_genome(self, genome: QuantumDNA, target_state: Optional[str] = None) -> ExecutionResult:
        """
        Execute a single genome in the quantum arena.
        
        Args:
            genome: The QuantumDNA to execute
            target_state: Expected ideal output state (for fitness calc)
        
        Returns:
            ExecutionResult with fitness metrics
        """
        if not self.backend:
            self.connect()
        
        if target_state is None:
            # Default target: all zeros (ground state survival)
            target_state = "0" * genome.num_qubits
        
        start_time = datetime.now()
        
        # Get circuit
        circuit = genome.to_circuit()
        
        # Transpile for backend
        pm = generate_preset_pass_manager(backend=self.backend, optimization_level=1)
        transpiled = pm.run(circuit)
        
        # Execute via Sampler
        sampler = Sampler(mode=self.backend)
        job = sampler.run([transpiled], shots=self.shots)
        result = job.result()
        
        # Get counts
        counts = result[0].data.meas.get_counts()
        
        execution_time = (datetime.now() - start_time).total_seconds()
        
        # Calculate fitness metrics
        target_prob = counts.get(target_state, 0) / self.shots
        fidelity = self._calculate_fidelity(counts, target_state)
        
        return ExecutionResult(
            genome_id=genome.id,
            counts=counts,
            total_shots=self.shots,
            target_state=target_state,
            target_probability=target_prob,
            fidelity=fidelity,
            execution_time=execution_time,
            backend_name=self.backend.name
        )
    
    def execute_batch(self, genomes: List[QuantumDNA], 
                      target_state: Optional[str] = None) -> List[ExecutionResult]:
        """
        Execute a batch of genomes in the quantum arena.
        More efficient than individual execution.
        """
        if not self.backend:
            self.connect()
        
        if target_state is None:
            target_state = "0" * genomes[0].num_qubits
        
        print(f"🧬 GENOME BATCH {len(genomes)} sent to Quantum Realm...")
        start_time = datetime.now()
        
        # Transpile all circuits
        circuits = [g.to_circuit() for g in genomes]
        pm = generate_preset_pass_manager(backend=self.backend, optimization_level=1)
        transpiled = pm.run(circuits)
        
        # Execute all
        sampler = Sampler(mode=self.backend)
        job = sampler.run(transpiled, shots=self.shots)
        
        print(f"⚡ Job submitted: {job.job_id()}")
        print(f"   Waiting for quantum execution on {self.backend.name}...")
        
        result = job.result()
        
        execution_time = (datetime.now() - start_time).total_seconds()
        print(f"✅ Execution complete in {execution_time:.2f}s")
        
        # Process results
        results = []
        for i, genome in enumerate(genomes):
            counts = result[i].data.meas.get_counts()
            target_prob = counts.get(target_state, 0) / self.shots
            fidelity = self._calculate_fidelity(counts, target_state)
            
            results.append(ExecutionResult(
                genome_id=genome.id,
                counts=counts,
                total_shots=self.shots,
                target_state=target_state,
                target_probability=target_prob,
                fidelity=fidelity,
                execution_time=execution_time / len(genomes),
                backend_name=self.backend.name
            ))
            
            # Alert for anomalies
            if fidelity > 0.9:
                print(f"⚠️ ANOMALY DETECTED: Genome {genome.id} survived with {fidelity:.1%} fidelity!")
        
        return results
    
    def _calculate_fidelity(self, counts: Dict[str, int], target_state: str) -> float:
        """
        Calculate fidelity score.
        
        Fidelity = how well the genome survived quantum noise.
        Higher = stronger DNA.
        """
        total = sum(counts.values())
        
        # Method: Calculate similarity to expected distribution
        target_count = counts.get(target_state, 0)
        
        # Base fidelity from target state probability
        base_fidelity = target_count / total
        
        # Bonus for low entropy (concentrated distribution)
        import math
        entropy = 0
        for count in counts.values():
            p = count / total
            if p > 0:
                entropy -= p * math.log2(p)
        
        max_entropy = math.log2(len(counts)) if len(counts) > 1 else 1
        entropy_bonus = 1 - (entropy / max_entropy) if max_entropy > 0 else 1
        
        # Combined fidelity
        fidelity = 0.6 * base_fidelity + 0.4 * entropy_bonus
        
        return min(1.0, fidelity)


# ═══════════════════════════════════════════════════════════════════════════════
# SIMULATOR FALLBACK - For testing without IBM access
# ═══════════════════════════════════════════════════════════════════════════════

class SimulatorArena:
    """
    Local simulator for testing when IBM not available.
    Uses Qiskit Aer if available, otherwise mock execution.
    """
    
    def __init__(self):
        self.shots = 1024
        self.backend_name = "local_simulator"
        
        try:
            from qiskit_aer import AerSimulator
            self.simulator = AerSimulator()
            self.aer_available = True
        except ImportError:
            self.simulator = None
            self.aer_available = False
    
    def execute_batch(self, genomes: List[QuantumDNA], 
                      target_state: Optional[str] = None) -> List[ExecutionResult]:
        """Execute genomes on local simulator."""
        if target_state is None:
            target_state = "0" * genomes[0].num_qubits
        
        results = []
        
        for genome in genomes:
            if self.aer_available:
                # Real simulation
                circuit = genome.to_circuit()
                job = self.simulator.run(circuit, shots=self.shots)
                counts = job.result().get_counts()
            else:
                # Mock execution
                counts = self._mock_execution(genome)
            
            target_prob = counts.get(target_state, 0) / self.shots
            fidelity = self._calculate_fidelity(counts, target_state)
            
            results.append(ExecutionResult(
                genome_id=genome.id,
                counts=counts,
                total_shots=self.shots,
                target_state=target_state,
                target_probability=target_prob,
                fidelity=fidelity,
                execution_time=0.1,
                backend_name=self.backend_name
            ))
        
        return results
    
    def _mock_execution(self, genome: QuantumDNA) -> Dict[str, int]:
        """Mock quantum execution."""
        import random
        
        # Generate random-ish counts based on genome complexity
        num_states = 2 ** genome.num_qubits
        counts = {}
        remaining = self.shots
        
        for i in range(min(8, num_states)):
            state = format(i, f'0{genome.num_qubits}b')
            count = random.randint(0, remaining // 2)
            if count > 0:
                counts[state] = count
                remaining -= count
        
        if remaining > 0:
            counts["0" * genome.num_qubits] = counts.get("0" * genome.num_qubits, 0) + remaining
        
        return counts
    
    def _calculate_fidelity(self, counts: Dict[str, int], target_state: str) -> float:
        """Calculate fidelity."""
        import math
        total = sum(counts.values())
        target_count = counts.get(target_state, 0)
        return target_count / total if total > 0 else 0


# Convenience function
def get_arena(use_ibm: bool = True, api_token: Optional[str] = None) -> 'QuantumArena':
    """Get appropriate arena (IBM or simulator)."""
    if use_ibm and IBM_AVAILABLE and api_token:
        arena = QuantumArena(api_token=api_token)
        if arena.connect():
            return arena
    
    print("📟 Using local simulator...")
    return SimulatorArena()
