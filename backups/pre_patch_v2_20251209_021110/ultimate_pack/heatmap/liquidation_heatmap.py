from dataclasses import dataclass
from typing import List
from datetime import datetime

@dataclass
class LiquidationLevel:
    price: float
    estimated_volume: float
    leverage_tier: int

@dataclass
class HeatmapSignal:
    timestamp: datetime
    nearest_long_liq: float
    nearest_short_liq: float
    magnet_direction: str
    cascade_risk: float

class LiquidationHeatmap:
    """
    Estimates liquidation clusters based on Open Interest and Price Action.
    Simplified probabilistic model.
    """
    def __init__(self):
        self.levels = []
        
    def update(self, current_price: float, open_interest: float):
        # Simulation Logic:
        # Assume new OI enters at current price with diverse leverage
        # 50x liq is +/- 2%
        # 20x liq is +/- 5%
        # 10x liq is +/- 10%
        
        # Store simplistic levels for magnet calculation
        long_50x = current_price * 0.98
        short_50x = current_price * 1.02
        
        return HeatmapSignal(
            timestamp=datetime.now(),
            nearest_long_liq=long_50x,
            nearest_short_liq=short_50x,
            magnet_direction="NEUTRAL", # Needs deeper logic
            cascade_risk=0.5
        )
