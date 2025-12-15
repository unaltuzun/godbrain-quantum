# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN Strategy Comparison
A/B testing framework for DNA configurations.
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Any, Callable, Optional
from scipy import stats


@dataclass
class StrategyMetrics:
    """Metrics for a single strategy."""
    name: str
    sharpe: float
    pnl: float
    pnl_pct: float
    max_dd: float
    win_rate: float
    trade_count: int
    profit_factor: float
    avg_trade: float
    
    # For statistical comparison
    daily_returns: List[float] = field(default_factory=list)


@dataclass
class ComparisonResult:
    """Result of strategy comparison."""
    strategies: List[StrategyMetrics]
    
    # Pairwise comparisons
    comparisons: Dict[str, Dict[str, Any]]
    
    # Rankings
    sharpe_ranking: List[str]
    pnl_ranking: List[str]
    risk_adjusted_ranking: List[str]
    
    # Best strategy
    best_overall: str
    
    def __str__(self) -> str:
        lines = [
            "",
            "╔══════════════════════════════════════════════════════════════════╗",
            "║                    STRATEGY COMPARISON                           ║",
            "╠══════════════════════════════════════════════════════════════════╣",
        ]
        
        # Header
        lines.append("║ {:20} {:>10} {:>10} {:>10} {:>10} ║".format(
            "Strategy", "Sharpe", "PnL", "MaxDD", "WinRate"
        ))
        lines.append("╠══════════════════════════════════════════════════════════════════╣")
        
        # Strategies
        for s in sorted(self.strategies, key=lambda x: x.sharpe, reverse=True):
            lines.append("║ {:20} {:>10.2f} {:>10.0f} {:>9.1f}% {:>9.1f}% ║".format(
                s.name[:20], s.sharpe, s.pnl, s.max_dd * 100, s.win_rate * 100
            ))
        
        lines.append("╠══════════════════════════════════════════════════════════════════╣")
        lines.append(f"║ 🏆 BEST OVERALL: {self.best_overall:45} ║")
        lines.append("╚══════════════════════════════════════════════════════════════════╝")
        
        # Statistical significance
        if self.comparisons:
            lines.append("\n📊 STATISTICAL SIGNIFICANCE (p-values):")
            for key, comp in self.comparisons.items():
                sig = "✅ SIGNIFICANT" if comp["significant"] else "❌ NOT SIGNIFICANT"
                lines.append(f"   {key}: p={comp['p_value']:.4f} {sig}")
        
        return "\n".join(lines)


