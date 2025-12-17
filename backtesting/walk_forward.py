"""
GODBRAIN Walk-Forward Optimization
Prevents overfitting through rolling out-of-sample validation.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Type
from datetime import datetime, timedelta
import itertools


@dataclass
class WalkForwardConfig:
    """Walk-forward optimization configuration."""
    
    in_sample_days: int = 90       # 3 months training
    out_sample_days: int = 30      # 1 month testing
    step_days: int = 30            # Move forward 1 month
    
    metric: str = "sharpe_ratio"   # Metric to optimize
    parameter_grid: Dict = field(default_factory=dict)
    
    min_trades: int = 20           # Minimum trades per window


@dataclass
class WalkForwardResult:
    """Walk-forward optimization result."""
    
    windows: List[Dict]
    aggregated_equity: pd.Series
    total_return: float
    sharpe_ratio: float
    parameter_stability: Dict
    robustness_score: float


class WalkForwardOptimizer:
    """
    Walk-forward analysis for robust strategy optimization.
    
    Process:
    1. Split data into windows (in-sample + out-sample)
    2. For each window:
       a. Optimize parameters on in-sample data
       b. Test with optimal params on out-sample data
    3. Aggregate out-of-sample results
    4. Calculate robustness metrics
    """
    
    def __init__(self, config: WalkForwardConfig):
        self.config = config
    
    async def run(
        self,
        strategy_class: Type,
        data: Dict[str, pd.DataFrame],
        backtest_config: 'BacktestConfig'
    ) -> WalkForwardResult:
        """Run walk-forward optimization."""
        from .engine import BacktestEngine, BacktestConfig
        
        first_symbol = list(data.keys())[0]
        start_date = data[first_symbol].index.min()
        end_date = data[first_symbol].index.max()
        
        windows = self._generate_windows(start_date, end_date)
        
        print(f"[WFO] Running {len(windows)} windows")
        print(f"[WFO] IS: {self.config.in_sample_days}d | OOS: {self.config.out_sample_days}d")
        
        results = []
        
        for i, window in enumerate(windows):
            print(f"\n[WFO] Window {i+1}/{len(windows)}")
            
            # Optimize on in-sample
            best_params, is_metric = await self._optimize_in_sample(
                strategy_class, data, window['is_start'], window['is_end'], backtest_config
            )
            
            print(f"[WFO] Best params: {best_params}, IS {self.config.metric}: {is_metric:.4f}")
            
            # Test on out-of-sample
            oos_result = await self._test_out_of_sample(
                strategy_class, data, window['oos_start'], window['oos_end'],
                backtest_config, best_params
            )
            
            print(f"[WFO] OOS {self.config.metric}: {getattr(oos_result, self.config.metric):.4f}")
            
            results.append({
                'window': window,
                'best_params': best_params,
                'is_metric': is_metric,
                'oos_result': oos_result
            })
        
        return self._aggregate_results(results)
    
    def _generate_windows(self, start_date: datetime, end_date: datetime) -> List[Dict]:
        """Generate walk-forward windows."""
        windows = []
        current = start_date
        
        while True:
            is_start = current
            is_end = is_start + timedelta(days=self.config.in_sample_days)
            oos_start = is_end
            oos_end = oos_start + timedelta(days=self.config.out_sample_days)
            
            if oos_end > end_date:
                break
            
            windows.append({
                'is_start': is_start,
                'is_end': is_end,
                'oos_start': oos_start,
                'oos_end': oos_end
            })
            
            current += timedelta(days=self.config.step_days)
        
        return windows
    
    async def _optimize_in_sample(
        self, strategy_class: Type, data: Dict, start: datetime, end: datetime,
        base_config: 'BacktestConfig'
    ) -> tuple:
        """Find optimal parameters on in-sample data."""
        from .engine import BacktestEngine, BacktestConfig
        
        best_params = {}
        best_metric = -np.inf
        
        param_names = list(self.config.parameter_grid.keys())
        param_values = list(self.config.parameter_grid.values())
        
        if not param_names:
            # No parameters to optimize
            config = BacktestConfig(
                start_date=start, end_date=end,
                initial_capital=base_config.initial_capital,
                timeframe=base_config.timeframe
            )
            engine = BacktestEngine(config)
            engine.set_data({k: v[(v.index >= start) & (v.index <= end)] for k, v in data.items()})
            engine.set_strategy(strategy_class())
            result = await engine.run()
            return {}, getattr(result, self.config.metric)
        
        for combo in itertools.product(*param_values):
            params = dict(zip(param_names, combo))
            
            config = BacktestConfig(
                start_date=start, end_date=end,
                initial_capital=base_config.initial_capital,
                timeframe=base_config.timeframe
            )
            
            engine = BacktestEngine(config)
            engine.set_data({k: v[(v.index >= start) & (v.index <= end)] for k, v in data.items()})
            
            try:
                strategy = strategy_class(**params)
                engine.set_strategy(strategy)
                result = await engine.run()
                metric_value = getattr(result, self.config.metric)
                
                if metric_value > best_metric and result.total_trades >= self.config.min_trades:
                    best_metric = metric_value
                    best_params = params
            except Exception as e:
                print(f"[WFO] Error with params {params}: {e}")
        
        return best_params, best_metric
    
    async def _test_out_of_sample(
        self, strategy_class: Type, data: Dict, start: datetime, end: datetime,
        base_config: 'BacktestConfig', params: Dict
    ) -> 'BacktestResult':
        """Test strategy on out-of-sample data."""
        from .engine import BacktestEngine, BacktestConfig
        
        config = BacktestConfig(
            start_date=start, end_date=end,
            initial_capital=base_config.initial_capital,
            timeframe=base_config.timeframe
        )
        
        engine = BacktestEngine(config)
        engine.set_data({k: v[(v.index >= start) & (v.index <= end)] for k, v in data.items()})
        
        strategy = strategy_class(**params) if params else strategy_class()
        engine.set_strategy(strategy)
        
        return await engine.run()
    
    def _aggregate_results(self, results: List[Dict]) -> WalkForwardResult:
        """Aggregate walk-forward results."""
        # Chain equity curves
        equity_curves = [r['oos_result'].equity_curve for r in results]
        
        aggregated = equity_curves[0].copy()
        for ec in equity_curves[1:]:
            scale = aggregated.iloc[-1] / ec.iloc[0]
            aggregated = pd.concat([aggregated, ec.iloc[1:] * scale])
        
        # Parameter stability
        all_params = [r['best_params'] for r in results if r['best_params']]
        stability = {}
        
        if all_params:
            for param in all_params[0].keys():
                values = [p.get(param) for p in all_params if p]
                if values and all(isinstance(v, (int, float)) for v in values):
                    stability[param] = {
                        'mean': np.mean(values),
                        'std': np.std(values),
                        'cv': np.std(values) / np.mean(values) if np.mean(values) != 0 else 0
                    }
        
        # Robustness score
        oos_metrics = [getattr(r['oos_result'], self.config.metric) for r in results]
        is_metrics = [r['is_metric'] for r in results]
        
        oos_consistency = 1 - (np.std(oos_metrics) / (np.mean(oos_metrics) + 1e-6))
        
        degradation = []
        for is_m, oos_m in zip(is_metrics, oos_metrics):
            if is_m > 0:
                degradation.append(oos_m / is_m)
        
        robustness = (max(0, oos_consistency) * 0.5 + min(np.mean(degradation) if degradation else 0, 1) * 0.5)
        
        total_return = (aggregated.iloc[-1] / aggregated.iloc[0]) - 1
        returns = aggregated.pct_change().dropna()
        sharpe = (returns.mean() / returns.std()) * np.sqrt(365) if returns.std() > 0 else 0
        
        return WalkForwardResult(
            windows=results,
            aggregated_equity=aggregated,
            total_return=total_return,
            sharpe_ratio=sharpe,
            parameter_stability=stability,
            robustness_score=robustness
        )
