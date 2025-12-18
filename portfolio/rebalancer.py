# -*- coding: utf-8 -*-
"""
🔄 DYNAMIC REBALANCER - Portfolio Rebalancing
Threshold-based rebalancing with tax-loss harvesting.
"""

from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class RebalanceOrder:
    symbol: str
    side: str  # 'buy' or 'sell'
    quantity: float
    notional_usd: float
    reason: str


class DynamicRebalancer:
    """
    Dynamic portfolio rebalancing.
    
    Features:
    - Drift detection
    - Threshold-based rebalancing
    - Tax-loss harvesting
    """
    
    def __init__(self, target_weights: Dict[str, float], threshold: float = 0.05):
        self.target_weights = target_weights
        self.threshold = threshold
    
    def check_drift(self, current_weights: Dict[str, float]) -> Dict[str, float]:
        """Check drift from target weights."""
        drift = {}
        for sym in self.target_weights:
            current = current_weights.get(sym, 0)
            target = self.target_weights[sym]
            drift[sym] = current - target
        return drift
    
    def rebalance_needed(self, current_weights: Dict[str, float]) -> bool:
        """Check if rebalancing is needed."""
        drift = self.check_drift(current_weights)
        max_drift = max(abs(d) for d in drift.values())
        return max_drift > self.threshold
    
    def generate_rebalance_orders(self, current_weights: Dict[str, float], 
                                   portfolio_value: float) -> List[RebalanceOrder]:
        """Generate orders to rebalance portfolio."""
        orders = []
        drift = self.check_drift(current_weights)
        
        for sym, d in drift.items():
            if abs(d) > self.threshold / 2:  # Only trade if meaningful
                notional = abs(d) * portfolio_value
                orders.append(RebalanceOrder(
                    symbol=sym,
                    side='sell' if d > 0 else 'buy',
                    quantity=0,  # Would calculate based on price
                    notional_usd=notional,
                    reason='rebalance'
                ))
        
        return orders
    
    def tax_loss_harvest(self, positions: Dict[str, Dict]) -> List[RebalanceOrder]:
        """
        Generate tax-loss harvesting orders.
        
        Args:
            positions: Dict of symbol -> {cost_basis, current_value, unrealized_pnl}
        """
        orders = []
        
        for sym, pos in positions.items():
            unrealized = pos.get('unrealized_pnl', 0)
            cost_basis = pos.get('cost_basis', 0)
            
            # If loss > 5% of cost basis, consider harvesting
            if unrealized < 0 and abs(unrealized) > cost_basis * 0.05:
                orders.append(RebalanceOrder(
                    symbol=sym,
                    side='sell',
                    quantity=pos.get('quantity', 0),
                    notional_usd=pos.get('current_value', 0),
                    reason='tax_loss_harvest'
                ))
        
        return orders


@dataclass
class CorrelationRegime:
    regime: str  # 'normal', 'crisis', 'divergence'
    avg_correlation: float
    max_correlation: float
    correlation_change: float
    timestamp: datetime


class CorrelationAnalyzer:
    """
    Analyze correlations between assets.
    Detect correlation regime changes.
    """
    
    def correlation_matrix(self, returns: Dict[str, List[float]]) -> Dict[str, Dict[str, float]]:
        """Calculate correlation matrix."""
        import numpy as np
        
        symbols = list(returns.keys())
        n = len(symbols)
        data = np.array([returns[s] for s in symbols])
        
        corr = np.corrcoef(data)
        
        matrix = {}
        for i, sym1 in enumerate(symbols):
            matrix[sym1] = {}
            for j, sym2 in enumerate(symbols):
                matrix[sym1][sym2] = float(corr[i, j])
        
        return matrix
    
    def diversification_score(self, returns: Dict[str, List[float]], 
                               weights: Dict[str, float]) -> float:
        """
        Calculate diversification score.
        Higher = more diversified.
        """
        import numpy as np
        
        matrix = self.correlation_matrix(returns)
        symbols = list(weights.keys())
        
        # Weighted average correlation
        total_corr = 0
        total_weight = 0
        
        for i, sym1 in enumerate(symbols):
            for j, sym2 in enumerate(symbols):
                if i != j:
                    w = weights.get(sym1, 0) * weights.get(sym2, 0)
                    c = matrix.get(sym1, {}).get(sym2, 1)
                    total_corr += w * c
                    total_weight += w
        
        avg_corr = total_corr / total_weight if total_weight > 0 else 1
        
        # Score: 0 (fully correlated) to 100 (uncorrelated)
        return (1 - avg_corr) * 100
    
    def regime_detect(self, returns: Dict[str, List[float]], 
                      lookback: int = 30) -> CorrelationRegime:
        """Detect correlation regime."""
        import numpy as np
        
        matrix = self.correlation_matrix(returns)
        symbols = list(returns.keys())
        
        # Calculate average off-diagonal correlation
        correlations = []
        for i, sym1 in enumerate(symbols):
            for j, sym2 in enumerate(symbols):
                if i < j:
                    correlations.append(matrix[sym1][sym2])
        
        avg_corr = np.mean(correlations) if correlations else 0
        max_corr = np.max(correlations) if correlations else 0
        
        # Determine regime
        if avg_corr > 0.8:
            regime = 'crisis'  # Everything moving together
        elif avg_corr < 0.2:
            regime = 'divergence'  # Assets uncorrelated
        else:
            regime = 'normal'
        
        return CorrelationRegime(
            regime=regime,
            avg_correlation=float(avg_corr),
            max_correlation=float(max_corr),
            correlation_change=0,  # Would compare to previous period
            timestamp=datetime.now()
        )
