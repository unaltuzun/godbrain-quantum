"""
Slippage simulation models for realistic backtesting.
"""

import numpy as np


class SlippageModel:
    """Base slippage model."""
    def calculate(self, price: float, size: float, side: str) -> float:
        raise NotImplementedError


class VolumeSlippageModel(SlippageModel):
    """
    Volume-based slippage model.
    
    Larger orders experience more slippage due to:
    - Order book depth limitations
    - Market impact
    - Execution delays
    """
    
    def __init__(self, base_slippage: float = 0.0001):
        """
        Args:
            base_slippage: Base slippage percentage (default 0.01%)
        """
        self.base_slippage = base_slippage
    
    def calculate(self, price: float, size: float, side: str) -> float:
        """
        Calculate slippage for order.
        
        Args:
            price: Current market price
            size: Order size in quote currency
            side: 'buy', 'long', 'sell', or 'short'
        
        Returns:
            Slippage as decimal (positive = unfavorable execution)
        """
        # Larger orders = more slippage (logarithmic scaling)
        size_factor = np.log1p(size / 10000) / 10
        slippage = self.base_slippage * (1 + size_factor)
        
        # Positive for buys (pay more), negative for sells (receive less)
        return slippage if side in ['buy', 'long'] else -slippage


class VolatilitySlippageModel(SlippageModel):
    """
    Volatility-adjusted slippage model.
    
    Higher volatility = wider spreads = more slippage.
    """
    
    def __init__(self, base_slippage: float = 0.0001, volatility_scalar: float = 10.0):
        self.base_slippage = base_slippage
        self.volatility_scalar = volatility_scalar
        self.current_volatility = 0.02  # 2% default
    
    def set_volatility(self, volatility: float):
        """Set current market volatility (as decimal)."""
        self.current_volatility = volatility
    
    def calculate(self, price: float, size: float, side: str) -> float:
        # Volatility factor
        vol_factor = 1 + (self.current_volatility * self.volatility_scalar)
        
        # Size factor
        size_factor = np.log1p(size / 10000) / 10
        
        slippage = self.base_slippage * vol_factor * (1 + size_factor)
        
        return slippage if side in ['buy', 'long'] else -slippage


class FixedSlippageModel(SlippageModel):
    """Simple fixed slippage model."""
    
    def __init__(self, slippage: float = 0.0001):
        self.slippage = slippage
    
    def calculate(self, price: float, size: float, side: str) -> float:
        return self.slippage if side in ['buy', 'long'] else -self.slippage
