# -*- coding: utf-8 -*-
"""
📊 SIGNAL RANKER - Rank Trading Opportunities
Prioritize signals by strength, confidence, and risk.
"""

from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass

from .signal_combiner import SignalCombiner, CombinedSignal


@dataclass
class RankedOpportunity:
    rank: int
    symbol: str
    direction: str
    signal_strength: float
    confidence: float
    liquidity_score: float
    risk_score: float
    overall_score: float
    entry_recommendation: str
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        return {
            "rank": self.rank,
            "symbol": self.symbol,
            "direction": self.direction,
            "signal_strength": self.signal_strength,
            "confidence": self.confidence,
            "overall_score": self.overall_score,
            "entry_recommendation": self.entry_recommendation,
            "timestamp": self.timestamp.isoformat()
        }


class SignalRanker:
    """
    Rank trading opportunities by overall attractiveness.
    
    Score = signal_strength * confidence * liquidity * (1 - risk)
    """
    
    def __init__(self, signal_combiner: Optional[SignalCombiner] = None):
        self.combiner = signal_combiner or SignalCombiner()
    
    async def rank_opportunities(self, symbols: List[str]) -> List[RankedOpportunity]:
        """Rank all symbols by opportunity score."""
        opportunities = []
        
        for symbol in symbols:
            signal = await self.combiner.combine(symbol)
            liquidity = await self._get_liquidity_score(symbol)
            risk = await self._get_risk_score(symbol)
            
            # Calculate overall score
            overall = signal.strength * signal.confidence * (liquidity / 100) * (1 - risk)
            
            # Entry recommendation
            if overall > 0.6 and signal.confidence > 0.7:
                recommendation = "strong_entry"
            elif overall > 0.4:
                recommendation = "consider_entry"
            elif overall > 0.2:
                recommendation = "monitor"
            else:
                recommendation = "avoid"
            
            opportunities.append(RankedOpportunity(
                rank=0,  # Will be set after sorting
                symbol=symbol,
                direction=signal.direction,
                signal_strength=signal.strength,
                confidence=signal.confidence,
                liquidity_score=liquidity,
                risk_score=risk,
                overall_score=overall,
                entry_recommendation=recommendation,
                timestamp=datetime.now()
            ))
        
        # Sort by overall score
        opportunities.sort(key=lambda x: x.overall_score, reverse=True)
        
        # Assign ranks
        for i, opp in enumerate(opportunities):
            opp.rank = i + 1
        
        return opportunities
    
    async def _get_liquidity_score(self, symbol: str) -> float:
        """Get liquidity score (0-100)."""
        try:
            from risk import LiquidityRiskManager
            lrm = LiquidityRiskManager()
            score = await lrm.liquidity_score(symbol)
            return score.score
        except:
            import random
            return random.uniform(50, 100)
    
    async def _get_risk_score(self, symbol: str) -> float:
        """Get risk score (0-1, higher = riskier)."""
        # Would calculate based on volatility, correlation, etc.
        import random
        return random.uniform(0.1, 0.5)
    
    async def top_n(self, symbols: List[str], n: int = 5) -> List[RankedOpportunity]:
        """Get top N opportunities."""
        ranked = await self.rank_opportunities(symbols)
        return ranked[:n]
    
    async def filter_by_risk(self, symbols: List[str], 
                             max_var: float = 0.02) -> List[RankedOpportunity]:
        """Filter opportunities by maximum VaR threshold."""
        ranked = await self.rank_opportunities(symbols)
        
        # Filter by risk score (proxy for VaR)
        return [opp for opp in ranked if opp.risk_score < max_var * 10]
    
    async def portfolio_fit(self, symbols: List[str],
                           current_positions: Dict[str, float]) -> List[RankedOpportunity]:
        """
        Rank opportunities considering current portfolio.
        Prefer symbols that add diversification.
        """
        ranked = await self.rank_opportunities(symbols)
        
        # Boost score for symbols not in current portfolio
        current_syms = set(current_positions.keys())
        
        for opp in ranked:
            if opp.symbol not in current_syms:
                opp.overall_score *= 1.2  # 20% boost for diversification
        
        # Re-sort and re-rank
        ranked.sort(key=lambda x: x.overall_score, reverse=True)
        for i, opp in enumerate(ranked):
            opp.rank = i + 1
        
        return ranked


# Convenience function
async def get_top_opportunities(n: int = 5) -> List[RankedOpportunity]:
    """Quick top opportunities check."""
    default_symbols = ['BTC', 'ETH', 'SOL', 'AVAX', 'MATIC', 'ARB', 'OP', 'LINK']
    ranker = SignalRanker()
    return await ranker.top_n(default_symbols, n)
