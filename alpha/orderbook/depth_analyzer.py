# -*- coding: utf-8 -*-
"""
📊 DEPTH ANALYZER - Liquidity Analysis
Analyze order book depth for slippage prediction and support/resistance.
"""

from datetime import datetime
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class DepthProfile:
    symbol: str
    bid_depth: List[Tuple[float, float]]  # [(price, cumulative_volume), ...]
    ask_depth: List[Tuple[float, float]]
    total_bid_volume: float
    total_ask_volume: float
    liquidity_score: float
    timestamp: datetime


@dataclass
class SupportResistance:
    support_levels: List[float]
    resistance_levels: List[float]
    strongest_support: float
    strongest_resistance: float


class DepthAnalyzer:
    """
    Analyze order book depth for:
    - Liquidity scoring
    - Slippage estimation
    - Support/resistance detection
    """
    
    def __init__(self, exchange_manager=None):
        self.exchange_manager = exchange_manager
    
    async def get_depth_profile(self, symbol: str, levels: int = 50) -> DepthProfile:
        """Get complete depth profile."""
        orderbook = await self._fetch_orderbook(symbol, levels)
        
        # Calculate cumulative depth
        bid_depth = []
        cumulative = 0
        for price, vol in orderbook['bids']:
            cumulative += vol
            bid_depth.append((price, cumulative))
        
        ask_depth = []
        cumulative = 0
        for price, vol in orderbook['asks']:
            cumulative += vol
            ask_depth.append((price, cumulative))
        
        total_bid = sum(v for _, v in orderbook['bids'])
        total_ask = sum(v for _, v in orderbook['asks'])
        
        # Liquidity score (0-100)
        liquidity_score = min(100, (total_bid + total_ask) / 100)
        
        return DepthProfile(
            symbol=symbol,
            bid_depth=bid_depth,
            ask_depth=ask_depth,
            total_bid_volume=total_bid,
            total_ask_volume=total_ask,
            liquidity_score=liquidity_score,
            timestamp=datetime.now()
        )
    
    async def _fetch_orderbook(self, symbol: str, depth: int) -> Dict:
        """Fetch orderbook from exchange."""
        if self.exchange_manager:
            try:
                return await self.exchange_manager.get_orderbook(symbol, depth)
            except:
                pass
        return self._mock_orderbook(symbol, depth)
    
    def _mock_orderbook(self, symbol: str, depth: int) -> Dict:
        """Generate mock orderbook."""
        import random
        base_price = 100000 if 'BTC' in symbol.upper() else 3500
        
        bids = []
        asks = []
        
        for i in range(depth):
            bid_price = base_price * (1 - 0.0001 * (i + 1))
            ask_price = base_price * (1 + 0.0001 * (i + 1))
            bid_vol = random.uniform(0.5, 20)
            ask_vol = random.uniform(0.5, 20)
            bids.append([bid_price, bid_vol])
            asks.append([ask_price, ask_vol])
        
        return {"bids": bids, "asks": asks}
    
    async def liquidity_score(self, symbol: str) -> float:
        """Get liquidity score (0-100)."""
        profile = await self.get_depth_profile(symbol)
        return profile.liquidity_score
    
    async def slippage_estimate(self, symbol: str, size_usd: float) -> float:
        """Estimate slippage for a given order size."""
        profile = await self.get_depth_profile(symbol, levels=100)
        
        base_price = profile.ask_depth[0][0] if profile.ask_depth else 100000
        
        # Find how deep we need to go
        cumulative_usd = 0
        slippage = 0
        
        for price, cum_vol in profile.ask_depth:
            level_usd = cum_vol * price
            if cumulative_usd + level_usd >= size_usd:
                # This level fills the order
                slippage = (price - base_price) / base_price
                break
            cumulative_usd += level_usd
        
        return abs(slippage)
    
    async def support_resistance_from_depth(self, symbol: str) -> SupportResistance:
        """Detect support/resistance from order book walls."""
        profile = await self.get_depth_profile(symbol, levels=100)
        
        # Find bid walls (support)
        supports = []
        prev_vol = 0
        for price, cum_vol in profile.bid_depth:
            vol_jump = cum_vol - prev_vol
            if vol_jump > profile.total_bid_volume * 0.1:  # >10% of total
                supports.append(price)
            prev_vol = cum_vol
        
        # Find ask walls (resistance)
        resistances = []
        prev_vol = 0
        for price, cum_vol in profile.ask_depth:
            vol_jump = cum_vol - prev_vol
            if vol_jump > profile.total_ask_volume * 0.1:
                resistances.append(price)
            prev_vol = cum_vol
        
        return SupportResistance(
            support_levels=supports[:5],
            resistance_levels=resistances[:5],
            strongest_support=supports[0] if supports else profile.bid_depth[0][0],
            strongest_resistance=resistances[0] if resistances else profile.ask_depth[0][0]
        )
    
    async def thin_market_alert(self, symbol: str, threshold: float = 30) -> Optional[Dict]:
        """Alert if market is too thin."""
        score = await self.liquidity_score(symbol)
        
        if score < threshold:
            return {
                "symbol": symbol,
                "alert": "thin_market",
                "liquidity_score": score,
                "recommendation": "reduce_position_size",
                "timestamp": datetime.now().isoformat()
            }
        return None
