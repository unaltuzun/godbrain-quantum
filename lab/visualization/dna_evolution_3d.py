# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN DNA Evolution 3D Visualization
Interactive visualization of genetic algorithm evolution and fitness landscape.
═══════════════════════════════════════════════════════════════════════════════
"""

import json
import math
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field

import numpy as np

# Try to import plotly, fallback to matplotlib
try:
    import plotly.graph_objects as go
    import plotly.express as px
    from plotly.subplots import make_subplots
    HAS_PLOTLY = True
except ImportError:
    HAS_PLOTLY = False
    import matplotlib.pyplot as plt
    from mpl_toolkits.mplot3d import Axes3D


ROOT = Path(__file__).parent.parent


@dataclass
class DNASnapshot:
    """Snapshot of DNA at a generation."""
    generation: int
    dna: List[int]
    fitness: float
    timestamp: str = ""
    metrics: Dict[str, float] = field(default_factory=dict)
    parent_gen: Optional[int] = None


@dataclass
class EvolutionHistory:
    """Complete evolution history."""
    snapshots: List[DNASnapshot] = field(default_factory=list)
    
    def add(self, snapshot: DNASnapshot) -> None:
        self.snapshots.append(snapshot)
    
    @property
    def generations(self) -> List[int]:
        return [s.generation for s in self.snapshots]
    
    @property
    def fitness_values(self) -> List[float]:
        return [s.fitness for s in self.snapshots]
    
    def to_dict(self) -> Dict:
        return {
            "snapshots": [
                {
                    "generation": s.generation,
                    "dna": s.dna,
                    "fitness": s.fitness,
                    "metrics": s.metrics
                }
                for s in self.snapshots
            ]
        }
    
    @classmethod
    def from_file(cls, path: Path) -> "EvolutionHistory":
        """Load from JSON file."""
        history = cls()
        if path.exists():
            with open(path) as f:
                data = json.load(f)
            for s in data.get("snapshots", []):
                history.add(DNASnapshot(
                    generation=s["generation"],
                    dna=s["dna"],
                    fitness=s["fitness"],
                    metrics=s.get("metrics", {})
                ))
        return history
    
    @classmethod
    def from_dna_tracker(cls) -> "EvolutionHistory":
        """Load from DNA tracker cache."""
        history = cls()
        cache_path = ROOT / "data" / "dna_history" / "evolution_cache.json"
        
        if cache_path.exists():
            with open(cache_path) as f:
                data = json.load(f)
            for s in data.get("history", []):
                history.add(DNASnapshot(
                    generation=s.get("generation", 0),
                    dna=s.get("dna", []),
                    fitness=s.get("fitness", 0),
                    metrics=s.get("metrics", {})
                ))
        
        return history


class DNAEvolutionVisualizer:
    """
    3D Visualization of DNA evolution.
    
    Creates:
    - Fitness landscape surface
    - Evolution trajectory
    - Parameter correlation heatmaps
    - Generation comparison charts
    
    Usage:
        viz = DNAEvolutionVisualizer()
        viz.load_history()
        
        # Generate all visualizations
        viz.create_fitness_trajectory()
        viz.create_3d_landscape()
        viz.create_parameter_heatmap()
        
        # Save to HTML
        viz.save_dashboard("evolution_dashboard.html")
    """
    
    def __init__(self, history: Optional[EvolutionHistory] = None):
        self.history = history or EvolutionHistory()
        self.figures: Dict[str, Any] = {}
    
    def load_history(self, path: Optional[Path] = None) -> None:
        """Load evolution history."""
        if path:
            self.history = EvolutionHistory.from_file(path)
        else:
            self.history = EvolutionHistory.from_dna_tracker()
    
    def create_fitness_trajectory(self) -> Any:
        """Create 2D fitness over generations chart."""
        if not self.history.snapshots:
            return None
        
        generations = self.history.generations
        fitness = self.history.fitness_values
        
        if HAS_PLOTLY:
            fig = go.Figure()
            
            # Fitness line
            fig.add_trace(go.Scatter(
                x=generations,
                y=fitness,
                mode='lines+markers',
                name='Fitness',
                line=dict(color='#00ff88', width=2),
                marker=dict(size=8, color='#00ff88')
            ))
            
            # Moving average
            if len(fitness) > 5:
                ma = np.convolve(fitness, np.ones(5)/5, mode='valid')
                fig.add_trace(go.Scatter(
                    x=generations[4:],
                    y=ma,
                    mode='lines',
                    name='5-gen MA',
                    line=dict(color='#ffaa00', width=2, dash='dash')
                ))
            
            fig.update_layout(
                title='DNA Fitness Evolution',
                xaxis_title='Generation',
                yaxis_title='Fitness Score',
                template='plotly_dark',
                height=400
            )
            
            self.figures['fitness_trajectory'] = fig
            return fig
        else:
            fig, ax = plt.subplots(figsize=(10, 6))
            ax.plot(generations, fitness, 'g-o', label='Fitness')
            ax.set_xlabel('Generation')
            ax.set_ylabel('Fitness Score')
            ax.set_title('DNA Fitness Evolution')
            ax.legend()
            ax.grid(True, alpha=0.3)
            self.figures['fitness_trajectory'] = fig
            return fig
    
    def create_3d_landscape(self) -> Any:
        """Create 3D fitness landscape visualization."""
        if not self.history.snapshots or len(self.history.snapshots) < 3:
            return None
        
        # Extract first two DNA parameters for X, Y axes
        data = []
        for s in self.history.snapshots:
            if len(s.dna) >= 2:
                data.append({
                    'x': s.dna[0],
                    'y': s.dna[1],
                    'z': s.fitness,
                    'gen': s.generation
                })
        
        if not data:
            return None
        
        x = [d['x'] for d in data]
        y = [d['y'] for d in data]
        z = [d['z'] for d in data]
        gens = [d['gen'] for d in data]
        
        if HAS_PLOTLY:
            fig = go.Figure()
            
            # Evolution trajectory as 3D line
            fig.add_trace(go.Scatter3d(
                x=x, y=y, z=z,
                mode='lines+markers',
                marker=dict(
                    size=8,
                    color=gens,
                    colorscale='Viridis',
                    colorbar=dict(title='Generation')
                ),
                line=dict(color='white', width=2),
                name='Evolution Path',
                text=[f"Gen {g}" for g in gens],
                hoverinfo='text+z'
            ))
            
            # Mark start and end
            fig.add_trace(go.Scatter3d(
                x=[x[0]], y=[y[0]], z=[z[0]],
                mode='markers',
                marker=dict(size=15, color='red', symbol='diamond'),
                name='Start'
            ))
            
            fig.add_trace(go.Scatter3d(
                x=[x[-1]], y=[y[-1]], z=[z[-1]],
                mode='markers',
                marker=dict(size=15, color='green', symbol='diamond'),
                name='Current Best'
            ))
            
            fig.update_layout(
                title='DNA Evolution 3D Landscape',
                scene=dict(
                    xaxis_title='DNA[0] - Aggression',
                    yaxis_title='DNA[1] - Sensitivity',
                    zaxis_title='Fitness',
                    bgcolor='rgb(20, 20, 30)'
                ),
                template='plotly_dark',
                height=600
            )
            
            self.figures['3d_landscape'] = fig
            return fig
        else:
            fig = plt.figure(figsize=(12, 8))
            ax = fig.add_subplot(111, projection='3d')
            
            scatter = ax.scatter(x, y, z, c=gens, cmap='viridis', s=50)
            ax.plot(x, y, z, 'w-', alpha=0.5)
            
            ax.set_xlabel('DNA[0]')
            ax.set_ylabel('DNA[1]')
            ax.set_zlabel('Fitness')
            ax.set_title('DNA Evolution 3D Landscape')
            
            plt.colorbar(scatter, label='Generation')
            self.figures['3d_landscape'] = fig
            return fig
    
    def create_parameter_heatmap(self) -> Any:
        """Create DNA parameter correlation heatmap."""
        if not self.history.snapshots:
            return None
        
        # Get all DNA parameters
        all_dna = [s.dna for s in self.history.snapshots if s.dna]
        if not all_dna:
            return None
        
        max_len = max(len(d) for d in all_dna)
        
        # Pad shorter DNAs
        padded = []
        for d in all_dna:
            padded.append(d + [0] * (max_len - len(d)))
        
        dna_array = np.array(padded)
        
        # Calculate correlation with fitness
        fitness = np.array(self.history.fitness_values)
        correlations = []
        
        for i in range(min(max_len, 10)):  # Limit to first 10 params
            if np.std(dna_array[:, i]) > 0:
                corr = np.corrcoef(dna_array[:, i], fitness)[0, 1]
            else:
                corr = 0
            correlations.append(corr)
        
        param_names = [f'DNA[{i}]' for i in range(len(correlations))]
        
        if HAS_PLOTLY:
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                x=param_names,
                y=correlations,
                marker_color=['green' if c > 0 else 'red' for c in correlations]
            ))
            
            fig.update_layout(
                title='DNA Parameter Correlation with Fitness',
                xaxis_title='Parameter',
                yaxis_title='Correlation Coefficient',
                template='plotly_dark',
                height=400
            )
            
            self.figures['parameter_heatmap'] = fig
            return fig
        else:
            fig, ax = plt.subplots(figsize=(10, 6))
            colors = ['green' if c > 0 else 'red' for c in correlations]
            ax.bar(param_names, correlations, color=colors)
            ax.set_xlabel('Parameter')
            ax.set_ylabel('Correlation')
            ax.set_title('DNA Parameter Correlation with Fitness')
            ax.axhline(y=0, color='white', linestyle='-', alpha=0.3)
            self.figures['parameter_heatmap'] = fig
            return fig
    
    def create_generation_comparison(self, gen1: int, gen2: int) -> Any:
        """Compare two generations' DNA configurations."""
        snap1 = next((s for s in self.history.snapshots if s.generation == gen1), None)
        snap2 = next((s for s in self.history.snapshots if s.generation == gen2), None)
        
        if not snap1 or not snap2:
            return None
        
        params = list(range(min(len(snap1.dna), len(snap2.dna))))
        
        if HAS_PLOTLY:
            fig = go.Figure()
            
            fig.add_trace(go.Bar(
                name=f'Gen {gen1}',
                x=[f'P{i}' for i in params],
                y=snap1.dna[:len(params)],
                marker_color='blue'
            ))
            
            fig.add_trace(go.Bar(
                name=f'Gen {gen2}',
                x=[f'P{i}' for i in params],
                y=snap2.dna[:len(params)],
                marker_color='green'
            ))
            
            fig.update_layout(
                title=f'DNA Comparison: Gen {gen1} vs Gen {gen2}',
                barmode='group',
                template='plotly_dark',
                height=400
            )
            
            self.figures['generation_comparison'] = fig
            return fig
        
        return None
    
    def create_dashboard(self) -> Any:
        """Create combined dashboard with all visualizations."""
        if not HAS_PLOTLY:
            print("Plotly required for dashboard")
            return None
        
        # Generate all figures
        self.create_fitness_trajectory()
        self.create_3d_landscape()
        self.create_parameter_heatmap()
        
        # Combine into subplots
        fig = make_subplots(
            rows=2, cols=2,
            specs=[
                [{"type": "xy"}, {"type": "scene"}],
                [{"type": "xy"}, {"type": "xy"}]
            ],
            subplot_titles=(
                'Fitness Evolution',
                '3D Evolution Landscape',
                'Parameter Correlation',
                'Metrics Over Time'
            )
        )
        
        # Add fitness trajectory
        if 'fitness_trajectory' in self.figures:
            for trace in self.figures['fitness_trajectory'].data:
                fig.add_trace(trace, row=1, col=1)
        
        # Add parameter heatmap
        if 'parameter_heatmap' in self.figures:
            for trace in self.figures['parameter_heatmap'].data:
                fig.add_trace(trace, row=2, col=1)
        
        fig.update_layout(
            title='GODBRAIN DNA Evolution Dashboard',
            template='plotly_dark',
            height=800,
            showlegend=True
        )
        
        return fig
    
    def save_dashboard(self, filename: str = "evolution_dashboard.html") -> Path:
        """Save dashboard to HTML file."""
        if not HAS_PLOTLY:
            print("Plotly required for HTML export")
            return None
        
        dashboard = self.create_dashboard()
        if dashboard:
            output_path = ROOT / "reports" / filename
            output_path.parent.mkdir(parents=True, exist_ok=True)
            dashboard.write_html(str(output_path))
            return output_path
        return None


