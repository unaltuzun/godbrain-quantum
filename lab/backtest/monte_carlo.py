# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN Monte Carlo Simulation
Risk analysis through trade shuffling and confidence intervals.
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from pathlib import Path
import json

from .metrics import BacktestReport, run_metrics_engine
from .parser import TradeEvent


@dataclass
class MonteCarloResult:
    """Results from Monte Carlo simulation."""
    n_simulations: int
    
    # Sharpe Ratio
    sharpe_mean: float
    sharpe_std: float
    sharpe_5pct: float
    sharpe_95pct: float
    
    # Max Drawdown
    max_dd_mean: float
    max_dd_std: float
    max_dd_5pct: float
    max_dd_95pct: float
    
    # PnL
    pnl_mean: float
    pnl_std: float
    pnl_5pct: float
    pnl_95pct: float
    
    # Win Rate
    winrate_mean: float
    winrate_std: float
    
    # Risk of Ruin
    risk_of_ruin: float  # Probability of losing > 50% of capital
    
    # All simulated values
    sharpe_distribution: List[float] = field(default_factory=list)
    pnl_distribution: List[float] = field(default_factory=list)
    max_dd_distribution: List[float] = field(default_factory=list)
    
    def to_dict(self) -> Dict:
        return {
            "n_simulations": self.n_simulations,
            "sharpe": {
                "mean": self.sharpe_mean,
                "std": self.sharpe_std,
                "ci_95": [self.sharpe_5pct, self.sharpe_95pct],
            },
            "max_drawdown": {
                "mean": self.max_dd_mean,
                "std": self.max_dd_std,
                "ci_95": [self.max_dd_5pct, self.max_dd_95pct],
            },
            "pnl": {
                "mean": self.pnl_mean,
                "std": self.pnl_std,
                "ci_95": [self.pnl_5pct, self.pnl_95pct],
            },
            "winrate": {
                "mean": self.winrate_mean,
                "std": self.winrate_std,
            },
            "risk_of_ruin": self.risk_of_ruin,
        }
    
    def __str__(self) -> str:
        return f"""
╔══════════════════════════════════════════════════════════════════╗
║                    MONTE CARLO SIMULATION                        ║
╠══════════════════════════════════════════════════════════════════╣
║ Simulations: {self.n_simulations:,}                                          
║                                                                  ║
║ SHARPE RATIO                                                     ║
║   Mean: {self.sharpe_mean:.3f}  Std: {self.sharpe_std:.3f}                               
║   95% CI: [{self.sharpe_5pct:.3f}, {self.sharpe_95pct:.3f}]                           
║                                                                  ║
║ MAX DRAWDOWN                                                     ║
║   Mean: {self.max_dd_mean*100:.1f}%  Std: {self.max_dd_std*100:.1f}%                              
║   95% CI: [{self.max_dd_5pct*100:.1f}%, {self.max_dd_95pct*100:.1f}%]                          
║                                                                  ║
║ PnL                                                              ║
║   Mean: ${self.pnl_mean:,.2f}  Std: ${self.pnl_std:,.2f}                       
║   95% CI: [${self.pnl_5pct:,.2f}, ${self.pnl_95pct:,.2f}]                  
║                                                                  ║
║ WIN RATE                                                         ║
║   Mean: {self.winrate_mean*100:.1f}%  Std: {self.winrate_std*100:.1f}%                             
║                                                                  ║
║ ⚠️  RISK OF RUIN (>50% loss): {self.risk_of_ruin*100:.2f}%                       
╚══════════════════════════════════════════════════════════════════╝
"""


