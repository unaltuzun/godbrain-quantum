# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN Lab Bridge
Connects Physics Lab insights to main DNA system.
═══════════════════════════════════════════════════════════════════════════════

This bridge:
1. Reads stability/robustness metrics from Physics Lab
2. Injects "survival awareness" into trading DNA evaluation
3. Provides noise robustness testing for trading strategies
4. Exports Pareto insights for multi-objective trading

The lab does NOT optimize - it observes what survives.
The bridge translates survival patterns into trading wisdom.
"""

import json
import numpy as np
from pathlib import Path
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
import logging

logger = logging.getLogger("godbrain.bridge")

# Cache file location (written by eternal_evolution.py)
DATA_DIR = Path(__file__).parent.parent / "data"
LAB_STATE_CACHE = DATA_DIR / "lab_state.json"

# Default values when lab is unavailable
DEFAULT_LAB_STATE = {
    "noise_robustness": 0.5,
    "avg_f_stab": 0.1,
    "avg_f_energy": 0.1,
    "suggested_dd_tolerance": 0.3,
    "regime_stability": 0.9,
    "pareto_front": [],
}


# =============================================================================
# CACHE-FIRST DATA ACCESS (DECOUPLED)
# =============================================================================

def get_cached_lab_state() -> Dict[str, Any]:
    """
    Get lab state from cache file (written by evolution daemon).
    
    This is the PRIMARY method for trading system to access lab data.
    Fully decoupled - doesn't import lab modules directly.
    
    Returns cached state or defaults if unavailable.
    """
    try:
        if LAB_STATE_CACHE.exists():
            data = json.loads(LAB_STATE_CACHE.read_text(encoding='utf-8'))
            data["_source"] = "cache"
            data["_cache_age_seconds"] = (
                datetime.now() - datetime.fromisoformat(data.get("timestamp", datetime.now().isoformat()))
            ).total_seconds()
            return data
    except Exception as e:
        logger.warning(f"Cache read failed: {e}")
    
    # Return defaults
    return {**DEFAULT_LAB_STATE, "_source": "default"}


def get_lab_insights_fast() -> Dict[str, Any]:
    """
    Fast, decoupled access to lab insights for trading.
    
    Use this in trading code - it reads from cache, never blocks.
    """
    state = get_cached_lab_state()
    
    return {
        "noise_robustness": state.get("noise_robustness", 0.5),
        "stability": state.get("avg_f_stab", 0.1),
        "energy": state.get("avg_f_energy", 0.1),
        "suggested_dd_tolerance": state.get("suggested_dd_tolerance", 0.3),
        "regime_stability": state.get("regime_stability", 0.9),
        "generation": state.get("generation", 0),
        "pareto_size": state.get("pareto_front_size", 0),
        "_source": state.get("_source", "unknown"),
    }


# =============================================================================
# PHYSICS LAB DIRECT ACCESS (OPTIONAL - FOR DEEP ANALYSIS)
# =============================================================================

def get_lab_vault():
    """Get the physics lab vault (lazy import to avoid circular deps)."""
    try:
        from quantum_lab.godbrain_core.genome_vault import get_vault
        return get_vault()
    except ImportError as e:
        logger.warning(f"Physics lab not available: {e}")
        return None


def get_lab_statistics() -> Optional[Dict[str, Any]]:
    """Get current physics lab statistics."""
    vault = get_lab_vault()
    if vault:
        return vault.get_statistics()
    return None


# =============================================================================
# STABILITY METRICS
# =============================================================================

@dataclass
class StabilityProfile:
    """
    Stability profile derived from physics lab.
    
    These metrics help trading strategies understand how to survive noise.
    """
    # Core metrics from physics lab
    avg_stability: float = 0.0      # Lower = more stable attractor
    avg_energy: float = 0.0         # Lower = more efficient dynamics
    noise_robustness: float = 0.0   # Fraction surviving high noise
    
    # Derived wisdom
    stability_energy_ratio: float = 0.0  # Trade-off balance
    diversity_score: float = 0.0         # Pareto front diversity
    
    # Lab metadata
    source_genomes: int = 0
    pareto_size: int = 0
    max_lineage: int = 0
    
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    def to_trading_weights(self) -> Dict[str, float]:
        """
        Convert stability profile to trading parameter suggestions.
        
        Maps physics insights to trading wisdom:
        - High stability → Can use tighter stop losses
        - High energy → Expect more volatility
        - High noise robustness → Can trade in choppy markets
        """
        return {
            "suggested_dd_tolerance": min(0.5, 0.1 + self.noise_robustness * 0.4),
            "volatility_expectation": self.avg_energy,
            "regime_stability": 1.0 - self.avg_stability,
            "diversity_factor": self.diversity_score,
        }


def compute_stability_profile() -> Optional[StabilityProfile]:
    """
    Compute stability profile from physics lab data.
    
    This is the main bridge function - translates physics into trading insights.
    """
    vault = get_lab_vault()
    if not vault:
        return None
    
    alive = vault.get_alive()
    if not alive:
        return None
    
    pareto = vault.get_pareto_genomes()
    stats = vault.get_statistics()
    
    # Compute averages from alive genomes
    stabilities = [g.f_stab for g in alive if g.f_stab is not None]
    energies = [g.f_energy for g in alive if g.f_energy is not None]
    
    avg_stab = np.mean(stabilities) if stabilities else 0.0
    avg_energy = np.mean(energies) if energies else 0.0
    
    # Noise robustness: fraction surviving at highest sigma
    high_noise_survivors = 0
    for g in alive:
        if g.noise_survival and g.noise_survival.get("0.3", False):
            high_noise_survivors += 1
    noise_robustness = high_noise_survivors / len(alive) if alive else 0.0
    
    # Diversity from Pareto front
    if len(pareto) >= 2:
        # Spread in Pareto space
        pareto_stabs = [g.f_stab for g in pareto if g.f_stab]
        pareto_energies = [g.f_energy for g in pareto if g.f_energy]
        diversity = (np.std(pareto_stabs) + np.std(pareto_energies)) / 2 if pareto_stabs else 0.0
    else:
        diversity = 0.0
    
    return StabilityProfile(
        avg_stability=float(avg_stab),
        avg_energy=float(avg_energy),
        noise_robustness=float(noise_robustness),
        stability_energy_ratio=float(avg_stab / avg_energy) if avg_energy > 0 else 0.0,
        diversity_score=float(diversity),
        source_genomes=len(alive),
        pareto_size=len(pareto),
        max_lineage=stats.get("max_lineage_depth", 0),
    )


# =============================================================================
# DNA AUGMENTATION
# =============================================================================

def augment_dna_metrics(base_metrics: Dict[str, float]) -> Dict[str, float]:
    """
    Augment trading DNA metrics with physics lab insights.
    
    Takes base trading metrics and adds:
    - noise_robustness_bonus: Reward for noise-tolerant behavior
    - stability_factor: How stable the underlying dynamics are
    - survival_score: Multi-objective survival assessment
    
    Args:
        base_metrics: Original metrics {"sharpe": x, "pnl": y, ...}
    
    Returns:
        Augmented metrics with lab insights
    """
    augmented = dict(base_metrics)
    
    # Get lab profile
    profile = compute_stability_profile()
    
    if profile and profile.source_genomes > 0:
        # Add physics-derived metrics
        augmented["lab_stability"] = profile.avg_stability
        augmented["lab_energy"] = profile.avg_energy
        augmented["lab_noise_robustness"] = profile.noise_robustness
        augmented["lab_diversity"] = profile.diversity_score
        
        # Compute survival score (multi-objective)
        # Not a reward - just awareness of how physics behaves
        augmented["physics_survival_score"] = (
            profile.noise_robustness * 0.4 +
            (1.0 - min(1.0, profile.avg_stability)) * 0.3 +
            (1.0 - min(1.0, profile.avg_energy)) * 0.3
        )
        
        # Trading suggestions from physics
        weights = profile.to_trading_weights()
        for k, v in weights.items():
            augmented[f"physics_{k}"] = v
    
    return augmented


# =============================================================================
# NOISE ROBUSTNESS TESTING
# =============================================================================

def test_strategy_robustness(
    strategy_fn,
    noise_levels: List[float] = [0.05, 0.15, 0.30],
    n_trials: int = 10
) -> Dict[str, Any]:
    """
    Test a trading strategy's robustness under different noise levels.
    
    Inspired by physics lab methodology:
    - Run strategy multiple times at each noise level
    - Track survival rate (doesn't blow up)
    - Measure performance consistency
    
    Args:
        strategy_fn: Callable that returns (pnl, survived: bool)
        noise_levels: Volatility multipliers to test
        n_trials: Trials per noise level
    
    Returns:
        Robustness assessment
    """
    results = {}
    
    for noise in noise_levels:
        survivals = 0
        pnls = []
        
        for _ in range(n_trials):
            try:
                pnl, survived = strategy_fn(noise_multiplier=noise)
                if survived:
                    survivals += 1
                    pnls.append(pnl)
            except Exception as e:
                logger.debug(f"Strategy failed at noise {noise}: {e}")
        
        results[f"noise_{noise}"] = {
            "survival_rate": survivals / n_trials,
            "avg_pnl": np.mean(pnls) if pnls else 0.0,
            "pnl_std": np.std(pnls) if len(pnls) > 1 else 0.0,
        }
    
    # Overall robustness score
    survival_rates = [r["survival_rate"] for r in results.values()]
    results["overall_robustness"] = np.mean(survival_rates) if survival_rates else 0.0
    
    return results


# =============================================================================
# PARETO INSIGHTS FOR TRADING
# =============================================================================

def get_pareto_trade_insights() -> List[Dict[str, Any]]:
    """
    Extract trading insights from physics lab Pareto front.
    
    The Pareto front shows optimal trade-offs between stability and energy.
    This translates to trading as: risk vs. reward non-dominated solutions.
    """
    vault = get_lab_vault()
    if not vault:
        return []
    
    pareto = vault.get_pareto_genomes()
    
    insights = []
    for g in pareto:
        insight = {
            "genome_id": g.genome_id[:8],
            "stability": g.f_stab,
            "energy": g.f_energy,
            "lineage_depth": g.lineage_depth,
            "noise_survival": g.noise_survival,
            
            # Trading interpretation
            "trading_hint": "",
        }
        
        # Interpret for trading
        if g.f_stab < 0.05 and g.f_energy < 0.08:
            insight["trading_hint"] = "LOW_RISK_LOW_REWARD: Stable, efficient - good for ranging markets"
        elif g.f_stab > 0.2:
            insight["trading_hint"] = "HIGH_VARIANCE: Dynamic system - may suit trending markets"
        elif g.f_energy > 0.15:
            insight["trading_hint"] = "HIGH_ENERGY: Active dynamics - consider momentum strategies"
        else:
            insight["trading_hint"] = "BALANCED: Moderate risk/reward profile"
        
        insights.append(insight)
    
    return insights


# =============================================================================
# BRIDGE STATUS
# =============================================================================

def get_bridge_status() -> Dict[str, Any]:
    """Get complete bridge status."""
    vault = get_lab_vault()
    profile = compute_stability_profile()
    
    return {
        "lab_connected": vault is not None,
        "lab_stats": get_lab_statistics() if vault else None,
        "stability_profile": profile.to_dict() if profile else None,
        "pareto_insights": get_pareto_trade_insights(),
        "bridge_timestamp": datetime.now().isoformat(),
    }


# =============================================================================
# CLI
# =============================================================================

if __name__ == "__main__":
    print("=== GODBRAIN LAB BRIDGE ===\n")
    
    status = get_bridge_status()
    
    print(f"Lab Connected: {status['lab_connected']}")
    
    if status['lab_stats']:
        print(f"\nLab Statistics:")
        for k, v in status['lab_stats'].items():
            print(f"  {k}: {v}")
    
    if status['stability_profile']:
        print(f"\nStability Profile:")
        for k, v in status['stability_profile'].items():
            print(f"  {k}: {v}")
    
    if status['pareto_insights']:
        print(f"\nPareto Insights ({len(status['pareto_insights'])} genomes):")
        for insight in status['pareto_insights'][:5]:
            print(f"  {insight['genome_id']}: {insight['trading_hint']}")