class StrategyComparator:
    """
    Compare multiple trading strategies with statistical significance testing.
    
    Usage:
        comparator = StrategyComparator()
        
        # Add strategies
        comparator.add_strategy("DNA_v1", backtest_result_1)
        comparator.add_strategy("DNA_v2", backtest_result_2)
        
        # Compare
        result = comparator.compare()
        print(result)
    """
    
    def __init__(self, significance_level: float = 0.05):
        self.strategies: Dict[str, StrategyMetrics] = {}
        self.significance_level = significance_level
    
    def add_strategy(
        self,
        name: str,
        sharpe: float,
        pnl: float,
        pnl_pct: float,
        max_dd: float,
        win_rate: float,
        trade_count: int,
        profit_factor: float = 0.0,
        avg_trade: float = 0.0,
        daily_returns: Optional[List[float]] = None
    ) -> None:
        """Add a strategy for comparison."""
        self.strategies[name] = StrategyMetrics(
            name=name,
            sharpe=sharpe,
            pnl=pnl,
            pnl_pct=pnl_pct,
            max_dd=max_dd,
            win_rate=win_rate,
            trade_count=trade_count,
            profit_factor=profit_factor,
            avg_trade=avg_trade,
            daily_returns=daily_returns or [],
        )
    
    def add_from_backtest_report(self, name: str, report: Any) -> None:
        """Add strategy from BacktestReport object."""
        # Calculate daily returns from equity curve
        daily_returns = []
        if hasattr(report, "equity_curve") and len(report.equity_curve) > 1:
            eq = np.array(report.equity_curve)
            daily_returns = list(np.diff(eq) / eq[:-1])
        
        self.add_strategy(
            name=name,
            sharpe=getattr(report, "sharpe", 0),
            pnl=getattr(report, "total_pnl", 0),
            pnl_pct=getattr(report, "total_pnl_pct", 0),
            max_dd=getattr(report, "max_drawdown", 0),
            win_rate=getattr(report, "win_rate", 0),
            trade_count=getattr(report, "trade_count", 0),
            daily_returns=daily_returns,
        )
    
    def compare(self) -> ComparisonResult:
        """Run comparison and statistical tests."""
        if not self.strategies:
            raise ValueError("No strategies to compare")
        
        strategies = list(self.strategies.values())
        
        # Rankings
        sharpe_ranking = sorted(strategies, key=lambda x: x.sharpe, reverse=True)
        pnl_ranking = sorted(strategies, key=lambda x: x.pnl, reverse=True)
        
        # Risk-adjusted ranking (Sharpe / MaxDD)
        def risk_score(s):
            if s.max_dd == 0:
                return s.sharpe
            return s.sharpe / s.max_dd
        
        risk_ranking = sorted(strategies, key=risk_score, reverse=True)
        
        # Statistical comparisons (pairwise t-tests)
        comparisons = {}
        strategy_names = [s.name for s in strategies]
        
        for i, s1 in enumerate(strategies):
            for s2 in strategies[i + 1:]:
                if s1.daily_returns and s2.daily_returns:
                    # Welch's t-test for unequal variances
                    t_stat, p_value = stats.ttest_ind(
                        s1.daily_returns,
                        s2.daily_returns,
                        equal_var=False
                    )
                    
                    key = f"{s1.name} vs {s2.name}"
                    comparisons[key] = {
                        "t_statistic": float(t_stat),
                        "p_value": float(p_value),
                        "significant": p_value < self.significance_level,
                        "better": s1.name if np.mean(s1.daily_returns) > np.mean(s2.daily_returns) else s2.name,
                    }
        
        # Determine best overall using a composite score
        def composite_score(s):
            # Weighted combination
            sharpe_score = s.sharpe * 0.4
            dd_score = (1 - s.max_dd) * 0.3
            wr_score = s.win_rate * 0.2
            pnl_norm = np.sign(s.pnl) * np.log1p(abs(s.pnl)) / 10 * 0.1
            return sharpe_score + dd_score + wr_score + pnl_norm
        
        best_strategy = max(strategies, key=composite_score)
        
        return ComparisonResult(
            strategies=strategies,
            comparisons=comparisons,
            sharpe_ranking=[s.name for s in sharpe_ranking],
            pnl_ranking=[s.name for s in pnl_ranking],
            risk_adjusted_ranking=[s.name for s in risk_ranking],
            best_overall=best_strategy.name,
        )
    
    def compare_dna_configs(
        self,
        data: pd.DataFrame,
        backtest_fn: Callable[[pd.DataFrame, List[int]], Dict[str, float]],
        dna_configs: Dict[str, List[int]]
    ) -> ComparisonResult:
        """
        Compare multiple DNA configurations.
        
        Args:
            data: OHLCV data
            backtest_fn: Function(data, dna) -> {"sharpe":, "pnl":, ...}
            dna_configs: {"name": [dna_values], ...}
        """
        for name, dna in dna_configs.items():
            print(f"[COMPARE] Running backtest for {name}...")
            result = backtest_fn(data, dna)
            
            self.add_strategy(
                name=name,
                sharpe=result.get("sharpe", 0),
                pnl=result.get("pnl", 0),
                pnl_pct=result.get("pnl_pct", 0),
                max_dd=result.get("max_dd", 0),
                win_rate=result.get("win_rate", 0),
                trade_count=result.get("trade_count", 0),
                daily_returns=result.get("daily_returns", []),
            )
        
        return self.compare()


if __name__ == "__main__":
    # Demo
    print("Strategy Comparison Demo")
    print("=" * 50)
    
    comparator = StrategyComparator()
    
    # Add demo strategies
    np.random.seed(42)
    
    comparator.add_strategy(
        name="DNA_Conservative",
        sharpe=1.2,
        pnl=1500,
        pnl_pct=15.0,
        max_dd=0.08,
        win_rate=0.55,
        trade_count=150,
        daily_returns=list(np.random.normal(0.001, 0.01, 365)),
    )
    
    comparator.add_strategy(
        name="DNA_Aggressive",
        sharpe=1.8,
        pnl=3200,
        pnl_pct=32.0,
        max_dd=0.25,
        win_rate=0.48,
        trade_count=300,
        daily_returns=list(np.random.normal(0.002, 0.025, 365)),
    )
    
    comparator.add_strategy(
        name="DNA_Balanced",
        sharpe=1.5,
        pnl=2100,
        pnl_pct=21.0,
        max_dd=0.12,
        win_rate=0.52,
        trade_count=200,
        daily_returns=list(np.random.normal(0.0015, 0.015, 365)),
    )
    
    result = comparator.compare()
    print(result)
