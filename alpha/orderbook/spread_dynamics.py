# -*- coding: utf-8 -*-
"""
📈 SPREAD DYNAMICS - Market Stress Indicator
Spread analysis for market conditions.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class SpreadData:
    symbol: str
    bid: float
    ask: float
    spread: float
    spread_bps: float  # basis points
    timestamp: datetime


class SpreadAnalyzer:
    """
    Analyze bid-ask spread dynamics.
    Spread = market stress indicator.
    """
    
    def __init__(self, exchange_manager=None):
        self.exchange_manager = exchange_manager
        self._history: Dict[str, List[SpreadData]] = {}
    
    async def current_spread(self, symbol: str) -> float:
        """Get current spread in basis points."""
        ticker = await self._fetch_ticker(symbol)
        bid = ticker.get('bid', 0)
        ask = ticker.get('ask', 0)
        
        if bid == 0:
            return 0
        
        spread_bps = (ask - bid) / bid * 10000
        
        # Store history
        if symbol not in self._history:
            self._history[symbol] = []
        
        self._history[symbol].append(SpreadData(
            symbol=symbol,
            bid=bid,
            ask=ask,
            spread=ask - bid,
            spread_bps=spread_bps,
            timestamp=datetime.now()
        ))
        
        # Keep 24h history
        cutoff = datetime.now() - timedelta(hours=24)
        self._history[symbol] = [h for h in self._history[symbol] if h.timestamp > cutoff]
        
        return spread_bps
    
    async def _fetch_ticker(self, symbol: str) -> Dict:
        """Fetch ticker from exchange."""
        if self.exchange_manager:
            try:
                return await self.exchange_manager.get_ticker(symbol)
            except:
                pass
        return self._mock_ticker(symbol)
    
    def _mock_ticker(self, symbol: str) -> Dict:
        """Generate mock ticker."""
        import random
        base_price = 100000 if 'BTC' in symbol.upper() else 3500
        spread = base_price * random.uniform(0.0001, 0.001)
        
        return {
            "bid": base_price - spread/2,
            "ask": base_price + spread/2,
            "last": base_price
        }
    
    async def spread_percentile(self, symbol: str, days: int = 30) -> float:
        """Get current spread as percentile of historical range."""
        current = await self.current_spread(symbol)
        history = self._history.get(symbol, [])
        
        if len(history) < 10:
            return 50.0  # Default to median
        
        spreads = sorted([h.spread_bps for h in history])
        
        # Find percentile
        count_below = sum(1 for s in spreads if s <= current)
        percentile = count_below / len(spreads) * 100
        
        return percentile
    
    async def spread_widening_alert(self, symbol: str, threshold_pct: float = 200) -> Optional[Dict]:
        """Alert if spread widened significantly."""
        history = self._history.get(symbol, [])
        
        if len(history) < 10:
            return None
        
        current = await self.current_spread(symbol)
        avg_spread = sum(h.spread_bps for h in history) / len(history)
        
        if current > avg_spread * (threshold_pct / 100):
            return {
                "symbol": symbol,
                "alert": "spread_widening",
                "current_spread_bps": current,
                "average_spread_bps": avg_spread,
                "widening_pct": current / avg_spread * 100,
                "recommendation": "reduce_urgency",
                "timestamp": datetime.now().isoformat()
            }
        
        return None
    
    async def market_stress_index(self) -> float:
        """Calculate overall market stress (0-100)."""
        symbols = ['BTC', 'ETH', 'SOL']
        stress_scores = []
        
        for sym in symbols:
            percentile = await self.spread_percentile(sym)
            stress_scores.append(percentile)
        
        return sum(stress_scores) / len(stress_scores) if stress_scores else 50
    
    async def optimal_entry_timing(self, symbol: str) -> Dict:
        """Find optimal entry based on spread."""
        current = await self.current_spread(symbol)
        percentile = await self.spread_percentile(symbol)
        
        if percentile < 25:
            timing = "excellent"
            recommendation = "enter_now"
        elif percentile < 50:
            timing = "good"
            recommendation = "enter_ok"
        elif percentile < 75:
            timing = "fair"
            recommendation = "consider_waiting"
        else:
            timing = "poor"
            recommendation = "wait_for_tighter"
        
        return {
            "symbol": symbol,
            "current_spread_bps": current,
            "spread_percentile": percentile,
            "timing": timing,
            "recommendation": recommendation,
            "timestamp": datetime.now().isoformat()
        }
