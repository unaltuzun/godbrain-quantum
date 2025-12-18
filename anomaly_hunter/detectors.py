# -*- coding: utf-8 -*-
"""
GODBRAIN ANOMALY DETECTORS
Nobel-worthy anomaly detection algorithms
"""

import numpy as np
import pandas as pd
from datetime import datetime
from typing import List, Optional
from scipy import stats
from scipy.signal import find_peaks

from . import Anomaly, AnomalyType, NobelPotential


class UniversalAttractorDetector:
    """Detects if all evolutionary paths converge to same point."""
    
    def __init__(self, convergence_threshold: float = 0.05):
        self.threshold = convergence_threshold
    
    def detect(self, df: pd.DataFrame) -> Optional[Anomaly]:
        if len(df) < 100:
            return None
        
        mature = df.tail(int(len(df) * 0.2))
        
        stab_var = mature['f_stab'].var() if 'f_stab' in df.columns else 1.0
        energy_var = mature['f_energy'].var() if 'f_energy' in df.columns else 1.0
        
        is_converging = stab_var < self.threshold and energy_var < self.threshold
        
        if is_converging:
            attractor_point = (mature['f_stab'].mean(), mature['f_energy'].mean())
            
            return Anomaly(
                id=f"attractor_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                type=AnomalyType.UNIVERSAL_ATTRACTOR,
                timestamp=datetime.now(),
                title="Universal Attractor Detected!",
                description=f"All lineages converging to point {attractor_point}",
                confidence=1 - (stab_var + energy_var) / 2,
                significance=1 / (stab_var + energy_var + 1e-10),
                nobel_potential=NobelPotential.HIGH if stab_var < 0.01 else NobelPotential.MEDIUM,
                generation_range=(int(df['generation'].min()), int(df['generation'].max())),
                affected_genomes=len(mature),
                raw_data={'attractor': attractor_point},
                evidence=[f"Variance: stab={stab_var:.6f}, energy={energy_var:.6f}"]
            )
        return None


