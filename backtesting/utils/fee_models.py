"""
Fee calculation models for realistic backtesting.
"""


class FeeModel:
    """Base fee model."""
    def calculate(self, volume: float, order_type: str) -> float:
        raise NotImplementedError


class TieredFeeModel(FeeModel):
    """
    Tiered fee model based on maker/taker.
    
    Default fees match typical exchange rates:
    - Maker: 0.02% (limit orders that add liquidity)
    - Taker: 0.05% (market orders that remove liquidity)
    """
    
    def __init__(self, maker_fee: float = 0.0002, taker_fee: float = 0.0005):
        self.maker_fee = maker_fee
        self.taker_fee = taker_fee
    
    def calculate(self, volume: float, order_type: str) -> float:
        """
        Calculate fee for given volume.
        
        Args:
            volume: Trade volume in quote currency
            order_type: 'maker' or 'taker'
        
        Returns:
            Fee amount in quote currency
        """
        fee_rate = self.maker_fee if order_type == 'maker' else self.taker_fee
        return volume * fee_rate


class VIPFeeModel(FeeModel):
    """
    VIP tier fee model with volume-based discounts.
    """
    
    TIERS = [
        (0, 0.0005, 0.0010),           # Tier 0: < $1M
        (1_000_000, 0.0004, 0.0008),   # Tier 1: $1M+
        (10_000_000, 0.0003, 0.0006),  # Tier 2: $10M+
        (50_000_000, 0.0002, 0.0004),  # Tier 3: $50M+
        (100_000_000, 0.0001, 0.0002), # Tier 4: $100M+
    ]
    
    def __init__(self, monthly_volume: float = 0):
        self.monthly_volume = monthly_volume
        self._update_tier()
    
    def _update_tier(self):
        self.maker_fee = 0.0005
        self.taker_fee = 0.0010
        
        for threshold, maker, taker in self.TIERS:
            if self.monthly_volume >= threshold:
                self.maker_fee = maker
                self.taker_fee = taker
    
    def calculate(self, volume: float, order_type: str) -> float:
        fee_rate = self.maker_fee if order_type == 'maker' else self.taker_fee
        return volume * fee_rate
