# -*- coding: utf-8 -*-
"""
📊 FEAR & GREED INDEX - Market Sentiment Indicator
"""

import os
import aiohttp
from datetime import datetime
from typing import Optional, Dict
from dataclasses import dataclass


@dataclass
class FearGreedData:
    value: int  # 0-100
    classification: str  # 'extreme_fear', 'fear', 'neutral', 'greed', 'extreme_greed'
    timestamp: datetime
    
    @property
    def normalized(self) -> float:
        """Normalize to -1 (extreme fear) to 1 (extreme greed)"""
        return (self.value - 50) / 50
    
    def to_dict(self) -> Dict:
        return {
            "value": self.value,
            "classification": self.classification,
            "normalized": self.normalized,
            "timestamp": self.timestamp.isoformat()
        }


class FearGreedIndex:
    """
    Crypto Fear & Greed Index.
    
    Source: alternative.me API
    
    Values:
    - 0-24: Extreme Fear (buying opportunity)
    - 25-49: Fear
    - 50: Neutral
    - 51-74: Greed
    - 75-100: Extreme Greed (selling opportunity)
    """
    
    API_URL = "https://api.alternative.me/fng/"
    
    def __init__(self):
        self.session: Optional[aiohttp.ClientSession] = None
        self._cache: Optional[FearGreedData] = None
        self._cache_time: Optional[datetime] = None
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_current(self) -> FearGreedData:
        """Get current Fear & Greed index."""
        # Check cache (valid for 1 hour)
        if self._cache and self._cache_time:
            age = (datetime.now() - self._cache_time).total_seconds()
            if age < 3600:
                return self._cache
        
        try:
            session = await self._get_session()
            async with session.get(self.API_URL) as resp:
                data = await resp.json()
                
                if data.get('data'):
                    fg = data['data'][0]
                    value = int(fg.get('value', 50))
                    
                    if value <= 24:
                        classification = 'extreme_fear'
                    elif value <= 49:
                        classification = 'fear'
                    elif value <= 50:
                        classification = 'neutral'
                    elif value <= 74:
                        classification = 'greed'
                    else:
                        classification = 'extreme_greed'
                    
                    self._cache = FearGreedData(
                        value=value,
                        classification=classification,
                        timestamp=datetime.now()
                    )
                    self._cache_time = datetime.now()
                    return self._cache
        except Exception as e:
            print(f"[FearGreed] API error: {e}")
        
        # Return mock data if API fails
        return self._mock_data()
    
    def _mock_data(self) -> FearGreedData:
        """Generate mock data."""
        import random
        value = random.randint(20, 80)
        
        if value <= 24:
            classification = 'extreme_fear'
        elif value <= 49:
            classification = 'fear'
        elif value <= 50:
            classification = 'neutral'
        elif value <= 74:
            classification = 'greed'
        else:
            classification = 'extreme_greed'
        
        return FearGreedData(
            value=value,
            classification=classification,
            timestamp=datetime.now()
        )
    
    async def get_historical(self, days: int = 7) -> list:
        """Get historical Fear & Greed data."""
        try:
            session = await self._get_session()
            url = f"{self.API_URL}?limit={days}"
            async with session.get(url) as resp:
                data = await resp.json()
                
                if data.get('data'):
                    return [
                        FearGreedData(
                            value=int(d['value']),
                            classification=d.get('value_classification', 'neutral'),
                            timestamp=datetime.fromtimestamp(int(d['timestamp']))
                        )
                        for d in data['data']
                    ]
        except:
            pass
        
        return [self._mock_data() for _ in range(days)]
    
    async def get_trend(self, days: int = 7) -> str:
        """Determine trend direction."""
        history = await self.get_historical(days)
        
        if len(history) < 2:
            return "neutral"
        
        first_half = sum(h.value for h in history[:len(history)//2]) / (len(history)//2)
        second_half = sum(h.value for h in history[len(history)//2:]) / (len(history) - len(history)//2)
        
        diff = second_half - first_half
        
        if diff > 10:
            return "increasing_greed"
        elif diff < -10:
            return "increasing_fear"
        return "stable"


# Convenience function
async def get_fear_greed() -> FearGreedData:
    """Quick Fear & Greed check."""
    fg = FearGreedIndex()
    try:
        return await fg.get_current()
    finally:
        await fg.close()
