# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN Walk-Forward Optimization
Prevent overfitting through rolling train/test splits.
═══════════════════════════════════════════════════════════════════════════════
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Callable, Any, Optional, Tuple
from datetime import datetime


@dataclass
class WalkForwardWindow:
    """Single walk-forward window result."""
    window_id: int
    train_start: datetime
    train_end: datetime
    test_start: datetime
    test_end: datetime
    
    # Best params found in training
    best_params: Dict[str, Any]
    
    # Metrics
    train_sharpe: float
    train_pnl: float
    train_max_dd: float
    
    test_sharpe: float
    test_pnl: float
    test_max_dd: float
    
    # Overfitting indicator
    @property
    def degradation_ratio(self) -> float:
        """Ratio of test/train performance. < 1 indicates overfitting."""
        if self.train_sharpe == 0:
            return 0
        return self.test_sharpe / self.train_sharpe


@dataclass
class WalkForwardResult:
    """Aggregate walk-forward optimization results."""
    n_windows: int
    windows: List[WalkForwardWindow]
    
    # Aggregated test metrics (out-of-sample)
    oos_sharpe: float
    oos_pnl: float
    oos_max_dd: float
    oos_win_rate: float
    
    # Overfitting analysis
    avg_degradation: float  # Average test/train ratio
    overfit_windows: int  # Number of windows with > 30% degradation
    
    def to_dict(self) -> Dict:
        return {
            "n_windows": self.n_windows,
            "oos_sharpe": self.oos_sharpe,
            "oos_pnl": self.oos_pnl,
            "oos_max_dd": self.oos_max_dd,
            "avg_degradation": self.avg_degradation,
            "overfit_windows": self.overfit_windows,
            "windows": [
                {
                    "id": w.window_id,
                    "train": f"{w.train_start} to {w.train_end}",
                    "test": f"{w.test_start} to {w.test_end}",
                    "train_sharpe": w.train_sharpe,
                    "test_sharpe": w.test_sharpe,
                    "degradation": w.degradation_ratio,
                }
                for w in self.windows
            ]
        }
    
    def __str__(self) -> str:
        overfit_pct = (self.overfit_windows / self.n_windows * 100) if self.n_windows > 0 else 0
        degradation_warning = "⚠️ HIGH OVERFIT RISK" if self.avg_degradation < 0.7 else "✅ ACCEPTABLE"
        
        return f"""
╔══════════════════════════════════════════════════════════════════╗
║                   WALK-FORWARD OPTIMIZATION                      ║
╠══════════════════════════════════════════════════════════════════╣
║ Windows: {self.n_windows}                                                    
║                                                                  ║
║ OUT-OF-SAMPLE PERFORMANCE (Real Expected Performance)           ║
║   Sharpe: {self.oos_sharpe:.3f}                                             
║   PnL: ${self.oos_pnl:,.2f}                                           
║   Max DD: {self.oos_max_dd*100:.1f}%                                         
║                                                                  ║
║ OVERFITTING ANALYSIS                                             ║
║   Avg Train→Test Degradation: {self.avg_degradation:.1%}                     
║   Windows with >30% degradation: {self.overfit_windows}/{self.n_windows} ({overfit_pct:.0f}%)          
║   Status: {degradation_warning}                                  
╚══════════════════════════════════════════════════════════════════╝
"""


