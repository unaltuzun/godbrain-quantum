"""
GODBRAIN Institutional Backtesting Framework

Features:
- Multi-exchange historical data (Binance, OKX, Bybit)
- Realistic execution modeling (fees, slippage)
- Institutional metrics (Sharpe, Sortino, VaR, CVaR)
- Walk-forward optimization (anti-overfitting)
- GODBRAIN DNA/genetics integration

Usage:
    from backtesting import BacktestEngine, BacktestConfig, GODBRAINStrategy
    
    config = BacktestConfig(start_date, end_date, initial_capital=10000)
    engine = BacktestEngine(config)
    await engine.load_data(['BTC/USDT'])
    engine.set_strategy(GODBRAINStrategy())
    result = await engine.run()
    print(result.summary())
"""

from .engine import BacktestEngine, BacktestConfig, BacktestResult, Strategy, BacktestContext
from .data_manager import HistoricalDataManager
from .metrics import MetricsCalculator
from .walk_forward import WalkForwardOptimizer, WalkForwardConfig, WalkForwardResult
from .strategies import GODBRAINStrategy

__all__ = [
    'BacktestEngine',
    'BacktestConfig',
    'BacktestResult',
    'BacktestContext',
    'Strategy',
    'HistoricalDataManager',
    'MetricsCalculator',
    'WalkForwardOptimizer',
    'WalkForwardConfig',
    'WalkForwardResult',
    'GODBRAINStrategy'
]

__version__ = '1.0.0'
