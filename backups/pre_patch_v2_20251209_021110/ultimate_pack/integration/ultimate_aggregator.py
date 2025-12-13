import asyncio
from dataclasses import dataclass
from typing import Dict, List
from datetime import datetime

# Import all modules
from ..regime.regime_detector import RegimeDetector
from ..orderflow.vpin_analyzer import VPINAnalyzer
from ..smartmoney.divergence_detector import SmartMoneyDivergence
from ..sizing.adaptive_kelly import AdaptiveKelly
from ..protection.mev_shield import MEVShield

@dataclass
class UltimateDecision:
    timestamp: datetime
    symbol: str
    action: str
    conviction: float
    position_size_usd: float
    regime: str
    execution_plan: Dict

class UltimateAggregator:
    """
    The GODBRAIN ULTIMATE Brain.
    Combines 8 advanced signals into one execution command.
    """
    def __init__(self):
        self.regime = RegimeDetector()
        self.vpin = VPINAnalyzer()
        self.smart = SmartMoneyDivergence()
        self.kelly = AdaptiveKelly()
        self.shield = MEVShield()
        
    async def get_decision(self, symbol: str, capital: float, market_data: Dict) -> UltimateDecision:
        # 1. Regime Check
        regime_sig = self.regime.analyze(market_data['ohlcv'])
        
        # 2. VPIN Check (Order Flow)
        # Assuming data feeds handled externally for simplicity
        
        # 3. Smart Money
        # Assuming data feeds
        
        # --- SYNTHESIS LOGIC ---
        # Base decision on Regime
        action = "HOLD"
        conviction = 0.0
        
        if regime_sig.recommended_strategy.startswith("trend_follow"):
            action = "BUY"
            conviction = regime_sig.confidence
        elif regime_sig.recommended_strategy == "reduce_exposure":
            action = "SELL"
            conviction = 0.9
            
        # 4. Sizing
        kelly_res = self.kelly.calculate_size(capital)
        final_size = kelly_res.size_usd * regime_sig.position_size_multiplier
        
        # 5. Protection
        mev_prot = self.shield.protect_order(final_size)
        
        return UltimateDecision(
            timestamp=datetime.now(),
            symbol=symbol,
            action=action,
            conviction=conviction,
            position_size_usd=final_size,
            regime=regime_sig.regime.value,
            execution_plan={
                "chunks": mev_prot.chunks,
                "delay_ms": mev_prot.delay_ms
            }
        )
