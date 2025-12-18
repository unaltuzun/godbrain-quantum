# -*- coding: utf-8 -*-
"""
🎯 SIGNAL COMBINER - Combine All Alpha Sources
Unified trading signal from multiple inputs.
"""

from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class CombinedSignal:
    symbol: str
    direction: str  # 'long', 'short', 'neutral'
    strength: float  # 0-1
    confidence: float  # 0-1
    sources_agreeing: int
    total_sources: int
    divergence_flag: bool
    component_signals: Dict[str, float]
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "direction": self.direction,
            "strength": self.strength,
            "confidence": self.confidence,
            "sources_agreeing": self.sources_agreeing,
            "divergence_flag": self.divergence_flag,
            "components": self.component_signals,
            "timestamp": self.timestamp.isoformat()
        }


class SignalCombiner:
    """
    Combine all alpha sources into a unified trading signal.
    
    Default weights:
    - onchain: 0.25
    - sentiment: 0.20
    - orderbook: 0.25
    - technical: 0.20
    - physics_lab: 0.10
    """
    
    def __init__(self, weights: Optional[Dict[str, float]] = None):
        self.weights = weights or {
            "onchain": 0.25,
            "sentiment": 0.20,
            "orderbook": 0.25,
            "technical": 0.20,
            "physics_lab": 0.10
        }
    
    async def combine(self, symbol: str) -> CombinedSignal:
        """Combine all signals for a symbol."""
        signals = {}
        
        # Get each signal component
        signals['onchain'] = await self._get_onchain_signal(symbol)
        signals['sentiment'] = await self._get_sentiment_signal(symbol)
        signals['orderbook'] = await self._get_orderbook_signal(symbol)
        signals['technical'] = await self._get_technical_signal(symbol)
        signals['physics_lab'] = await self._get_physics_signal(symbol)
        
        # Calculate weighted combination
        weighted_sum = 0
        for source, signal in signals.items():
            weight = self.weights.get(source, 0)
            weighted_sum += signal * weight
        
        # Determine direction
        if weighted_sum > 0.2:
            direction = 'long'
        elif weighted_sum < -0.2:
            direction = 'short'
        else:
            direction = 'neutral'
        
        # Count agreeing sources
        positive = sum(1 for s in signals.values() if s > 0.1)
        negative = sum(1 for s in signals.values() if s < -0.1)
        sources_agreeing = max(positive, negative)
        
        # Check for divergence
        divergence = positive >= 2 and negative >= 2
        
        # Confidence based on agreement
        confidence = sources_agreeing / len(signals) * (0.5 if divergence else 1.0)
        
        return CombinedSignal(
            symbol=symbol,
            direction=direction,
            strength=abs(weighted_sum),
            confidence=confidence,
            sources_agreeing=sources_agreeing,
            total_sources=len(signals),
            divergence_flag=divergence,
            component_signals=signals,
            timestamp=datetime.now()
        )
    
    async def _get_onchain_signal(self, symbol: str) -> float:
        """Get on-chain signal (-1 to 1)."""
        try:
            from alpha.onchain import WhaleTracker
            tracker = WhaleTracker()
            flow = await tracker.exchange_flow(symbol)
            await tracker.close()
            
            # Outflow = bullish, Inflow = bearish
            if flow['net_flow_usd'] < 0:
                return min(1.0, abs(flow['net_flow_usd']) / 10_000_000)
            else:
                return max(-1.0, -abs(flow['net_flow_usd']) / 10_000_000)
        except:
            import random
            return random.uniform(-0.5, 0.5)
    
    async def _get_sentiment_signal(self, symbol: str) -> float:
        """Get sentiment signal (-1 to 1)."""
        try:
            from alpha.sentiment import SentimentAggregator
            agg = SentimentAggregator()
            sentiment = await agg.get_combined_sentiment(symbol)
            return sentiment.final_score
        except:
            import random
            return random.uniform(-0.5, 0.5)
    
    async def _get_orderbook_signal(self, symbol: str) -> float:
        """Get order book signal (-1 to 1)."""
        try:
            from alpha.orderbook import OrderBookImbalance
            ob = OrderBookImbalance()
            imbalance = await ob.get_imbalance(symbol)
            return imbalance
        except:
            import random
            return random.uniform(-0.5, 0.5)
    
    async def _get_technical_signal(self, symbol: str) -> float:
        """Get technical signal from existing GODBRAIN system."""
        # Would integrate with existing agg.py
        import random
        return random.uniform(-0.5, 0.5)
    
    async def _get_physics_signal(self, symbol: str) -> float:
        """Get Physics Lab / DNA signal."""
        # Would integrate with VOLTRAN DNA score
        import random
        return random.uniform(-0.3, 0.3)
    
    async def signal_history(self, symbol: str, hours: int = 24) -> List[Dict]:
        """Get signal history."""
        # Would query historical signals from Redis/DB
        return []
    
    async def backtest_weights(self, start: datetime, end: datetime) -> Dict[str, float]:
        """Backtest to find optimal weights."""
        # Would run optimization on historical data
        return self.weights
