from dataclasses import dataclass
from datetime import datetime
from enum import Enum


class TradeType(Enum):
    ENTRY = "entry"
    EXIT = "exit"


@dataclass
class Trade:
    """Trade execution record."""
    symbol: str
    side: str
    type: TradeType
    price: float
    size: float
    fee: float
    timestamp: datetime
    pnl: float = None
    slippage: float = 0.0
