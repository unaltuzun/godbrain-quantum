import numpy as np
from dataclasses import dataclass
from collections import deque
from datetime import datetime

@dataclass
class KellyResult:
    recommended_fraction: float
    position_size_usd: float
    risk_metrics: dict

class AdaptiveKelly:
    def __init__(self):
        self.trades = deque(maxlen=100)
        self.peak_equity = 0
        self.current_drawdown = 0
        
    def record_trade(self, pnl_usd, pnl_pct):
        self.trades.append({'pnl': pnl_usd, 'pct': pnl_pct, 'win': pnl_usd > 0})
        
    def update_equity(self, eq):
        if eq > self.peak_equity: self.peak_equity = eq
        if self.peak_equity > 0:
            self.current_drawdown = (self.peak_equity - eq) / self.peak_equity
            
    def calculate(self, capital, volatility_multiplier=1.0, regime_multiplier=1.0, conviction=1.0):
        if len(self.trades) < 10:
            p = 0.55
            b = 1.5
        else:
            wins = [t for t in self.trades if t['win']]
            losses = [t for t in self.trades if not t['win']]
            p = len(wins) / len(self.trades)
            avg_win = np.mean([t['pct'] for t in wins]) if wins else 0
            avg_loss = abs(np.mean([t['pct'] for t in losses])) if losses else 1
            b = avg_win / avg_loss if avg_loss > 0 else 1.5
            
        q = 1 - p
        f = (b * p - q) / b if b > 0 else 0
        f = max(0, f) * 0.5 # Half Kelly
        
        # Adjustments
        if self.current_drawdown > 0.1: f *= 0.5
        f *= (1.0 / max(1.0, volatility_multiplier))
        f *= regime_multiplier
        f *= conviction
        f = min(f, 0.25) # Max 25% portfolio
        
        return KellyResult(f, capital * f, {'win_rate': p, 'ratio': b})
