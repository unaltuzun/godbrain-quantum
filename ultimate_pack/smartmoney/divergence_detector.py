from dataclasses import dataclass
from datetime import datetime
from typing import Dict, Optional

@dataclass
class DivergenceSignal:
    timestamp: datetime
    divergence_type: str
    smart_money_direction: str
    retail_direction: str
    divergence_strength: float
    recommended_action: str
    components: Dict

class SmartMoneyDivergence:
    def analyze(self, retail_ls_ratio=None, whale_net_flow_usd=None):
        components = {'retail': retail_ls_ratio, 'whale': whale_net_flow_usd}
        
        retail_dir = "NEUTRAL"
        if retail_ls_ratio:
            if retail_ls_ratio > 1.2: retail_dir = "LONG"
            elif retail_ls_ratio < 0.8: retail_dir = "SHORT"
            
        smart_dir = "NEUTRAL"
        if whale_net_flow_usd:
            if whale_net_flow_usd > 1000000: smart_dir = "LONG"
            elif whale_net_flow_usd < -1000000: smart_dir = "SHORT"
            
        div_type = "NO_SIGNAL"
        action = "HOLD"
        strength = 0.0
        
        if smart_dir == "LONG" and retail_dir == "SHORT":
            div_type = "BULLISH_DIVERGENCE"
            action = "STRONG_BUY"
            strength = 0.9
        elif smart_dir == "SHORT" and retail_dir == "LONG":
            div_type = "BEARISH_DIVERGENCE"
            action = "STRONG_SELL"
            strength = 0.9
            
        return DivergenceSignal(
            datetime.now(), div_type, smart_dir, retail_dir, strength, action, components
        )
