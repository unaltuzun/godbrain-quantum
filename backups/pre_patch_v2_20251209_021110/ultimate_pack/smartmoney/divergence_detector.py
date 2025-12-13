from dataclasses import dataclass
from datetime import datetime
from typing import Dict

@dataclass
class DivergenceSignal:
    timestamp: datetime
    divergence_type: str  # BULLISH_DIV, BEARISH_DIV, NO_SIGNAL
    smart_money_pos: str  # LONG/SHORT
    retail_pos: str       # LONG/SHORT
    strength: float
    action: str

class SmartMoneyDivergence:
    """
    Detects when retail and smart money are betting against each other.
    Requires data feeds for Long/Short Ratios (Retail) and Whale Flows (Smart).
    """
    def __init__(self):
        pass
        
    def analyze(self, retail_ls_ratio: float, whale_net_flow: float) -> DivergenceSignal:
        """
        retail_ls_ratio: > 1.0 means retail is LONG
        whale_net_flow: > 0 means whales are ACCUMULATING
        """
        retail_pos = "LONG" if retail_ls_ratio > 1.2 else "SHORT" if retail_ls_ratio < 0.8 else "NEUTRAL"
        smart_pos = "LONG" if whale_net_flow > 1000000 else "SHORT" if whale_net_flow < -1000000 else "NEUTRAL"
        
        div_type = "NO_SIGNAL"
        strength = 0.0
        action = "HOLD"
        
        # Classic Smart Money Divergence
        if smart_pos == "LONG" and retail_pos == "SHORT":
            div_type = "BULLISH_DIVERGENCE"
            strength = 0.9
            action = "STRONG_BUY"
        elif smart_pos == "SHORT" and retail_pos == "LONG":
            div_type = "BEARISH_DIVERGENCE"
            strength = 0.9
            action = "STRONG_SELL"
        elif smart_pos == retail_pos and smart_pos != "NEUTRAL":
            div_type = "CONFIRMATION"
            strength = 0.6
            action = "FOLLOW_TREND"
            
        return DivergenceSignal(
            timestamp=datetime.now(),
            divergence_type=div_type,
            smart_money_pos=smart_pos,
            retail_pos=retail_pos,
            strength=strength,
            action=action
        )
