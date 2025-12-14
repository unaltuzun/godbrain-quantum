# ==============================================================================
# TRADE SIMULATOR - Strategy Testing Engine
# ==============================================================================
"""
Simulate trading strategies before execution.

Features:
- Backtest strategies on historical data
- Forward test on simulated market
- Risk analysis
- What-if scenarios
"""

import json
import random
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from pathlib import Path
from datetime import datetime, timedelta

logger = logging.getLogger("seraph.simulation.trade")


@dataclass
class TradeResult:
    """Result of a simulated trade"""
    symbol: str
    action: str  # "BUY" | "SELL"
    entry_price: float
    exit_price: float
    size_usd: float
    pnl: float
    pnl_pct: float
    duration_hours: float
    regime: str
    dna_params: Dict[str, float]


@dataclass
class SimulationResult:
    """Result of a simulation run"""
    total_trades: int
    winning_trades: int
    losing_trades: int
    total_pnl: float
    max_drawdown: float
    sharpe_ratio: float
    best_trade: Optional[TradeResult]
    worst_trade: Optional[TradeResult]
    trades: List[TradeResult]


class TradeSimulator:
    """
    Trading strategy simulator.
    
    Use cases:
    1. Test DNA parameters before applying
    2. Evaluate Seraph's trading decisions
    3. Generate training data for self-improvement
    """
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or Path(__file__).parent.parent.parent / "logs"
        self._price_history: List[Dict] = []
        self._load_price_history()
    
    def _load_price_history(self):
        """Load historical price data"""
        # Try to load from tick history
        tick_file = self.data_dir / "tick_history.json"
        if tick_file.exists():
            try:
                with open(tick_file, 'r') as f:
                    self._price_history = json.load(f)
            except Exception:
                pass
        
        # Generate synthetic data if no history
        if not self._price_history:
            self._price_history = self._generate_synthetic_prices(1000)
    
    def _generate_synthetic_prices(self, n: int) -> List[Dict]:
        """Generate synthetic price data for testing"""
        prices = []
        price = 100000  # Start at 100k
        
        for i in range(n):
            # Random walk with mean reversion
            change = random.gauss(0, 0.02)  # 2% volatility
            price *= (1 + change)
            
            prices.append({
                "timestamp": (datetime.now() - timedelta(hours=n-i)).isoformat(),
                "price": price,
                "volume": random.uniform(1000, 10000),
                "regime": random.choice(["BULL", "BEAR", "SIDEWAYS"])
            })
        
        return prices
    
    def simulate_trade(
        self,
        action: str,
        entry_idx: int,
        size_usd: float,
        dna_params: Dict[str, float]
    ) -> TradeResult:
        """
        Simulate a single trade.
        
        Args:
            action: "BUY" or "SELL"
            entry_idx: Index in price history
            size_usd: Trade size in USD
            dna_params: DNA parameters (stop_loss, take_profit, etc.)
        
        Returns:
            TradeResult
        """
        if entry_idx >= len(self._price_history) - 1:
            entry_idx = len(self._price_history) - 100
        
        entry_price = self._price_history[entry_idx]["price"]
        regime = self._price_history[entry_idx]["regime"]
        
        stop_loss = dna_params.get("stop_loss_pct", 2.0) / 100
        take_profit = dna_params.get("take_profit_pct", 4.0) / 100
        
        # Simulate price movement
        exit_idx = entry_idx
        exit_price = entry_price
        
        for i in range(entry_idx + 1, min(entry_idx + 100, len(self._price_history))):
            current_price = self._price_history[i]["price"]
            
            if action == "BUY":
                pnl_pct = (current_price - entry_price) / entry_price
            else:  # SELL
                pnl_pct = (entry_price - current_price) / entry_price
            
            # Check stop loss / take profit
            if pnl_pct <= -stop_loss or pnl_pct >= take_profit:
                exit_idx = i
                exit_price = current_price
                break
        else:
            # Timeout - exit at last price
            exit_idx = min(entry_idx + 99, len(self._price_history) - 1)
            exit_price = self._price_history[exit_idx]["price"]
        
        # Calculate P&L
        if action == "BUY":
            pnl_pct = (exit_price - entry_price) / entry_price
        else:
            pnl_pct = (entry_price - exit_price) / entry_price
        
        pnl = size_usd * pnl_pct
        duration_hours = exit_idx - entry_idx  # Simplified
        
        return TradeResult(
            symbol="BTC/USDT",
            action=action,
            entry_price=entry_price,
            exit_price=exit_price,
            size_usd=size_usd,
            pnl=pnl,
            pnl_pct=pnl_pct * 100,
            duration_hours=duration_hours,
            regime=regime,
            dna_params=dna_params
        )
    
    def run_simulation(
        self,
        dna_params: Dict[str, float],
        n_trades: int = 100,
        size_usd: float = 1000
    ) -> SimulationResult:
        """
        Run a full simulation with given DNA parameters.
        
        Args:
            dna_params: DNA parameters to test
            n_trades: Number of trades to simulate
            size_usd: Trade size
        
        Returns:
            SimulationResult with statistics
        """
        trades: List[TradeResult] = []
        equity_curve = [0]
        max_equity = 0
        max_drawdown = 0
        
        for i in range(n_trades):
            # Random entry point
            entry_idx = random.randint(0, len(self._price_history) - 150)
            
            # Random direction (simplified)
            action = random.choice(["BUY", "SELL"])
            
            trade = self.simulate_trade(action, entry_idx, size_usd, dna_params)
            trades.append(trade)
            
            # Track equity
            equity_curve.append(equity_curve[-1] + trade.pnl)
            max_equity = max(max_equity, equity_curve[-1])
            drawdown = max_equity - equity_curve[-1]
            max_drawdown = max(max_drawdown, drawdown)
        
        # Calculate statistics
        winning = [t for t in trades if t.pnl > 0]
        losing = [t for t in trades if t.pnl <= 0]
        total_pnl = sum(t.pnl for t in trades)
        
        # Sharpe ratio (simplified)
        returns = [t.pnl_pct for t in trades]
        avg_return = sum(returns) / len(returns)
        std_return = (sum((r - avg_return)**2 for r in returns) / len(returns)) ** 0.5
        sharpe = avg_return / max(0.001, std_return) * (252 ** 0.5)  # Annualized
        
        return SimulationResult(
            total_trades=len(trades),
            winning_trades=len(winning),
            losing_trades=len(losing),
            total_pnl=total_pnl,
            max_drawdown=max_drawdown,
            sharpe_ratio=sharpe,
            best_trade=max(trades, key=lambda t: t.pnl) if trades else None,
            worst_trade=min(trades, key=lambda t: t.pnl) if trades else None,
            trades=trades
        )
    
    def compare_dna_params(
        self,
        params_list: List[Dict[str, float]],
        n_trades: int = 100
    ) -> List[Dict[str, Any]]:
        """
        Compare multiple DNA parameter sets.
        
        Returns ranked list of results.
        """
        results = []
        
        for i, params in enumerate(params_list):
            sim_result = self.run_simulation(params, n_trades)
            results.append({
                "rank": 0,
                "params": params,
                "total_pnl": sim_result.total_pnl,
                "win_rate": sim_result.winning_trades / max(1, sim_result.total_trades),
                "sharpe": sim_result.sharpe_ratio,
                "max_drawdown": sim_result.max_drawdown
            })
        
        # Rank by Sharpe ratio
        results.sort(key=lambda x: x["sharpe"], reverse=True)
        for i, r in enumerate(results):
            r["rank"] = i + 1
        
        return results

