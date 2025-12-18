# -*- coding: utf-8 -*-
"""
💧 LIQUIDITY RISK MANAGER - Liquidity Scoring & Risk
Position sizing based on market liquidity.
"""

from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class LiquidityScore:
    symbol: str
    score: float  # 0-100
    tier: str  # 'high', 'medium', 'low', 'illiquid'
    daily_volume_usd: float
    bid_ask_spread_bps: float
    depth_score: float
    timestamp: datetime


class LiquidityRiskManager:
    """
    Liquidity risk management.
    
    Features:
    - Liquidity scoring
    - Time to liquidate estimation
    - Liquidation cost calculation
    - Position size recommendations
    """
    
    def __init__(self, exchange_manager=None):
        self.exchange_manager = exchange_manager
    
    async def liquidity_score(self, symbol: str) -> LiquidityScore:
        """Calculate liquidity score (0-100)."""
        data = await self._get_market_data(symbol)
        
        # Components
        volume_score = min(100, data['daily_volume_usd'] / 1_000_000_000 * 100)
        spread_score = max(0, 100 - data['spread_bps'] * 10)
        depth_score = min(100, data['depth_usd'] / 10_000_000 * 100)
        
        # Weighted average
        score = (
            volume_score * 0.4 +
            spread_score * 0.3 +
            depth_score * 0.3
        )
        
        # Tier
        if score >= 80:
            tier = 'high'
        elif score >= 50:
            tier = 'medium'
        elif score >= 20:
            tier = 'low'
        else:
            tier = 'illiquid'
        
        return LiquidityScore(
            symbol=symbol,
            score=score,
            tier=tier,
            daily_volume_usd=data['daily_volume_usd'],
            bid_ask_spread_bps=data['spread_bps'],
            depth_score=depth_score,
            timestamp=datetime.now()
        )
    
    async def _get_market_data(self, symbol: str) -> Dict:
        """Get market liquidity data."""
        if self.exchange_manager:
            try:
                ticker = await self.exchange_manager.get_ticker(symbol)
                depth = await self.exchange_manager.get_depth(symbol)
                return {
                    'daily_volume_usd': ticker.get('volume_usd', 0),
                    'spread_bps': (ticker.get('ask', 0) - ticker.get('bid', 0)) / ticker.get('bid', 1) * 10000,
                    'depth_usd': depth.get('total_depth_usd', 0)
                }
            except:
                pass
        
        # Mock data
        import random
        return {
            'daily_volume_usd': random.uniform(100_000_000, 10_000_000_000),
            'spread_bps': random.uniform(1, 20),
            'depth_usd': random.uniform(1_000_000, 50_000_000)
        }
    
    async def time_to_liquidate(self, symbol: str, 
                                position_size_usd: float) -> timedelta:
        """
        Estimate time to liquidate a position.
        
        Assumes 10% participation rate in daily volume.
        """
        data = await self._get_market_data(symbol)
        daily_volume = data['daily_volume_usd']
        
        participation_rate = 0.1  # 10% of volume
        daily_capacity = daily_volume * participation_rate
        
        if daily_capacity <= 0:
            return timedelta(days=999)
        
        days_to_liquidate = position_size_usd / daily_capacity
        return timedelta(days=days_to_liquidate)
    
    async def liquidation_cost(self, symbol: str, size_usd: float,
                               urgency: str = 'normal') -> float:
        """
        Estimate cost of liquidation.
        
        Args:
            urgency: 'low', 'normal', 'high', 'emergency'
        """
        score = await self.liquidity_score(symbol)
        
        # Base slippage based on liquidity
        base_slippage = (100 - score.score) / 1000  # 0-10%
        
        # Urgency multiplier
        urgency_mult = {
            'low': 0.5,
            'normal': 1.0,
            'high': 2.0,
            'emergency': 5.0
        }.get(urgency, 1.0)
        
        # Size impact
        data = await self._get_market_data(symbol)
        size_pct = size_usd / data['daily_volume_usd']
        size_impact = size_pct * 0.5  # 50% of position as % of volume
        
        total_slippage = base_slippage + size_impact * urgency_mult
        cost = size_usd * total_slippage
        
        return cost
    
    async def illiquid_position_alert(self, positions: Dict[str, float],
                                      threshold: float = 0.1) -> List[Dict]:
        """
        Alert if any position is too large relative to daily volume.
        
        Args:
            threshold: Max position as fraction of daily volume (default 10%)
        """
        alerts = []
        
        for symbol, size_usd in positions.items():
            data = await self._get_market_data(symbol)
            daily_volume = data['daily_volume_usd']
            
            if daily_volume > 0:
                pct_of_volume = size_usd / daily_volume
                
                if pct_of_volume > threshold:
                    alerts.append({
                        "symbol": symbol,
                        "alert": "illiquid_position",
                        "position_size_usd": size_usd,
                        "daily_volume_usd": daily_volume,
                        "pct_of_volume": pct_of_volume,
                        "threshold": threshold,
                        "recommendation": f"Reduce position to <{threshold*100}% of daily volume"
                    })
        
        return alerts
    
    async def liquidity_adjusted_var(self, positions: Dict[str, Dict],
                                      returns_data: Dict[str, list],
                                      base_var: float) -> float:
        """
        Adjust VaR for liquidity risk.
        
        Illiquid positions get VaR penalty.
        """
        import numpy as np
        
        adjustment = 0
        
        for symbol, pos in positions.items():
            score = await self.liquidity_score(symbol)
            
            # Penalty increases as liquidity decreases
            liquidity_penalty = (100 - score.score) / 100  # 0-1
            position_var_contribution = pos.get('weight', 0) * base_var
            
            adjustment += position_var_contribution * liquidity_penalty * 0.5  # 50% max adjustment
        
        return base_var + adjustment
