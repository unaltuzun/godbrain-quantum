from dataclasses import dataclass
from datetime import datetime

@dataclass
class ArbSignal:
    timestamp: datetime
    symbol: str
    buy_ex: str
    sell_ex: str
    spread_pct: float
    is_actionable: bool

class LatencyArbEngine:
    """
    Detects price dislocations across exchanges (Spatial Arbitrage).
    """
    def __init__(self, min_spread_pct: float = 0.5):
        self.min_spread = min_spread_pct
        
    def check_arb(self, prices: dict) -> ArbSignal:
        # prices = {"binance": 50000, "okx": 50100}
        if not prices or len(prices) < 2:
            return None
            
        sorted_ex = sorted(prices.items(), key=lambda x: x[1])
        min_ex, min_price = sorted_ex[0]
        max_ex, max_price = sorted_ex[-1]
        
        spread = (max_price - min_price) / min_price * 100
        
        return ArbSignal(
            timestamp=datetime.now(),
            symbol="BTC/USDT",
            buy_ex=min_ex,
            sell_ex=max_ex,
            spread_pct=spread,
            is_actionable=spread > self.min_spread
        )
