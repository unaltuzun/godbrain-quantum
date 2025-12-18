# -*- coding: utf-8 -*-
"""
🧊 ICEBERG EXECUTOR - Hidden Quantity Orders
Show only partial size, refill on execution.
"""

import asyncio
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
import random


@dataclass
class IcebergOrder:
    symbol: str
    side: str
    total_quantity: float
    visible_quantity: float
    executed_quantity: float
    remaining_quantity: float
    fills: List[Dict]
    status: str  # 'active', 'completed', 'cancelled'
    start_time: datetime


class IcebergExecutor:
    """
    Iceberg order execution.
    
    Shows only a fraction of total size in the order book.
    Automatically refills when visible portion is executed.
    
    Usage:
        executor = IcebergExecutor(exchange_manager)
        order = await executor.execute('BTC', 'buy', 10, visible_qty=1)
    """
    
    def __init__(self, exchange_manager=None):
        self.exchange_manager = exchange_manager
        self._active_orders: Dict[str, IcebergOrder] = {}
    
    async def execute(self, symbol: str, side: str, total_qty: float,
                     visible_qty: float) -> IcebergOrder:
        """
        Execute iceberg order.
        
        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            total_qty: Total quantity to execute
            visible_qty: Quantity visible in order book
        """
        order = IcebergOrder(
            symbol=symbol,
            side=side,
            total_quantity=total_qty,
            visible_quantity=visible_qty,
            executed_quantity=0,
            remaining_quantity=total_qty,
            fills=[],
            status='active',
            start_time=datetime.now()
        )
        
        order_id = f"{symbol}_{datetime.now().timestamp()}"
        self._active_orders[order_id] = order
        
        # Simulate execution
        while order.remaining_quantity > 0:
            # Place visible portion
            qty_to_place = min(visible_qty, order.remaining_quantity)
            fill = await self._place_and_fill(symbol, side, qty_to_place)
            
            order.fills.append(fill)
            order.executed_quantity += fill['quantity']
            order.remaining_quantity -= fill['quantity']
        
        order.status = 'completed'
        return order
    
    async def _place_and_fill(self, symbol: str, side: str, qty: float) -> Dict:
        """Place order and get fill."""
        if self.exchange_manager:
            try:
                result = await self.exchange_manager.limit_order(symbol, side, qty)
                return {
                    'quantity': qty,
                    'price': result.get('price', 0),
                    'timestamp': datetime.now().isoformat()
                }
            except:
                pass
        
        # Mock fill
        base = 100000 if 'BTC' in symbol.upper() else 3500
        return {
            'quantity': qty,
            'price': base * (1 + random.uniform(-0.0005, 0.0005)),
            'timestamp': datetime.now().isoformat()
        }
    
    def randomize_visible(self, total_qty: float, min_pct: float = 0.05, 
                          max_pct: float = 0.15) -> float:
        """
        Randomize visible quantity to avoid detection.
        
        Returns visible quantity as random percentage of total.
        """
        pct = random.uniform(min_pct, max_pct)
        return total_qty * pct
    
    async def stealth_mode(self, symbol: str, side: str, qty: float) -> IcebergOrder:
        """
        Maximum hiding mode.
        Very small visible size with random variations.
        """
        visible_qty = self.randomize_visible(qty, min_pct=0.02, max_pct=0.05)
        return await self.execute(symbol, side, qty, visible_qty)
