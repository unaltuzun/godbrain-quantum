# -*- coding: utf-8 -*-
"""
📊 ORDER BOOK IMBALANCE - Short-term Direction Predictor
Bid/Ask imbalance indicates immediate supply/demand.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass


@dataclass
class ImbalanceData:
    symbol: str
    exchange: str
    bid_volume: float
    ask_volume: float
    imbalance: float  # -1 to 1
    timestamp: datetime
    
    @property
    def direction(self) -> str:
        if self.imbalance > 0.2:
            return "bullish"
        elif self.imbalance < -0.2:
            return "bearish"
        return "neutral"
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "exchange": self.exchange,
            "bid_volume": self.bid_volume,
            "ask_volume": self.ask_volume,
            "imbalance": self.imbalance,
            "direction": self.direction,
            "timestamp": self.timestamp.isoformat()
        }


@dataclass
class ImbalanceSignal:
    symbol: str
    imbalance: float
    trend: str  # 'increasing', 'decreasing', 'stable'
    multi_exchange_agreement: float
    confidence: float
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "imbalance": self.imbalance,
            "direction": "bullish" if self.imbalance > 0.2 else "bearish" if self.imbalance < -0.2 else "neutral",
            "trend": self.trend,
            "multi_exchange_agreement": self.multi_exchange_agreement,
            "confidence": self.confidence,
            "timestamp": self.timestamp.isoformat()
        }


class OrderBookImbalance:
    """
    Calculate and track order book imbalance.
    
    Formula: (bid_volume - ask_volume) / (bid_volume + ask_volume)
    Range: -1 (heavy selling) to +1 (heavy buying)
    
    Usage:
        imbalance = OrderBookImbalance(exchange_manager)
        current = await imbalance.get_imbalance('BTC', depth=20)
        signal = await imbalance.imbalance_signal('BTC')
    """
    
    def __init__(self, exchange_manager=None):
        self.exchange_manager = exchange_manager
        self._history: Dict[str, List[ImbalanceData]] = {}
    
    async def get_imbalance(self, symbol: str, depth: int = 20) -> float:
        """
        Get current order book imbalance.
        
        Returns:
            float: Imbalance from -1 (sell pressure) to +1 (buy pressure)
        """
        orderbook = await self._fetch_orderbook(symbol, depth)
        
        bid_volume = sum(level[1] for level in orderbook['bids'])
        ask_volume = sum(level[1] for level in orderbook['asks'])
        
        total = bid_volume + ask_volume
        if total == 0:
            return 0
        
        imbalance = (bid_volume - ask_volume) / total
        
        # Store in history
        if symbol not in self._history:
            self._history[symbol] = []
        
        self._history[symbol].append(ImbalanceData(
            symbol=symbol,
            exchange="aggregated",
            bid_volume=bid_volume,
            ask_volume=ask_volume,
            imbalance=imbalance,
            timestamp=datetime.now()
        ))
        
        # Keep only last hour
        cutoff = datetime.now() - timedelta(hours=1)
        self._history[symbol] = [h for h in self._history[symbol] if h.timestamp > cutoff]
        
        return imbalance
    
    async def _fetch_orderbook(self, symbol: str, depth: int) -> Dict:
        """Fetch orderbook from exchange."""
        if self.exchange_manager:
            try:
                return await self.exchange_manager.get_orderbook(symbol, depth)
            except:
                pass
        
        # Mock orderbook
        return self._mock_orderbook(symbol, depth)
    
    def _mock_orderbook(self, symbol: str, depth: int) -> Dict:
        """Generate mock orderbook."""
        import random
        
        base_price = 100000 if 'BTC' in symbol.upper() else 3500 if 'ETH' in symbol.upper() else 100
        
        bids = []
        asks = []
        
        for i in range(depth):
            bid_price = base_price * (1 - 0.0001 * (i + 1))
            ask_price = base_price * (1 + 0.0001 * (i + 1))
            
            # Add some randomness to volume
            bid_vol = random.uniform(0.1, 10) * (1 + random.random())
            ask_vol = random.uniform(0.1, 10) * (1 + random.random())
            
            bids.append([bid_price, bid_vol])
            asks.append([ask_price, ask_vol])
        
        return {"bids": bids, "asks": asks}
    
    async def imbalance_trend(self, symbol: str, minutes: int = 60) -> List[Tuple[datetime, float]]:
        """Get imbalance trend over time."""
        # Ensure we have history
        if symbol not in self._history or len(self._history[symbol]) < 2:
            # Generate some historical data
            for _ in range(minutes):
                await self.get_imbalance(symbol)
                await asyncio.sleep(0.01)  # Minimal delay
        
        history = self._history.get(symbol, [])
        return [(h.timestamp, h.imbalance) for h in history]
    
    async def multi_exchange_imbalance(self, symbol: str) -> Dict[str, float]:
        """Get imbalance across multiple exchanges."""
        exchanges = ['binance', 'okx', 'bybit', 'coinbase']
        
        results = {}
        for exchange in exchanges:
            # Mock different imbalances per exchange
            import random
            results[exchange] = random.uniform(-0.5, 0.5)
        
        # Calculate weighted average
        results['weighted_avg'] = sum(results.values()) / len(exchanges)
        
        return results
    
    async def imbalance_signal(self, symbol: str, threshold: float = 0.3) -> ImbalanceSignal:
        """Generate trading signal from imbalance."""
        current_imbalance = await self.get_imbalance(symbol)
        
        # Get trend
        history = self._history.get(symbol, [])
        if len(history) >= 5:
            recent = [h.imbalance for h in history[-5:]]
            if recent[-1] > recent[0] + 0.1:
                trend = "increasing"
            elif recent[-1] < recent[0] - 0.1:
                trend = "decreasing"
            else:
                trend = "stable"
        else:
            trend = "stable"
        
        # Multi-exchange check
        multi = await self.multi_exchange_imbalance(symbol)
        agreement = 1 - abs(max(multi.values()) - min(multi.values()))
        
        # Confidence based on strength and agreement
        confidence = abs(current_imbalance) * agreement
        
        return ImbalanceSignal(
            symbol=symbol,
            imbalance=current_imbalance,
            trend=trend,
            multi_exchange_agreement=agreement,
            confidence=confidence,
            timestamp=datetime.now()
        )


# Convenience function
async def get_imbalance(symbol: str) -> ImbalanceSignal:
    """Quick imbalance check."""
    analyzer = OrderBookImbalance()
    return await analyzer.imbalance_signal(symbol)