class MonteCarloSimulator:
    """
    Monte Carlo simulation for trading strategy analysis.
    
    Shuffles trade order to estimate confidence intervals
    and risk metrics independent of entry timing.
    """
    
    def __init__(self, seed: Optional[int] = None):
        self.rng = np.random.default_rng(seed)
    
    def simulate_from_trades(
        self,
        trade_pnls: List[float],
        initial_capital: float = 1000.0,
        n_simulations: int = 1000,
        ruin_threshold: float = 0.5  # 50% loss = ruin
    ) -> MonteCarloResult:
        """
        Run Monte Carlo simulation from a list of trade PnLs.
        
        Args:
            trade_pnls: List of individual trade profit/losses
            initial_capital: Starting capital
            n_simulations: Number of simulations
            ruin_threshold: Fraction of capital loss considered "ruin"
        
        Returns:
            MonteCarloResult with statistics
        """
        if not trade_pnls:
            return self._empty_result(n_simulations)
        
        trade_pnls = np.array(trade_pnls)
        n_trades = len(trade_pnls)
        
        sharpe_values = []
        max_dd_values = []
        pnl_values = []
        winrate_values = []
        ruin_count = 0
        
        for _ in range(n_simulations):
            # Shuffle trades
            shuffled = self.rng.permutation(trade_pnls)
            
            # Calculate equity curve
            equity_curve = np.zeros(n_trades + 1)
            equity_curve[0] = initial_capital
            equity_curve[1:] = initial_capital + np.cumsum(shuffled)
            
            # Metrics
            final_pnl = equity_curve[-1] - initial_capital
            pnl_values.append(final_pnl)
            
            # Win rate
            wins = np.sum(shuffled > 0)
            winrate_values.append(wins / n_trades if n_trades > 0 else 0)
            
            # Max drawdown
            running_max = np.maximum.accumulate(equity_curve)
            drawdowns = (equity_curve - running_max) / running_max
            max_dd = np.abs(np.min(drawdowns))
            max_dd_values.append(max_dd)
            
            # Sharpe (simplified - daily returns approximation)
            returns = np.diff(equity_curve) / equity_curve[:-1]
            if len(returns) > 1 and np.std(returns) > 0:
                sharpe = np.mean(returns) / np.std(returns) * np.sqrt(252)
            else:
                sharpe = 0.0
            sharpe_values.append(sharpe)
            
            # Risk of ruin check
            if np.min(equity_curve) < initial_capital * (1 - ruin_threshold):
                ruin_count += 1
        
        sharpe_arr = np.array(sharpe_values)
        max_dd_arr = np.array(max_dd_values)
        pnl_arr = np.array(pnl_values)
        winrate_arr = np.array(winrate_values)
        
        return MonteCarloResult(
            n_simulations=n_simulations,
            sharpe_mean=float(np.mean(sharpe_arr)),
            sharpe_std=float(np.std(sharpe_arr)),
            sharpe_5pct=float(np.percentile(sharpe_arr, 5)),
            sharpe_95pct=float(np.percentile(sharpe_arr, 95)),
            max_dd_mean=float(np.mean(max_dd_arr)),
            max_dd_std=float(np.std(max_dd_arr)),
            max_dd_5pct=float(np.percentile(max_dd_arr, 5)),
            max_dd_95pct=float(np.percentile(max_dd_arr, 95)),
            pnl_mean=float(np.mean(pnl_arr)),
            pnl_std=float(np.std(pnl_arr)),
            pnl_5pct=float(np.percentile(pnl_arr, 5)),
            pnl_95pct=float(np.percentile(pnl_arr, 95)),
            winrate_mean=float(np.mean(winrate_arr)),
            winrate_std=float(np.std(winrate_arr)),
            risk_of_ruin=ruin_count / n_simulations,
            sharpe_distribution=sharpe_values,
            pnl_distribution=pnl_values,
            max_dd_distribution=max_dd_values,
        )
    
    def _empty_result(self, n: int) -> MonteCarloResult:
        return MonteCarloResult(
            n_simulations=n,
            sharpe_mean=0, sharpe_std=0, sharpe_5pct=0, sharpe_95pct=0,
            max_dd_mean=0, max_dd_std=0, max_dd_5pct=0, max_dd_95pct=0,
            pnl_mean=0, pnl_std=0, pnl_5pct=0, pnl_95pct=0,
            winrate_mean=0, winrate_std=0,
            risk_of_ruin=0,
        )


def extract_trade_pnls_from_events(
    events: List[TradeEvent],
    price_provider,
    initial_capital: float = 1000.0
) -> Tuple[List[float], BacktestReport]:
    """
    Extract individual trade PnLs from events using FIFO matching.
    
    Returns:
        Tuple of (trade_pnls, backtest_report)
    """
    from .metrics import FifoPositionTracker
    
    if not events:
        return [], BacktestReport()
    
    events = sorted(events, key=lambda e: e.timestamp)
    trackers: Dict[str, FifoPositionTracker] = {}
    trade_pnls = []
    
    for event in events:
        if event.symbol not in trackers:
            trackers[event.symbol] = FifoPositionTracker(event.symbol)
        
        price = price_provider.get_price(event.symbol, event.timestamp)
        if price > 0:
            pnl = trackers[event.symbol].process_trade(
                event.action, price, event.size_usd
            )
            if pnl != 0:  # Completed trade
                trade_pnls.append(pnl)
    
    # Also run full backtest for comparison
    report = run_metrics_engine(events, price_provider, initial_capital)
    
    return trade_pnls, report


if __name__ == "__main__":
    # Demo with synthetic trades
    import random
    
    print("Monte Carlo Demo with Synthetic Data")
    print("=" * 50)
    
    # Generate synthetic trade PnLs
    random.seed(42)
    trade_pnls = [random.gauss(5, 20) for _ in range(100)]  # Mean +$5, std $20
    
    simulator = MonteCarloSimulator(seed=42)
    result = simulator.simulate_from_trades(
        trade_pnls,
        initial_capital=1000,
        n_simulations=10000
    )
    
    print(result)