def generate_sample_history(n_generations: int = 50) -> EvolutionHistory:
    """Generate sample evolution history for testing."""
    history = EvolutionHistory()
    
    # Simulate evolution
    dna = [10, 10, 200, 300, 400, 500]
    fitness = 0.3
    
    for gen in range(n_generations):
        # Mutate DNA
        for i in range(len(dna)):
            dna[i] += random.randint(-20, 20)
            dna[i] = max(1, min(1000, dna[i]))
        
        # Simulate fitness improvement with noise
        fitness += random.uniform(-0.02, 0.05)
        fitness = max(0.1, min(1.0, fitness))
        
        history.add(DNASnapshot(
            generation=gen,
            dna=dna.copy(),
            fitness=fitness,
            metrics={
                "sharpe": fitness * 1.5 + random.uniform(-0.2, 0.2),
                "max_dd": -0.1 - random.uniform(0, 0.1),
                "win_rate": 0.5 + fitness * 0.2
            }
        ))
    
    return history


if __name__ == "__main__":
    import random
    
    print("DNA Evolution Visualizer Demo")
    print("=" * 60)
    
    # Generate sample data
    print("Generating sample evolution history...")
    history = generate_sample_history(50)
    
    # Create visualizer
    viz = DNAEvolutionVisualizer(history)
    
    # Generate visualizations
    print("Creating visualizations...")
    viz.create_fitness_trajectory()
    viz.create_3d_landscape()
    viz.create_parameter_heatmap()
    
    if HAS_PLOTLY:
        output = viz.save_dashboard()
        print(f"\nDashboard saved to: {output}")
    else:
        print("Install plotly for interactive dashboards: pip install plotly")
        print("Falling back to matplotlib...")
        plt.show()