class PhaseTransitionDetector:
    """Detects sudden regime changes in evolution."""
    
    def __init__(self, sensitivity: float = 3.0):
        self.sensitivity = sensitivity
    
    def detect(self, df: pd.DataFrame) -> List[Anomaly]:
        if len(df) < 50:
            return []
        
        anomalies = []
        
        for col in ['f_stab', 'f_energy']:
            if col not in df.columns:
                continue
            
            series = df[col].values
            window = min(50, len(series) // 10)
            rolling_mean = pd.Series(series).rolling(window).mean()
            
            diff = np.abs(np.diff(rolling_mean.dropna()))
            if len(diff) == 0:
                continue
                
            threshold = diff.mean() + self.sensitivity * diff.std()
            jump_indices = np.where(diff > threshold)[0]
            
            for idx in jump_indices[:3]:  # Max 3 per metric
                actual_gen = int(df.iloc[min(idx + window, len(df)-1)]['generation'])
                
                before = series[max(0, idx-window):idx].mean()
                after = series[idx:min(len(series), idx+window)].mean()
                jump_magnitude = abs(after - before)
                
                anomalies.append(Anomaly(
                    id=f"phase_{col}_{actual_gen}",
                    type=AnomalyType.PHASE_TRANSITION,
                    timestamp=datetime.now(),
                    title=f"Phase Transition in {col}!",
                    description=f"Sudden regime change at gen {actual_gen}, jump: {jump_magnitude:.4f}",
                    confidence=min(1.0, jump_magnitude * 10),
                    significance=jump_magnitude,
                    nobel_potential=NobelPotential.HIGH,
                    generation_range=(actual_gen - window, actual_gen + window),
                    affected_genomes=window * 2,
                    raw_data={'metric': col, 'before': before, 'after': after},
                    evidence=[f"Jump magnitude: {jump_magnitude:.4f}"]
                ))
        
        return anomalies


class PowerLawDetector:
    """Detects power law distributions in metrics."""
    
    def __init__(self, r_squared_threshold: float = 0.9):
        self.threshold = r_squared_threshold
    
    def detect(self, df: pd.DataFrame) -> List[Anomaly]:
        anomalies = []
        
        for col in ['f_stab', 'f_energy']:
            if col not in df.columns:
                continue
            
            data = df[col].dropna().values
            data = data[data > 0]
            
            if len(data) < 50:
                continue
            
            try:
                hist, bin_edges = np.histogram(data, bins=30, density=True)
                bin_centers = (bin_edges[:-1] + bin_edges[1:]) / 2
                
                mask = hist > 0
                log_x = np.log(bin_centers[mask])
                log_y = np.log(hist[mask])
                
                slope, intercept, r_value, _, _ = stats.linregress(log_x, log_y)
                r_squared = r_value ** 2
                
                if r_squared > self.threshold:
                    alpha = -slope
                    
                    anomalies.append(Anomaly(
                        id=f"powerlaw_{col}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                        type=AnomalyType.POWER_LAW,
                        timestamp=datetime.now(),
                        title=f"Power Law in {col}!",
                        description=f"Power law with α={alpha:.2f}, R²={r_squared:.4f}",
                        confidence=r_squared,
                        significance=1 / (1 - r_squared + 0.01),
                        nobel_potential=NobelPotential.HIGH if r_squared > 0.95 else NobelPotential.MEDIUM,
                        generation_range=(int(df['generation'].min()), int(df['generation'].max())),
                        affected_genomes=len(data),
                        raw_data={'alpha': alpha, 'r_squared': r_squared},
                        evidence=[f"Exponent α = {alpha:.2f}", f"R² = {r_squared:.4f}"]
                    ))
            except:
                continue
        
        return anomalies


class QuantumSignatureDetector:
    """Detects quantum-like signatures in classical evolution."""
    
    def detect(self, df: pd.DataFrame) -> List[Anomaly]:
        anomalies = []
        
        if len(df) < 200:
            return anomalies
        
        for col in ['f_stab', 'f_energy']:
            if col not in df.columns:
                continue
            
            data = df[col].dropna().values
            
            # Check for bimodal distribution
            hist, bin_edges = np.histogram(data, bins=50)
            peaks, _ = find_peaks(hist, height=hist.max() * 0.3)
            
            if len(peaks) == 2:
                peak_locs = [(bin_edges[p] + bin_edges[p+1]) / 2 for p in peaks]
                separation = abs(peak_locs[1] - peak_locs[0])
                
                anomalies.append(Anomaly(
                    id=f"quantum_super_{col}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    type=AnomalyType.QUANTUM_SIGNATURE,
                    timestamp=datetime.now(),
                    title=f"Superposition-like State in {col}!",
                    description=f"Bimodal distribution with peaks at {peak_locs}",
                    confidence=min(1.0, separation * 10),
                    significance=separation,
                    nobel_potential=NobelPotential.VERY_HIGH,
                    generation_range=(int(df['generation'].min()), int(df['generation'].max())),
                    affected_genomes=len(df),
                    raw_data={'peaks': peak_locs},
                    evidence=["System occupies TWO states simultaneously!"]
                ))
        
        return anomalies


class SymmetryBreakingDetector:
    """Detects spontaneous symmetry breaking."""
    
    def detect(self, df: pd.DataFrame) -> Optional[Anomaly]:
        if len(df) < 100:
            return None
        
        early = df.head(int(len(df) * 0.3))
        late = df.tail(int(len(df) * 0.3))
        
        for col in ['f_stab', 'f_energy']:
            if col not in df.columns:
                continue
            
            early_skew = stats.skew(early[col].dropna())
            late_skew = stats.skew(late[col].dropna())
            
            if abs(early_skew) < 0.5 and abs(late_skew) > 1.0:
                return Anomaly(
                    id=f"symmetry_{col}_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                    type=AnomalyType.SYMMETRY_BREAKING,
                    timestamp=datetime.now(),
                    title=f"Symmetry Breaking in {col}!",
                    description=f"Early skew={early_skew:.2f} → Late skew={late_skew:.2f}",
                    confidence=abs(late_skew) / (abs(late_skew) + abs(early_skew) + 0.1),
                    significance=abs(late_skew - early_skew),
                    nobel_potential=NobelPotential.HIGH,
                    generation_range=(int(df['generation'].min()), int(df['generation'].max())),
                    affected_genomes=len(df),
                    raw_data={'early_skew': early_skew, 'late_skew': late_skew},
                    evidence=["Symmetry spontaneously broken!"]
                )
        return None


class EntropyReversalDetector:
    """Detects apparent violations of entropy increase."""
    
    def __init__(self, window: int = 100):
        self.window = window
    
    def detect(self, df: pd.DataFrame) -> Optional[Anomaly]:
        if len(df) < self.window * 3 or 'f_stab' not in df.columns:
            return None
        
        entropies = []
        generations = []
        
        for i in range(self.window, len(df), self.window // 2):
            window_data = df['f_stab'].iloc[i-self.window:i].values
            hist, _ = np.histogram(window_data, bins=20, density=True)
            hist = hist[hist > 0]
            entropy = -np.sum(hist * np.log(hist + 1e-10))
            entropies.append(entropy)
            generations.append(df['generation'].iloc[i])
        
        if len(entropies) < 3:
            return None
        
        entropies = np.array(entropies)
        total_decrease = entropies[0] - entropies[-1] if entropies[-1] < entropies[0] else 0
        
        if total_decrease > 0.1:
            return Anomaly(
                id=f"entropy_{datetime.now().strftime('%Y%m%d_%H%M%S')}",
                type=AnomalyType.ENTROPY_REVERSAL,
                timestamp=datetime.now(),
                title="⚠️ ENTROPY REVERSAL! ⚠️",
                description=f"System entropy DECREASED by {total_decrease:.4f}!",
                confidence=min(1.0, total_decrease * 5),
                significance=total_decrease,
                nobel_potential=NobelPotential.NOBEL_WORTHY,
                generation_range=(int(generations[0]), int(generations[-1])),
                affected_genomes=len(df),
                raw_data={'total_decrease': total_decrease},
                evidence=["SECOND LAW OF THERMODYNAMICS CHALLENGED?!"]
            )
        return None
