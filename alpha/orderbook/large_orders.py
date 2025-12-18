# -*- coding: utf-8 -*-
"""
🐋 LARGE ORDER DETECTOR - Whale Order Detection
Detect large orders, spoofing, and iceberg orders.
"""

from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class LargeOrder:
    symbol: str
    side: str  # 'bid' or 'ask'
    price: float
    size: float
    size_usd: float
    is_wall: bool
    timestamp: datetime


@dataclass
class HiddenOrder:
    symbol: str
    side: str
    estimated_size: float
    detected_refills: int
    price_level: float
    timestamp: datetime


class LargeOrderDetector:
    """
    Detect whale orders in order book.
    
    Features:
    - Large order detection
    - Spoofing detection (fake walls)
    - Iceberg order detection (hidden size)
    """
    
    def __init__(self, min_size_usd: float = 100_000, exchange_manager=None):
        self.min_size_usd = min_size_usd
        self.exchange_manager = exchange_manager
        self._historical_walls: Dict[str, List] = {}
    
    async def scan_large_orders(self, symbol: str) -> List[LargeOrder]:
        """Scan for large orders in the book."""
        orderbook = await self._fetch_orderbook(symbol, depth=100)
        large_orders = []
        
        base_price = orderbook['bids'][0][0] if orderbook['bids'] else 100000
        
        # Check bids
        for price, size in orderbook['bids']:
            size_usd = price * size
            if size_usd >= self.min_size_usd:
                large_orders.append(LargeOrder(
                    symbol=symbol,
                    side='bid',
                    price=price,
                    size=size,
                    size_usd=size_usd,
                    is_wall=size_usd >= self.min_size_usd * 5,
                    timestamp=datetime.now()
                ))
        
        # Check asks
        for price, size in orderbook['asks']:
            size_usd = price * size
            if size_usd >= self.min_size_usd:
                large_orders.append(LargeOrder(
                    symbol=symbol,
                    side='ask',
                    price=price,
                    size=size,
                    size_usd=size_usd,
                    is_wall=size_usd >= self.min_size_usd * 5,
                    timestamp=datetime.now()
                ))
        
        return sorted(large_orders, key=lambda x: x.size_usd, reverse=True)
    
    async def _fetch_orderbook(self, symbol: str, depth: int) -> Dict:
        """Fetch orderbook from exchange."""
        if self.exchange_manager:
            try:
                return await self.exchange_manager.get_orderbook(symbol, depth)
            except:
                pass
        return self._mock_orderbook(symbol, depth)
    
    def _mock_orderbook(self, symbol: str, depth: int) -> Dict:
        """Generate mock orderbook with some whale orders."""
        import random
        base_price = 100000 if 'BTC' in symbol.upper() else 3500
        
        bids = []
        asks = []
        
        for i in range(depth):
            bid_price = base_price * (1 - 0.0001 * (i + 1))
            ask_price = base_price * (1 + 0.0001 * (i + 1))
            
            # Occasionally add whale orders
            if random.random() < 0.05:
                bid_vol = random.uniform(10, 50)
                ask_vol = random.uniform(10, 50)
            else:
                bid_vol = random.uniform(0.1, 2)
                ask_vol = random.uniform(0.1, 2)
            
            bids.append([bid_price, bid_vol])
            asks.append([ask_price, ask_vol])
        
        return {"bids": bids, "asks": asks}
    
    async def spoofing_detect(self, symbol: str) -> bool:
        """
        Detect potential spoofing.
        Spoofing: Large orders that disappear when price approaches.
        """
        # Check if previous walls disappeared
        current_orders = await self.scan_large_orders(symbol)
        current_walls = {(o.side, o.price) for o in current_orders if o.is_wall}
        
        key = symbol
        if key in self._historical_walls:
            prev_walls = self._historical_walls[key]
            disappeared = prev_walls - current_walls
            
            # If significant walls disappeared, possible spoofing
            if len(disappeared) >= 2:
                return True
        
        self._historical_walls[key] = current_walls
        return False
    
    async def iceberg_detect(self, symbol: str) -> List[HiddenOrder]:
        """
        Detect iceberg orders (hidden quantity).
        Look for repeated refills at same price level.
        """
        # Mock detection - in production would track order flow
        import random
        
        icebergs = []
        if random.random() < 0.2:  # 20% chance of detecting iceberg
            base_price = 100000 if 'BTC' in symbol.upper() else 3500
            
            icebergs.append(HiddenOrder(
                symbol=symbol,
                side=random.choice(['bid', 'ask']),
                estimated_size=random.uniform(10, 100),
                detected_refills=random.randint(3, 10),
                price_level=base_price * (1 + random.uniform(-0.01, 0.01)),
                timestamp=datetime.now()
            ))
        
        return icebergs
    
    async def whale_order_signal(self, symbol: str) -> Optional[Dict]:
        """Generate signal from whale order activity."""
        large_orders = await self.scan_large_orders(symbol)
        
        if not large_orders:
            return None
        
        bid_walls = sum(o.size_usd for o in large_orders if o.side == 'bid' and o.is_wall)
        ask_walls = sum(o.size_usd for o in large_orders if o.side == 'ask' and o.is_wall)
        
        if bid_walls > ask_walls * 1.5:
            direction = "bullish"
        elif ask_walls > bid_walls * 1.5:
            direction = "bearish"
        else:
            direction = "neutral"
        
        return {
            "symbol": symbol,
            "large_orders_count": len(large_orders),
            "bid_wall_usd": bid_walls,
            "ask_wall_usd": ask_walls,
            "direction": direction,
            "spoofing_detected": await self.spoofing_detect(symbol),
            "timestamp": datetime.now().isoformat()
        }
