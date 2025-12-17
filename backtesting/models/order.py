from dataclasses import dataclass
from datetime import datetime
from enum import Enum
from typing import Optional


class OrderType(Enum):
    MARKET = "market"
    LIMIT = "limit"
    STOP = "stop"


class OrderSide(Enum):
    BUY = "buy"
    SELL = "sell"


@dataclass
class Order:
    """Order representation."""
    id: str
    symbol: str
    side: OrderSide
    type: OrderType
    size: float
    price: Optional[float] = None
    stop_price: Optional[float] = None
    status: str = "pending"
    created_at: datetime = None
    filled_at: datetime = None
