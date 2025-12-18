# -*- coding: utf-8 -*-
"""
📊 VAR ENGINE - Value at Risk Calculation
Historical, Parametric, and Monte Carlo VaR.
"""

import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class VaRResult:
    var: float
    cvar: float  # Conditional VaR / Expected Shortfall
    confidence: float
    method: str
    horizon_days: int
    timestamp: datetime


class VaREngine:
    """
    Value at Risk calculation engine.
    
    Methods:
    - Historical VaR
    - Parametric VaR (assumes normal distribution)
    - Monte Carlo VaR
    - CVaR (Conditional VaR / Expected Shortfall)
    """
    
    def __init__(self, confidence: float = 0.95, horizon_days: int = 1):
        self.confidence = confidence
        self.horizon_days = horizon_days
    
    def historical_var(self, returns: np.ndarray, confidence: float = None) -> float:
        """
        Historical VaR - uses actual return distribution.
        
        Args:
            returns: Array of historical returns
            confidence: Confidence level (default: self.confidence)
        
        Returns:
            VaR as positive number (potential loss)
        """
        conf = confidence or self.confidence
        percentile = (1 - conf) * 100
        var = np.percentile(returns, percentile)
        return abs(var)
    
    def parametric_var(self, returns: np.ndarray, confidence: float = None) -> float:
        """
        Parametric VaR - assumes normal distribution.
        
        VaR = μ - z * σ
        where z is the z-score for confidence level
        """
        from scipy import stats
        
        conf = confidence or self.confidence
        z = stats.norm.ppf(1 - conf)
        
        mu = np.mean(returns)
        sigma = np.std(returns)
        
        var = -(mu + z * sigma)
        return abs(var)
    
    def monte_carlo_var(self, returns: np.ndarray, simulations: int = 10000,
                        confidence: float = None) -> float:
        """
        Monte Carlo VaR - simulate future scenarios.
        """
        conf = confidence or self.confidence
        
        mu = np.mean(returns)
        sigma = np.std(returns)
        
        # Generate simulated returns
        simulated = np.random.normal(mu, sigma, simulations)
        
        percentile = (1 - conf) * 100
        var = np.percentile(simulated, percentile)
        return abs(var)
    
    def cvar(self, returns: np.ndarray, confidence: float = None) -> float:
        """
        Conditional VaR (Expected Shortfall).
        
        Average loss when loss exceeds VaR.
        More conservative than VaR.
        """
        conf = confidence or self.confidence
        var = self.historical_var(returns, conf)
        
        # Get returns worse than VaR
        threshold = np.percentile(returns, (1 - conf) * 100)
        tail_returns = returns[returns <= threshold]
        
        if len(tail_returns) == 0:
            return var
        
        cvar = abs(np.mean(tail_returns))
        return cvar
    
    def portfolio_var(self, positions: Dict[str, Dict], 
                      returns_data: Dict[str, np.ndarray],
                      confidence: float = None) -> VaRResult:
        """
        Calculate portfolio VaR.
        
        Args:
            positions: Dict of symbol -> {value, weight}
            returns_data: Dict of symbol -> returns array
        """
        conf = confidence or self.confidence
        
        # Calculate portfolio returns
        weights = np.array([positions[sym]['weight'] for sym in positions])
        returns_matrix = np.array([returns_data[sym] for sym in positions])
        
        portfolio_returns = np.dot(weights, returns_matrix)
        
        var = self.historical_var(portfolio_returns, conf)
        cvar = self.cvar(portfolio_returns, conf)
        
        return VaRResult(
            var=var,
            cvar=cvar,
            confidence=conf,
            method='historical',
            horizon_days=self.horizon_days,
            timestamp=datetime.now()
        )
    
    def marginal_var(self, positions: Dict[str, Dict],
                     returns_data: Dict[str, np.ndarray],
                     new_position: Dict) -> float:
        """
        Calculate marginal VaR of adding a new position.
        
        Shows how much VaR increases with new position.
        """
        # VaR before
        var_before = self.portfolio_var(positions, returns_data).var
        
        # Add new position
        updated_positions = positions.copy()
        updated_positions[new_position['symbol']] = {
            'value': new_position['value'],
            'weight': new_position['weight']
        }
        
        # Normalize weights
        total_weight = sum(p['weight'] for p in updated_positions.values())
        for sym in updated_positions:
            updated_positions[sym]['weight'] /= total_weight
        
        # VaR after
        var_after = self.portfolio_var(updated_positions, returns_data).var
        
        return var_after - var_before
