import asyncio
import pandas as pd
from typing import Dict, Any

# Import Aggregator
try:
    from .integration.ultimate_aggregator import UltimateAggregator, UltimateDecision
except ImportError:
    # Standalone run fix
    import sys
    from pathlib import Path
    sys.path.append(str(Path(__file__).parent.parent))
    from ultimate_pack.integration.ultimate_aggregator import UltimateAggregator, UltimateDecision

class UltimateConnector:
    """
    Bridge between agg.py and the 8-module Ultimate Alpha System.
    """
    def __init__(self):
        self.aggregator = UltimateAggregator()
        self.warmup_done = False
        
    async def get_signal(self, symbol: str, capital: float, market_data: Any) -> UltimateDecision:
        # Data Adapter
        data_payload = {}
        
        # OHLCV Handling
        if isinstance(market_data, pd.DataFrame):
            data_payload['ohlcv'] = market_data
        elif isinstance(market_data, list):
            try:
                df = pd.DataFrame(market_data, columns=['timestamp','open','high','low','close','vol'])
                data_payload['ohlcv'] = df
            except:
                pass
                
        # Safety Check
        if 'ohlcv' not in data_payload or data_payload['ohlcv'].empty:
            from datetime import datetime
            return UltimateDecision(
                timestamp=datetime.now(), symbol=symbol, action="HOLD",
                conviction=0.0, position_size_usd=0.0, regime="WAITING_DATA",
                execution_plan={}, 
                risk_reward_ratio=0.0, expected_value=0.0, max_loss_usd=0.0,
                regime_confidence=0.0, signals_summary={}, signals_agreement=0.0,
                execution_method="MARKET", order_chunks=1, mev_protection_active=False,
                reasoning="Insufficient Data", warnings=[], dna_enhancement={}
            )

        # Get Decision from the 8-Module Brain
        decision = await self.aggregator.get_decision(symbol, capital, data_payload)
        return decision
