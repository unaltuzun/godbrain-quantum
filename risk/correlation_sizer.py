import numpy as np
from typing import List, Dict

class CorrelationAwarePositionSizer:
    """
    GODBRAIN V3 RISK MODULE
    Prevents over-exposure to correlated assets.
    """
    def __init__(self):
        # Hardcoded correlation matrix for simulation speed
        # BTC, ETH, SOL
        self.corr_matrix = np.array([
            [1.0, 0.85, 0.70],
            [0.85, 1.0, 0.65],
            [0.70, 0.65, 1.0]
        ])
        self.assets = ["BTC", "ETH", "SOL"]

    def adjust_size(self, symbol: str, proposed_usd: float, current_portfolio_usd: float) -> float:
        """
        If portfolio is heavy on correlated assets, reduce new position size.
        """
        base_sym = symbol.split("/")[0]
        if base_sym not in self.assets:
            return proposed_usd
            
        # Mock logic: If portfolio > $5000, start reducing size by correlation factor
        if current_portfolio_usd > 5000:
            return proposed_usd * 0.8 # Safety buffer
            
        return proposed_usd
