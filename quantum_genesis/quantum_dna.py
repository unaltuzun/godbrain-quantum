# -*- coding: utf-8 -*-
"""
🧬 QUANTUM DNA - The Genetic Code of Digital Life
Each genome is a parameterized quantum circuit.
Gate → Nucleotide mapping creates the "DNA sequence".
"""

import random
import hashlib
from enum import Enum
from typing import List, Optional, Tuple
from dataclasses import dataclass, field

try:
    from qiskit import QuantumCircuit
    from qiskit.circuit import Parameter
    QISKIT_AVAILABLE = True
except ImportError:
    QISKIT_AVAILABLE = False
    QuantumCircuit = None


class Nucleotide(Enum):
    """DNA Nucleotides mapped to quantum gates."""
    A = "H"      # Adenine  → Hadamard (Superposition)
    T = "X"      # Thymine  → X gate (Bit flip)
    G = "CX"     # Guanine  → CNOT (Entanglement)
    C = "RZ"     # Cytosine → RZ rotation (Phase)


@dataclass
class Gene:
    """A single gene = one quantum gate operation."""
    nucleotide: Nucleotide
    target_qubit: int
    control_qubit: Optional[int] = None  # For CX gates
    parameter: Optional[float] = None     # For RZ gates
    
    def to_gate_str(self) -> str:
        if self.nucleotide == Nucleotide.G:
            return f"CX({self.control_qubit},{self.target_qubit})"
        elif self.nucleotide == Nucleotide.C:
            return f"RZ({self.parameter:.3f},{self.target_qubit})"
        else:
            return f"{self.nucleotide.value}({self.target_qubit})"


