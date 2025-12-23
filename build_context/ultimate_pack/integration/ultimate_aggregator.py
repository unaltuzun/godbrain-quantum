import asyncio
from dataclasses import dataclass, field
from typing import Dict, List, Optional, Any
from datetime import datetime

# Import modules (relative for package structure)
try:
    from ..regime.regime_detector import RegimeDetector
    from ..orderflow.vpin_analyzer import VPINAnalyzer
    from ..smartmoney.divergence_detector import SmartMoneyDivergence
    from ..sizing.adaptive_kelly import AdaptiveKelly
    from ..protection.mev_shield import MEVShield
except ImportError:
    # Fallback if imports fail during setup
    pass

@dataclass
class UltimateDecision:
    """
    Standardized Decision Object v2.0
    Supports full rich data from Ultimate Connector.
    """
    timestamp: datetime
    symbol: str
    action: str              # BUY, SELL, HOLD, STRONG_BUY...
    conviction: float        # 0.0 - 1.0
    position_size_usd: float
    regime: str
    reasoning: str = ""
    stop_loss_pct: float = 0.0
    take_profit_pct: float = 0.0
    execution_chunks: int = 1
    execution_delay_ms: int = 0
    signals: Dict = field(default_factory=dict)
    dna_enhancement: Dict = field(default_factory=dict)
    
    # Legacy field support (optional)
    execution_plan: Dict = field(default_factory=dict)

class UltimateAggregator:
    """
    The GODBRAIN ULTIMATE Brain.
    Combines 8 advanced signals into one execution command.
    """
    def __init__(self):
        # Initialize modules safely
        try:
            self.regime = RegimeDetector()
            self.vpin = VPINAnalyzer()
            self.smart = SmartMoneyDivergence()
            self.kelly = AdaptiveKelly()
            self.shield = MEVShield()
        except:
            pass # Modules might be init by Connector
        
    async def get_decision(self, symbol: str, capital: float, market_data: Dict) -> UltimateDecision:
        # Placeholder for direct aggregation logic if needed in future.
        # Currently UltimateConnector handles the logic.
        return UltimateDecision(
            timestamp=datetime.now(),
            symbol=symbol,
            action="HOLD",
            conviction=0.0,
            position_size_usd=0.0,
            regime="INIT",
            reasoning="Aggregator Init"
        )
