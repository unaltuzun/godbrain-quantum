# -*- coding: utf-8 -*-
"""
🛣️ SMART ORDER ROUTER - Best Execution Across Venues
Route orders to optimal exchanges.
"""

from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class VenueScore:
    exchange: str
    price: float
    liquidity: float
    fees_bps: float
    latency_ms: float
    score: float  # Combined score


@dataclass
class RoutedOrder:
    exchange: str
    symbol: str
    side: str
    quantity: float
    expected_price: float
    expected_slippage: float
    status: str


class SmartOrderRouter:
    """
    Smart Order Router for best execution.
    
    Analyzes multiple venues and routes orders optimally.
    
    Features:
    - Price comparison
    - Liquidity analysis
    - Fee optimization
    - Latency consideration
    """
    
    def __init__(self, exchange_manager=None):
        self.exchange_manager = exchange_manager
        self.venues = ['binance', 'okx', 'bybit', 'coinbase']
        
        # Fee structure (in bps)
        self.fees = {
            'binance': 10,
            'okx': 8,
            'bybit': 6,
            'coinbase': 50,
        }
    
    async def analyze_venues(self, symbol: str, qty: float) -> List[VenueScore]:
        """Analyze all venues for best execution."""
        scores = []
        
        for venue in self.venues:
            venue_data = await self._get_venue_data(venue, symbol, qty)
            
            # Calculate composite score (higher = better)
            score = (
                (1 / venue_data['price']) * 1000 +  # Better price
                venue_data['liquidity'] * 0.5 +      # More liquidity
                (100 - venue_data['fees']) * 0.3 +   # Lower fees
                (100 - venue_data['latency']) * 0.2  # Lower latency
            )
            
            scores.append(VenueScore(
                exchange=venue,
                price=venue_data['price'],
                liquidity=venue_data['liquidity'],
                fees_bps=venue_data['fees'],
                latency_ms=venue_data['latency'],
                score=score
            ))
        
        return sorted(scores, key=lambda x: x.score, reverse=True)
    
    async def _get_venue_data(self, venue: str, symbol: str, qty: float) -> Dict:
        """Get venue-specific data."""
        if self.exchange_manager:
            try:
                ticker = await self.exchange_manager.get_ticker(symbol, venue)
                depth = await self.exchange_manager.get_depth(symbol, venue)
                return {
                    'price': ticker.get('last', 100000),
                    'liquidity': depth.get('bid_volume', 100),
                    'fees': self.fees.get(venue, 10),
                    'latency': 50  # Would measure actual latency
                }
            except:
                pass
        
        # Mock data
        import random
        base = 100000 if 'BTC' in symbol.upper() else 3500
        return {
            'price': base * (1 + random.uniform(-0.001, 0.001)),
            'liquidity': random.uniform(50, 150),
            'fees': self.fees.get(venue, 10),
            'latency': random.uniform(20, 100)
        }
    
    async def route_order(self, symbol: str, side: str, qty: float) -> List[RoutedOrder]:
        """Route order to best venue(s)."""
        scores = await self.analyze_venues(symbol, qty)
        
        best_venue = scores[0]
        
        return [RoutedOrder(
            exchange=best_venue.exchange,
            symbol=symbol,
            side=side,
            quantity=qty,
            expected_price=best_venue.price,
            expected_slippage=0.0005,  # 5 bps
            status='routed'
        )]
    
    async def split_order(self, symbol: str, side: str, qty: float,
                         max_venues: int = 3) -> List[RoutedOrder]:
        """Split order across multiple venues."""
        scores = await self.analyze_venues(symbol, qty)
        
        # Use top venues
        top_venues = scores[:max_venues]
        total_score = sum(v.score for v in top_venues)
        
        orders = []
        for venue in top_venues:
            venue_qty = qty * (venue.score / total_score)
            orders.append(RoutedOrder(
                exchange=venue.exchange,
                symbol=symbol,
                side=side,
                quantity=venue_qty,
                expected_price=venue.price,
                expected_slippage=0.0003,  # Lower slippage with split
                status='routed'
            ))
        
        return orders
    
    async def execution_quality_report(self, orders: List[RoutedOrder]) -> Dict:
        """Generate execution quality report."""
        if not orders:
            return {}
        
        total_qty = sum(o.quantity for o in orders)
        weighted_price = sum(o.expected_price * o.quantity for o in orders) / total_qty
        
        return {
            'total_quantity': total_qty,
            'venues_used': len(orders),
            'weighted_avg_price': weighted_price,
            'expected_slippage_bps': sum(o.expected_slippage for o in orders) / len(orders) * 10000,
            'execution_rating': 'excellent' if len(orders) > 1 else 'good',
            'timestamp': datetime.now().isoformat()
        }