class WalkForwardOptimizer:
    """
    Walk-forward optimization framework.
    
    Splits data into rolling train/test windows to:
    1. Optimize parameters on training data
    2. Validate on unseen test data
    3. Detect overfitting via train/test performance gap
    
    Usage:
        optimizer = WalkForwardOptimizer(
            data=ohlcv_df,
            n_windows=5,
            train_pct=0.7
        )
        
        result = optimizer.run(
            objective_fn=backtest_with_params,
            param_grid={
                "dna_0": [5, 10, 15],
                "dna_1": [200, 300, 400],
            }
        )
    """
    
    def __init__(
        self,
        data: pd.DataFrame,
        n_windows: int = 5,
        train_pct: float = 0.7,
        gap_bars: int = 0  # Gap between train and test to avoid lookahead
    ):
        """
        Args:
            data: OHLCV DataFrame with timestamp column
            n_windows: Number of walk-forward windows
            train_pct: Fraction of each window for training
            gap_bars: Number of bars gap between train and test
        """
        self.data = data.copy()
        if "timestamp" in data.columns:
            self.data = self.data.sort_values("timestamp")
        
        self.n_windows = n_windows
        self.train_pct = train_pct
        self.gap_bars = gap_bars
        
        self._windows = self._create_windows()
    
    def _create_windows(self) -> List[Tuple[pd.DataFrame, pd.DataFrame]]:
        """Create train/test splits for each window."""
        n = len(self.data)
        window_size = n // self.n_windows
        
        windows = []
        for i in range(self.n_windows):
            start_idx = i * window_size
            end_idx = min((i + 1) * window_size, n)
            
            window_data = self.data.iloc[start_idx:end_idx]
            
            train_size = int(len(window_data) * self.train_pct)
            train_data = window_data.iloc[:train_size]
            test_data = window_data.iloc[train_size + self.gap_bars:]
            
            if len(train_data) > 0 and len(test_data) > 0:
                windows.append((train_data, test_data))
        
        return windows
    
    def run(
        self,
        objective_fn: Callable[[pd.DataFrame, Dict[str, Any]], Dict[str, float]],
        param_grid: Dict[str, List[Any]],
        metric: str = "sharpe"
    ) -> WalkForwardResult:
        """
        Run walk-forward optimization.
        
        Args:
            objective_fn: Function that takes (data, params) and returns 
                          {"sharpe": x, "pnl": y, "max_dd": z}
            param_grid: Parameter grid to search
            metric: Metric to optimize ("sharpe", "pnl", "max_dd")
        
        Returns:
            WalkForwardResult with aggregated metrics
        """
        from itertools import product
        
        # Generate all parameter combinations
        param_names = list(param_grid.keys())
        param_values = list(param_grid.values())
        param_combos = [dict(zip(param_names, combo)) for combo in product(*param_values)]
        
        window_results: List[WalkForwardWindow] = []
        all_test_pnls = []
        
        for window_id, (train_data, test_data) in enumerate(self._windows):
            print(f"[WF] Window {window_id + 1}/{self.n_windows}")
            
            # Find best params on training data
            best_params = None
            best_train_metric = float("-inf")
            best_train_result = {"sharpe": 0, "pnl": 0, "max_dd": 0}
            
            for params in param_combos:
                try:
                    result = objective_fn(train_data, params)
                    metric_val = result.get(metric, 0)
                    
                    if metric_val > best_train_metric:
                        best_train_metric = metric_val
                        best_params = params
                        best_train_result = result
                except Exception as e:
                    continue
            
            if best_params is None:
                best_params = param_combos[0] if param_combos else {}
            
            # Evaluate on test data
            try:
                test_result = objective_fn(test_data, best_params)
            except Exception:
                test_result = {"sharpe": 0, "pnl": 0, "max_dd": 0}
            
            # Get timestamps
            train_start = train_data["timestamp"].iloc[0] if "timestamp" in train_data.columns else datetime.now()
            train_end = train_data["timestamp"].iloc[-1] if "timestamp" in train_data.columns else datetime.now()
            test_start = test_data["timestamp"].iloc[0] if "timestamp" in test_data.columns else datetime.now()
            test_end = test_data["timestamp"].iloc[-1] if "timestamp" in test_data.columns else datetime.now()
            
            window_result = WalkForwardWindow(
                window_id=window_id,
                train_start=train_start,
                train_end=train_end,
                test_start=test_start,
                test_end=test_end,
                best_params=best_params,
                train_sharpe=best_train_result.get("sharpe", 0),
                train_pnl=best_train_result.get("pnl", 0),
                train_max_dd=best_train_result.get("max_dd", 0),
                test_sharpe=test_result.get("sharpe", 0),
                test_pnl=test_result.get("pnl", 0),
                test_max_dd=test_result.get("max_dd", 0),
            )
            
            window_results.append(window_result)
            all_test_pnls.append(test_result.get("pnl", 0))
        
        # Aggregate results
        test_sharpes = [w.test_sharpe for w in window_results]
        test_pnls = [w.test_pnl for w in window_results]
        test_dds = [w.test_max_dd for w in window_results]
        degradations = [w.degradation_ratio for w in window_results if w.degradation_ratio > 0]
        
        overfit_count = sum(1 for w in window_results if w.degradation_ratio < 0.7)
        
        return WalkForwardResult(
            n_windows=len(window_results),
            windows=window_results,
            oos_sharpe=float(np.mean(test_sharpes)) if test_sharpes else 0,
            oos_pnl=float(np.sum(test_pnls)),
            oos_max_dd=float(np.max(test_dds)) if test_dds else 0,
            oos_win_rate=sum(1 for p in test_pnls if p > 0) / len(test_pnls) if test_pnls else 0,
            avg_degradation=float(np.mean(degradations)) if degradations else 1.0,
            overfit_windows=overfit_count,
        )


# Demo objective function
def demo_objective(data: pd.DataFrame, params: Dict[str, Any]) -> Dict[str, float]:
    """Demo objective function for testing."""
    import random
    
    # Simulate backtest result based on params
    base_sharpe = 0.5
    param_boost = sum(params.values()) / 1000
    noise = random.gauss(0, 0.2)
    
    sharpe = base_sharpe + param_boost + noise
    pnl = sharpe * 100 + random.gauss(0, 50)
    max_dd = abs(random.gauss(0.1, 0.05))
    
    return {"sharpe": sharpe, "pnl": pnl, "max_dd": max_dd}


if __name__ == "__main__":
    # Demo
    print("Walk-Forward Optimization Demo")
    print("=" * 50)
    
    # Create synthetic data
    dates = pd.date_range(start="2023-01-01", periods=1000, freq="1h")
    demo_data = pd.DataFrame({
        "timestamp": dates,
        "close": np.cumsum(np.random.randn(1000)) + 100,
    })
    
    optimizer = WalkForwardOptimizer(demo_data, n_windows=5, train_pct=0.7)
    
    result = optimizer.run(
        objective_fn=demo_objective,
        param_grid={
            "dna_0": [5, 10, 15],
            "dna_1": [200, 300],
        }
    )
    
    print(result)
