from dataclasses import dataclass

@dataclass
class KellyResult:
    fraction: float
    size_usd: float
    leverage: float

class AdaptiveKelly:
    """
    Calculates optimal position size using Kelly Criterion f* = (bp - q) / b
    Adjusted for volatility and regime.
    """
    def __init__(self, win_rate=0.55, win_loss_ratio=1.5):
        self.p = win_rate
        self.b = win_loss_ratio
        
    def calculate_size(self, capital: float, volatility_adj: float = 1.0) -> KellyResult:
        # Basic Kelly
        q = 1 - self.p
        f_star = (self.b * self.p - q) / self.b
        
        # Half-Kelly for safety
        safe_f = f_star * 0.5
        
        # Volatility Adjustment (Inverse)
        final_f = safe_f * (1.0 / volatility_adj)
        final_f = max(0.0, min(0.20, final_f)) # Cap at 20%
        
        size = capital * final_f
        
        return KellyResult(
            fraction=final_f,
            size_usd=size,
            leverage=1.0 # Base leverage
        )
