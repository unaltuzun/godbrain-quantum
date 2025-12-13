import asyncio
import logging
from typing import Any
import pandas as pd
from datetime import datetime

try:
    from .regime.regime_detector import RegimeDetector
    from .orderflow.vpin_analyzer import VPINAnalyzer
    from .smartmoney.divergence_detector import SmartMoneyDivergence
    from .sizing.adaptive_kelly import AdaptiveKelly
    from .feeds.data_feeds import DataHub
    from .integration.ultimate_aggregator import UltimateDecision
except ImportError:
    from ultimate_pack.regime.regime_detector import RegimeDetector
    from ultimate_pack.orderflow.vpin_analyzer import VPINAnalyzer
    from ultimate_pack.smartmoney.divergence_detector import SmartMoneyDivergence
    from ultimate_pack.sizing.adaptive_kelly import AdaptiveKelly
    from ultimate_pack.feeds.data_feeds import DataHub
    from ultimate_pack.integration.ultimate_aggregator import UltimateDecision

class UltimateConnector:
    def __init__(self):
        self.regime = RegimeDetector()
        self.vpin = VPINAnalyzer()
        self.smart = SmartMoneyDivergence()
        self.kelly = AdaptiveKelly()
        self.data_hub = DataHub()
        self.initialized = False
        
    async def initialize(self):
        await self.data_hub.start_all_feeds()
        self.initialized = True
        
    async def get_signal(self, symbol, capital, market_data) -> UltimateDecision:
        df = pd.DataFrame()
        if isinstance(market_data, pd.DataFrame): df = market_data
        elif isinstance(market_data, list) and len(market_data) > 0:
            df = pd.DataFrame(market_data, columns=['timestamp','open','high','low','close','vol'])
            
        if df.empty:
            return UltimateDecision(
                datetime.now(), symbol, "HOLD", 0.0, 0.0, "NO_DATA", "Waiting for data",
                0, 0, 1, 0, {}, {}
            )
            
        ls_data = self.data_hub.ls_ratio_feed.cache.get("BTCUSDT")
        fg_data = self.data_hub.fear_greed_feed.current
        
        regime_sig = self.regime.analyze(df)
        
        retail_val = ls_data.long_short_ratio if ls_data else None
        div_signal = self.smart.analyze(retail_ls_ratio=retail_val)
        
        action = "HOLD"
        conviction = 0.0
        
        is_trending_up = "TRENDING_UP" in regime_sig.regime.value
        is_trending_down = "TRENDING_DOWN" in regime_sig.regime.value
        
        if is_trending_up:
            action = "BUY"
            conviction = regime_sig.confidence
            if div_signal.divergence_type == "BULLISH_DIVERGENCE":
                action = "STRONG_BUY"
                conviction = min(0.99, conviction + 0.2)
                
        elif is_trending_down:
            action = "SELL"
            conviction = regime_sig.confidence
            if div_signal.divergence_type == "BEARISH_DIVERGENCE":
                action = "STRONG_SELL"
                conviction = min(0.99, conviction + 0.2)
            
        k_res = self.kelly.calculate(capital, regime_multiplier=regime_sig.position_size_multiplier)
        
        reason = f"Regime:{regime_sig.regime.value}"
        if fg_data: reason += f" | F&G:{fg_data.value}"
        if ls_data: reason += f" | L/S:{ls_data.long_short_ratio:.2f}"
        
        return UltimateDecision(
            datetime.now(), symbol, action, conviction, k_res.position_size_usd,
            regime_sig.regime.value, reason,
            0, 0, 1, 0, {}, {}
        )
