# -*- coding: utf-8 -*-
"""
🎯 SENTIMENT AGGREGATOR - Combine All Sentiment Sources
"""

import asyncio
from datetime import datetime
from typing import Dict, Optional
from dataclasses import dataclass


@dataclass
class CombinedSentiment:
    symbol: str
    twitter_score: float
    reddit_score: float
    news_score: float
    fear_greed: float
    final_score: float
    confidence: float
    sources_agreeing: int
    divergence_flag: bool
    timestamp: datetime
    
    @property
    def direction(self) -> str:
        if self.final_score > 0.2:
            return "bullish"
        elif self.final_score < -0.2:
            return "bearish"
        return "neutral"
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "twitter_score": self.twitter_score,
            "reddit_score": self.reddit_score,
            "news_score": self.news_score,
            "fear_greed": self.fear_greed,
            "final_score": self.final_score,
            "confidence": self.confidence,
            "direction": self.direction,
            "sources_agreeing": self.sources_agreeing,
            "divergence_flag": self.divergence_flag,
            "timestamp": self.timestamp.isoformat()
        }


class SentimentAggregator:
    """
    Combine all sentiment sources into a unified signal.
    
    Weights:
    - Twitter: 0.30
    - Reddit: 0.20
    - News: 0.30
    - Fear & Greed: 0.20
    """
    
    def __init__(self):
        self.weights = {
            "twitter": 0.30,
            "reddit": 0.20,
            "news": 0.30,
            "fear_greed": 0.20
        }
    
    async def get_combined_sentiment(self, symbol: str) -> CombinedSentiment:
        """Get combined sentiment from all sources."""
        # Get individual scores (mock for now)
        twitter_score = await self._get_twitter_sentiment(symbol)
        reddit_score = await self._get_reddit_sentiment(symbol)
        news_score = await self._get_news_sentiment(symbol)
        fear_greed = await self._get_fear_greed()
        
        # Calculate weighted final score
        final_score = (
            twitter_score * self.weights["twitter"] +
            reddit_score * self.weights["reddit"] +
            news_score * self.weights["news"] +
            fear_greed * self.weights["fear_greed"]
        )
        
        # Check how many sources agree
        scores = [twitter_score, reddit_score, news_score, fear_greed]
        positive = sum(1 for s in scores if s > 0.1)
        negative = sum(1 for s in scores if s < -0.1)
        
        sources_agreeing = max(positive, negative)
        divergence_flag = positive >= 2 and negative >= 2
        
        # Confidence based on agreement
        confidence = sources_agreeing / 4 * (1 - 0.3 * divergence_flag)
        
        return CombinedSentiment(
            symbol=symbol,
            twitter_score=twitter_score,
            reddit_score=reddit_score,
            news_score=news_score,
            fear_greed=fear_greed,
            final_score=final_score,
            confidence=confidence,
            sources_agreeing=sources_agreeing,
            divergence_flag=divergence_flag,
            timestamp=datetime.now()
        )
    
    async def _get_twitter_sentiment(self, symbol: str) -> float:
        """Get Twitter sentiment (-1 to 1)."""
        import random
        # Mock: In production, use Twitter API + LLM
        return random.uniform(-0.5, 0.5)
    
    async def _get_reddit_sentiment(self, symbol: str) -> float:
        """Get Reddit sentiment (-1 to 1)."""
        import random
        # Mock: In production, use Reddit API + NLP
        return random.uniform(-0.4, 0.6)
    
    async def _get_news_sentiment(self, symbol: str) -> float:
        """Get news sentiment (-1 to 1)."""
        import random
        # Mock: In production, use News API + LLM
        return random.uniform(-0.3, 0.3)
    
    async def _get_fear_greed(self) -> float:
        """Get Fear & Greed normalized (-1 to 1)."""
        try:
            from .fear_greed import FearGreedIndex
            fg = FearGreedIndex()
            data = await fg.get_current()
            await fg.close()
            return data.normalized
        except:
            import random
            return random.uniform(-0.5, 0.5)
    
    async def sentiment_divergence(self, symbol: str) -> Dict:
        """Check when sources disagree."""
        sentiment = await self.get_combined_sentiment(symbol)
        
        return {
            "symbol": symbol,
            "divergence": sentiment.divergence_flag,
            "sources_agreeing": sentiment.sources_agreeing,
            "twitter_vs_news": abs(sentiment.twitter_score - sentiment.news_score),
            "recommendation": "wait" if sentiment.divergence_flag else "proceed"
        }
    
    async def extreme_sentiment_alert(self, symbol: str, threshold: float = 0.7) -> Optional[Dict]:
        """Alert when sentiment is extreme."""
        sentiment = await self.get_combined_sentiment(symbol)
        
        if abs(sentiment.final_score) >= threshold:
            return {
                "symbol": symbol,
                "alert": "extreme_sentiment",
                "direction": sentiment.direction,
                "score": sentiment.final_score,
                "confidence": sentiment.confidence,
                "recommendation": "contrarian_opportunity" if sentiment.confidence > 0.7 else "monitor"
            }
        
        return None


# Convenience function
async def get_sentiment(symbol: str) -> CombinedSentiment:
    """Quick sentiment check."""
    agg = SentimentAggregator()
    return await agg.get_combined_sentiment(symbol)