@dataclass
class QuantumDNA:
    """
    A digital organism's genome represented as a quantum circuit.
    
    The DNA sequence determines the quantum state evolution.
    Organisms compete for survival in the noisy quantum environment.
    """
    
    id: str
    num_qubits: int
    genes: List[Gene] = field(default_factory=list)
    generation: int = 0
    fitness: float = 0.0
    parent_ids: List[str] = field(default_factory=list)
    
    def __post_init__(self):
        if not self.id:
            self.id = self._generate_id()
    
    def _generate_id(self) -> str:
        """Generate unique genome ID."""
        data = f"{self.num_qubits}_{len(self.genes)}_{random.random()}"
        return f"DNA_{hashlib.md5(data.encode()).hexdigest()[:8]}"
    
    @classmethod
    def random(cls, num_qubits: int = 5, gene_count: int = 10, generation: int = 0) -> 'QuantumDNA':
        """Create a random genome (primordial soup)."""
        genes = []
        
        for _ in range(gene_count):
            nucleotide = random.choice(list(Nucleotide))
            target = random.randint(0, num_qubits - 1)
            
            if nucleotide == Nucleotide.G and num_qubits > 1:
                # CNOT needs control qubit
                control = random.randint(0, num_qubits - 1)
                while control == target:
                    control = random.randint(0, num_qubits - 1)
                genes.append(Gene(nucleotide, target, control_qubit=control))
            elif nucleotide == Nucleotide.C:
                # RZ needs parameter
                angle = random.uniform(0, 2 * 3.14159)
                genes.append(Gene(nucleotide, target, parameter=angle))
            else:
                genes.append(Gene(nucleotide, target))
        
        return cls(
            id="",
            num_qubits=num_qubits,
            genes=genes,
            generation=generation
        )
    
    def to_circuit(self) -> 'QuantumCircuit':
        """Convert DNA to executable quantum circuit."""
        if not QISKIT_AVAILABLE:
            raise ImportError("Qiskit not installed. Run: pip install qiskit qiskit-ibm-runtime")
        
        qc = QuantumCircuit(self.num_qubits, self.num_qubits)
        
        for gene in self.genes:
            if gene.nucleotide == Nucleotide.A:  # Hadamard
                qc.h(gene.target_qubit)
            elif gene.nucleotide == Nucleotide.T:  # X gate
                qc.x(gene.target_qubit)
            elif gene.nucleotide == Nucleotide.G:  # CNOT
                qc.cx(gene.control_qubit, gene.target_qubit)
            elif gene.nucleotide == Nucleotide.C:  # RZ
                qc.rz(gene.parameter, gene.target_qubit)
        
        # Measure all qubits
        qc.measure(range(self.num_qubits), range(self.num_qubits))
        
        return qc
    
    def mutate(self, mutation_rate: float = 0.1) -> 'QuantumDNA':
        """
        Mutate the genome.
        Mutations can:
        - Add a new gene
        - Remove a gene
        - Modify a parameter
        """
        import copy
        new_genes = copy.deepcopy(self.genes)
        
        for i, gene in enumerate(new_genes):
            if random.random() < mutation_rate:
                mutation_type = random.choice(['modify', 'add', 'delete'])
                
                if mutation_type == 'modify' and gene.nucleotide == Nucleotide.C:
                    # Modify RZ angle
                    delta = random.gauss(0, 0.5)
                    gene.parameter = (gene.parameter or 0) + delta
                
                elif mutation_type == 'add' and len(new_genes) < 20:
                    # Add random gene
                    new_gene = Gene(
                        nucleotide=random.choice(list(Nucleotide)),
                        target_qubit=random.randint(0, self.num_qubits - 1),
                        parameter=random.uniform(0, 6.28) if random.random() > 0.5 else None
                    )
                    new_genes.insert(i, new_gene)
                    break
                
                elif mutation_type == 'delete' and len(new_genes) > 3:
                    new_genes.pop(i)
                    break
        
        return QuantumDNA(
            id="",
            num_qubits=self.num_qubits,
            genes=new_genes,
            generation=self.generation + 1,
            parent_ids=[self.id]
        )
    
    @classmethod
    def crossover(cls, parent1: 'QuantumDNA', parent2: 'QuantumDNA') -> 'QuantumDNA':
        """
        Sexual reproduction between two genomes.
        Creates offspring with mixed genes from both parents.
        """
        crossover_point = random.randint(1, min(len(parent1.genes), len(parent2.genes)) - 1)
        
        new_genes = parent1.genes[:crossover_point] + parent2.genes[crossover_point:]
        
        return cls(
            id="",
            num_qubits=parent1.num_qubits,
            genes=new_genes[:15],  # Limit gene count
            generation=max(parent1.generation, parent2.generation) + 1,
            parent_ids=[parent1.id, parent2.id]
        )
    
    def dna_sequence(self) -> str:
        """Get DNA as nucleotide sequence string."""
        return "".join(gene.nucleotide.name for gene in self.genes)
    
    def to_dict(self) -> dict:
        """Serialize genome."""
        return {
            "id": self.id,
            "num_qubits": self.num_qubits,
            "generation": self.generation,
            "fitness": self.fitness,
            "dna_sequence": self.dna_sequence(),
            "gene_count": len(self.genes),
            "parent_ids": self.parent_ids
        }
    
    def __repr__(self) -> str:
        return f"QuantumDNA({self.id}, qubits={self.num_qubits}, genes={len(self.genes)}, fitness={self.fitness:.3f})"


# ═══════════════════════════════════════════════════════════════════════════════
# PRIMORDIAL SOUP - Random Population Generator
# ═══════════════════════════════════════════════════════════════════════════════

def create_population(size: int = 20, num_qubits: int = 5, gene_count: int = 10) -> List[QuantumDNA]:
    """Create initial population (primordial soup)."""
    return [QuantumDNA.random(num_qubits, gene_count) for _ in range(size)]


# Test
if __name__ == "__main__":
    print("🧬 Creating primordial soup...")
    population = create_population(5)
    
    for dna in population:
        print(f"  {dna.id}: {dna.dna_sequence()}")
    
    print("\n🔀 Testing crossover...")
    child = QuantumDNA.crossover(population[0], population[1])
    print(f"  Child: {child.dna_sequence()}")
    
    print("\n⚡ Testing mutation...")
    mutant = child.mutate(0.3)
    print(f"  Mutant: {mutant.dna_sequence()}")
    
    if QISKIT_AVAILABLE:
        print("\n🔬 Creating quantum circuit...")
        circuit = mutant.to_circuit()
        print(circuit.draw())
