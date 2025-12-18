# -*- coding: utf-8 -*-
"""
📊 FLOW ANALYZER - Exchange Inflow/Outflow Analysis
Track exchange flows as leading indicators.
"""

import os
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass

GLASSNODE_API_KEY = os.getenv('GLASSNODE_API_KEY', '')


@dataclass
class ExchangeFlow:
    exchange: str
    symbol: str
    inflow: float
    outflow: float
    net_flow: float
    timestamp: datetime
    
    @property
    def direction(self) -> str:
        if self.net_flow > 0:
            return "bearish"  # More inflow = selling pressure
        elif self.net_flow < 0:
            return "bullish"  # More outflow = holding
        return "neutral"


@dataclass
class FlowSignal:
    symbol: str
    net_flow_24h: float
    flow_momentum: float
    direction: str
    confidence: float
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "net_flow_24h": self.net_flow_24h,
            "flow_momentum": self.flow_momentum,
            "direction": self.direction,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat()
        }


class FlowAnalyzer:
    """
    Analyze exchange flows as leading indicators.
    
    Logic:
    - Exchange inflow → Selling pressure → Bearish
    - Exchange outflow → Holding → Bullish
    - Stablecoin inflow to exchange → Buying power → Bullish
    """
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self._cache: Dict[str, any] = {}
        self._cache_ttl = 300  # 5 minutes
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_exchange_reserves(self, symbol: str) -> Dict[str, float]:
        """Get exchange reserves across major exchanges."""
        # In production, would query Glassnode or similar
        if not GLASSNODE_API_KEY:
            return self._mock_reserves(symbol)
        
        return self._mock_reserves(symbol)
    
    def _mock_reserves(self, symbol: str) -> Dict[str, float]:
        """Mock exchange reserves."""
        import random
        base = 1_000_000 if symbol == 'BTC' else 10_000_000
        
        return {
            "binance": base * random.uniform(0.3, 0.5),
            "coinbase": base * random.uniform(0.1, 0.2),
            "kraken": base * random.uniform(0.05, 0.1),
            "okx": base * random.uniform(0.05, 0.15),
            "bybit": base * random.uniform(0.03, 0.08),
            "total": base * random.uniform(0.6, 1.0)
        }
    
    async def net_flow(self, symbol: str, hours: int = 24) -> float:
        """
        Get net exchange flow.
        Positive = net inflow (bearish)
        Negative = net outflow (bullish)
        """
        flows = await self._get_historical_flows(symbol, hours)
        
        total_inflow = sum(f.inflow for f in flows)
        total_outflow = sum(f.outflow for f in flows)
        
        return total_inflow - total_outflow
    
    async def _get_historical_flows(self, symbol: str, hours: int) -> List[ExchangeFlow]:
        """Get historical flow data."""
        # Mock implementation
        import random
        flows = []
        
        for h in range(hours):
            inflow = random.uniform(100, 5000) * (1000 if symbol == 'BTC' else 1)
            outflow = random.uniform(100, 5000) * (1000 if symbol == 'BTC' else 1)
            
            flows.append(ExchangeFlow(
                exchange="all",
                symbol=symbol,
                inflow=inflow,
                outflow=outflow,
                net_flow=inflow - outflow,
                timestamp=datetime.now() - timedelta(hours=hours - h)
            ))
        
        return flows
    
    async def flow_momentum(self, symbol: str) -> float:
        """
        Rate of change in net flow.
        Positive = accelerating inflow (more bearish)
        Negative = accelerating outflow (more bullish)
        """
        flows_24h = await self._get_historical_flows(symbol, 24)
        flows_48h = await self._get_historical_flows(symbol, 48)
        
        net_24h = sum(f.net_flow for f in flows_24h)
        net_prev_24h = sum(f.net_flow for f in flows_48h[24:]) if len(flows_48h) > 24 else 0
        
        if net_prev_24h == 0:
            return 0
        
        momentum = (net_24h - net_prev_24h) / abs(net_prev_24h + 1)
        return momentum
    
    async def stablecoin_flow(self) -> Dict:
        """
        Track stablecoin flows.
        Stablecoin inflow to exchange = buying power = bullish
        """
        usdt_flow = await self.net_flow('USDT', hours=24)
        usdc_flow = await self.net_flow('USDC', hours=24)
        
        total_stable_flow = usdt_flow + usdc_flow
        
        return {
            "usdt_net_flow": usdt_flow,
            "usdc_net_flow": usdc_flow,
            "total_stable_flow": total_stable_flow,
            "direction": "bullish" if total_stable_flow > 0 else "bearish",
            "timestamp": datetime.now().isoformat()
        }
    
    async def get_signal(self, symbol: str) -> FlowSignal:
        """Generate flow-based signal."""
        net = await self.net_flow(symbol, hours=24)
        momentum = await self.flow_momentum(symbol)
        
        # Determine direction
        if net < 0 and momentum < 0:
            direction = "bullish"
            confidence = min(1.0, abs(net) / 1_000_000 * abs(momentum))
        elif net > 0 and momentum > 0:
            direction = "bearish"
            confidence = min(1.0, abs(net) / 1_000_000 * abs(momentum))
        else:
            direction = "neutral"
            confidence = 0.3
        
        return FlowSignal(
            symbol=symbol,
            net_flow_24h=net,
            flow_momentum=momentum,
            direction=direction,
            confidence=confidence,
            timestamp=datetime.now()
        )


# Convenience function
async def get_flow_signal(symbol: str) -> FlowSignal:
    """Quick flow signal check."""
    analyzer = FlowAnalyzer()
    try:
        return await analyzer.get_signal(symbol)
    finally:
        await analyzer.close()
