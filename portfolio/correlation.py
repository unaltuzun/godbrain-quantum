# -*- coding: utf-8 -*-
"""
📈 CORRELATION ANALYZER - Correlation Matrix & Regime Detection
"""

import numpy as np
from typing import Dict, List
from dataclasses import dataclass
from datetime import datetime
import pandas as pd


@dataclass
class CorrelationRegime:
    regime: str  # 'normal', 'crisis', 'divergence'
    avg_correlation: float
    max_correlation: float
    timestamp: datetime


class CorrelationAnalyzer:
    """
    Analyze asset correlations and detect regime changes.
    """
    
    def correlation_matrix(self, symbols: List[str], days: int = 90) -> pd.DataFrame:
        """Calculate correlation matrix."""
        # Mock returns data
        import random
        
        data = {}
        for sym in symbols:
            base_return = random.uniform(-0.001, 0.001)
            data[sym] = [base_return + random.gauss(0, 0.02) for _ in range(days)]
        
        df = pd.DataFrame(data)
        return df.corr()
    
    def rolling_correlation(self, sym1: str, sym2: str, window: int = 30) -> List[float]:
        """Calculate rolling correlation between two assets."""
        import random
        # Mock rolling correlation
        correlations = []
        current = random.uniform(0.3, 0.7)
        
        for _ in range(100):
            current += random.gauss(0, 0.05)
            current = max(-1, min(1, current))
            correlations.append(current)
        
        return correlations
    
    def correlation_breakdown_detect(self, symbols: List[str]) -> bool:
        """
        Detect correlation breakdown (crisis mode).
        Returns True if correlations spiked to 1.
        """
        matrix = self.correlation_matrix(symbols)
        
        # Check off-diagonal elements
        off_diag = []
        for i, sym1 in enumerate(symbols):
            for j, sym2 in enumerate(symbols):
                if i < j:
                    off_diag.append(abs(matrix.loc[sym1, sym2]))
        
        avg_corr = np.mean(off_diag) if off_diag else 0
        return avg_corr > 0.8  # Crisis if avg correlation > 0.8
    
    def diversification_score(self, portfolio: Dict[str, float]) -> float:
        """
        Calculate portfolio diversification score.
        0-100, higher = more diversified.
        """
        symbols = list(portfolio.keys())
        weights = list(portfolio.values())
        
        matrix = self.correlation_matrix(symbols)
        
        # Weighted average correlation
        total = 0
        weight_sum = 0
        
        for i, sym1 in enumerate(symbols):
            for j, sym2 in enumerate(symbols):
                if i < j:
                    w = weights[i] * weights[j]
                    c = matrix.loc[sym1, sym2]
                    total += w * c
                    weight_sum += w
        
        avg_corr = total / weight_sum if weight_sum > 0 else 0
        
        # Convert to score
        return (1 - avg_corr) * 100
    
    def regime_detect(self, symbols: List[str]) -> str:
        """
        Detect correlation regime.
        Returns: 'normal', 'crisis', or 'divergence'
        """
        matrix = self.correlation_matrix(symbols)
        
        off_diag = []
        for i, sym1 in enumerate(symbols):
            for j, sym2 in enumerate(symbols):
                if i < j:
                    off_diag.append(matrix.loc[sym1, sym2])
        
        avg = np.mean(off_diag) if off_diag else 0
        
        if avg > 0.7:
            return 'crisis'
        elif avg < 0.2:
            return 'divergence'
        return 'normal'
