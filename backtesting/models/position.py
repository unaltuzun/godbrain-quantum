from dataclasses import dataclass
from datetime import datetime
from typing import Optional


@dataclass
class Position:
    """Open position tracking."""
    symbol: str
    side: str  # 'long' or 'short'
    size: float
    entry_price: float
    entry_time: datetime
    stop_loss: Optional[float] = None
    take_profit: Optional[float] = None
    unrealized_pnl: float = 0.0
