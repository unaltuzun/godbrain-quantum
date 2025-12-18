# -*- coding: utf-8 -*-
"""
🦢 TAIL RISK MANAGER - Black Swan Protection
Extreme event detection and protection.
"""

import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class TailMetrics:
    left_tail_probability: float
    expected_tail_loss: float
    tail_index: float
    kurtosis: float
    skewness: float


@dataclass
class StressScenario:
    name: str
    description: str
    market_drop_pct: float
    portfolio_impact: float
    probability: float


class TailRiskManager:
    """
    Tail risk / Black swan protection.
    
    Features:
    - Tail risk metrics
    - Stress testing
    - Black swan probability
    - Hedge recommendations
    """
    
    def __init__(self, tail_threshold: float = 0.05):
        self.tail_threshold = tail_threshold  # 5% worst cases
    
    def calculate_tail_risk(self, returns: np.ndarray) -> TailMetrics:
        """Calculate comprehensive tail risk metrics."""
        from scipy import stats
        
        # Left tail (losses)
        threshold = np.percentile(returns, self.tail_threshold * 100)
        tail_returns = returns[returns <= threshold]
        
        left_tail_prob = len(tail_returns) / len(returns)
        expected_tail_loss = abs(np.mean(tail_returns)) if len(tail_returns) > 0 else 0
        
        # Tail index (higher = fatter tails)
        kurtosis = stats.kurtosis(returns)
        skewness = stats.skew(returns)
        
        # Tail index using Hill estimator (simplified)
        sorted_returns = np.sort(returns)
        k = int(len(returns) * self.tail_threshold)
        if k > 1:
            tail_index = k / np.sum(np.log(sorted_returns[-k:] / sorted_returns[-k-1]))
        else:
            tail_index = 2.0  # Default
        
        return TailMetrics(
            left_tail_probability=left_tail_prob,
            expected_tail_loss=expected_tail_loss,
            tail_index=abs(tail_index),
            kurtosis=kurtosis,
            skewness=skewness
        )
    
    def black_swan_probability(self, returns: np.ndarray, days: int = 30) -> float:
        """
        Estimate probability of black swan event in next N days.
        
        Black swan = >3 standard deviation move
        """
        sigma = np.std(returns)
        mu = np.mean(returns)
        
        # Historical frequency of >3 sigma events
        extreme_events = np.sum(np.abs(returns - mu) > 3 * sigma)
        daily_prob = extreme_events / len(returns)
        
        # Probability in next N days
        prob_n_days = 1 - (1 - daily_prob) ** days
        
        return prob_n_days
    
    def stress_scenarios(self, portfolio_value: float) -> List[StressScenario]:
        """
        Predefined stress scenarios based on historical events.
        """
        scenarios = [
            StressScenario(
                name="COVID Crash (Mar 2020)",
                description="BTC dropped 50% in 24 hours",
                market_drop_pct=50,
                portfolio_impact=portfolio_value * 0.50,
                probability=0.01
            ),
            StressScenario(
                name="LUNA Collapse (May 2022)",
                description="Alt coins dropped 80%+",
                market_drop_pct=80,
                portfolio_impact=portfolio_value * 0.60,
                probability=0.02
            ),
            StressScenario(
                name="Flash Crash",
                description="30% drop in minutes, recovery in hours",
                market_drop_pct=30,
                portfolio_impact=portfolio_value * 0.30,
                probability=0.05
            ),
            StressScenario(
                name="Bear Market",
                description="Prolonged 70% drawdown over months",
                market_drop_pct=70,
                portfolio_impact=portfolio_value * 0.70,
                probability=0.10
            ),
            StressScenario(
                name="Exchange Failure",
                description="Major exchange becomes insolvent",
                market_drop_pct=40,
                portfolio_impact=portfolio_value * 0.40,
                probability=0.03
            ),
        ]
        return scenarios
    
    def hedge_recommendation(self, returns: np.ndarray, 
                            portfolio_value: float) -> Dict:
        """
        Generate hedge recommendations based on tail risk.
        """
        metrics = self.calculate_tail_risk(returns)
        black_swan_prob = self.black_swan_probability(returns)
        
        recommendations = []
        
        if metrics.kurtosis > 3:  # Fat tails
            recommendations.append({
                "action": "buy_puts",
                "reason": "High kurtosis indicates fat tails",
                "suggested_coverage": portfolio_value * 0.1
            })
        
        if metrics.skewness < -0.5:  # Left skew
            recommendations.append({
                "action": "reduce_leverage",
                "reason": "Negative skew indicates crash risk",
                "suggested_reduction": 0.2
            })
        
        if black_swan_prob > 0.05:  # >5% black swan probability
            recommendations.append({
                "action": "increase_cash",
                "reason": "Elevated black swan probability",
                "suggested_cash_pct": 0.2
            })
        
        return {
            "metrics": {
                "kurtosis": metrics.kurtosis,
                "skewness": metrics.skewness,
                "black_swan_prob": black_swan_prob
            },
            "recommendations": recommendations,
            "overall_risk": "high" if len(recommendations) >= 2 else "moderate" if recommendations else "low"
        }
    
    def circuit_breaker(self, current_drawdown: float, 
                        threshold: float = 0.15) -> Dict:
        """
        Circuit breaker - stop trading when drawdown exceeds threshold.
        """
        triggered = current_drawdown >= threshold
        
        return {
            "triggered": triggered,
            "current_drawdown": current_drawdown,
            "threshold": threshold,
            "action": "halt_trading" if triggered else "continue",
            "message": f"CIRCUIT BREAKER: {'TRIGGERED' if triggered else 'OK'}"
        }
