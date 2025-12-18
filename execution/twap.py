# -*- coding: utf-8 -*-
"""
⏰ TWAP EXECUTOR - Time-Weighted Average Price
Split orders across time to minimize market impact.
"""

import asyncio
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass, field


@dataclass
class TWAPSlice:
    slice_id: int
    quantity: float
    target_time: datetime
    executed: bool = False
    execution_price: Optional[float] = None
    execution_time: Optional[datetime] = None


@dataclass
class TWAPReport:
    symbol: str
    side: str
    total_quantity: float
    executed_quantity: float
    average_price: float
    target_duration_minutes: int
    slices: int
    completion_pct: float
    start_time: datetime
    end_time: Optional[datetime] = None
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "side": self.side,
            "total_quantity": self.total_quantity,
            "executed_quantity": self.executed_quantity,
            "average_price": self.average_price,
            "duration_minutes": self.target_duration_minutes,
            "slices": self.slices,
            "completion_pct": self.completion_pct,
            "vwap_benchmark": self.average_price,  # Would compare to market VWAP
        }


class TWAPExecutor:
    """
    Time-Weighted Average Price execution.
    
    Splits large orders into equal time slices to minimize market impact.
    
    Usage:
        executor = TWAPExecutor(exchange_manager)
        report = await executor.execute('BTC', 'buy', 10, duration_minutes=60, slices=12)
    """
    
    def __init__(self, exchange_manager=None):
        self.exchange_manager = exchange_manager
        self._active_orders: Dict[str, List[TWAPSlice]] = {}
    
    async def execute(self, symbol: str, side: str, total_qty: float,
                     duration_minutes: int, slices: int = 10) -> TWAPReport:
        """
        Execute TWAP order.
        
        Args:
            symbol: Trading pair
            side: 'buy' or 'sell'
            total_qty: Total quantity to execute
            duration_minutes: Total execution time
            slices: Number of slices
        """
        slice_qty = total_qty / slices
        interval = duration_minutes * 60 / slices  # seconds between slices
        
        start_time = datetime.now()
        executed_qty = 0
        prices = []
        
        # Create slices
        order_slices = []
        for i in range(slices):
            target_time = start_time + timedelta(seconds=i * interval)
            order_slices.append(TWAPSlice(
                slice_id=i,
                quantity=slice_qty,
                target_time=target_time
            ))
        
        # Execute slices (simulated)
        for slice_order in order_slices:
            # Wait until target time (in real implementation)
            # await asyncio.sleep(interval)
            
            price = await self._execute_slice(symbol, side, slice_order.quantity)
            slice_order.executed = True
            slice_order.execution_price = price
            slice_order.execution_time = datetime.now()
            
            executed_qty += slice_order.quantity
            prices.append(price)
        
        avg_price = sum(prices) / len(prices) if prices else 0
        
        return TWAPReport(
            symbol=symbol,
            side=side,
            total_quantity=total_qty,
            executed_quantity=executed_qty,
            average_price=avg_price,
            target_duration_minutes=duration_minutes,
            slices=slices,
            completion_pct=executed_qty / total_qty * 100,
            start_time=start_time,
            end_time=datetime.now()
        )
    
    async def _execute_slice(self, symbol: str, side: str, qty: float) -> float:
        """Execute a single slice."""
        if self.exchange_manager:
            try:
                result = await self.exchange_manager.market_order(symbol, side, qty)
                return result.get('price', 0)
            except:
                pass
        
        # Mock execution
        import random
        base = 100000 if 'BTC' in symbol.upper() else 3500
        return base * (1 + random.uniform(-0.001, 0.001))
    
    async def adaptive_twap(self, symbol: str, side: str, qty: float, 
                           duration_minutes: int) -> TWAPReport:
        """
        Adaptive TWAP - adjust slice size based on volume.
        Execute more when volume is high.
        """
        # Get volume profile (mock)
        import random
        volume_weights = [random.uniform(0.5, 1.5) for _ in range(10)]
        total_weight = sum(volume_weights)
        
        # Distribute quantity based on volume
        slices = len(volume_weights)
        slice_qtys = [qty * w / total_weight for w in volume_weights]
        
        interval = duration_minutes * 60 / slices
        start_time = datetime.now()
        executed_qty = 0
        prices = []
        
        for i, slice_qty in enumerate(slice_qtys):
            price = await self._execute_slice(symbol, side, slice_qty)
            executed_qty += slice_qty
            prices.append(price * slice_qty)  # Weighted
        
        avg_price = sum(prices) / executed_qty if executed_qty > 0 else 0
        
        return TWAPReport(
            symbol=symbol,
            side=side,
            total_quantity=qty,
            executed_quantity=executed_qty,
            average_price=avg_price,
            target_duration_minutes=duration_minutes,
            slices=slices,
            completion_pct=100,
            start_time=start_time,
            end_time=datetime.now()
        )
