#!/usr/bin/env python3
"""
GODBRAIN Backtesting - Run Script

Usage:
    python -m backtesting.run_backtest --symbols BTC/USDT ETH/USDT --days 365
    python -m backtesting.run_backtest --symbols BTC/USDT --days 180 --walk-forward
"""

import asyncio
import argparse
from datetime import datetime, timedelta

from .data_manager import HistoricalDataManager
from .engine import BacktestEngine, BacktestConfig
from .strategies.godbrain_strategy import GODBRAINStrategy
from .walk_forward import WalkForwardOptimizer, WalkForwardConfig


async def main():
    parser = argparse.ArgumentParser(description='GODBRAIN Backtesting')
    parser.add_argument('--symbols', nargs='+', default=['BTC/USDT'])
    parser.add_argument('--exchange', default='binance')
    parser.add_argument('--timeframe', default='1h')
    parser.add_argument('--days', type=int, default=180)
    parser.add_argument('--capital', type=float, default=10000)
    parser.add_argument('--walk-forward', action='store_true')
    
    args = parser.parse_args()
    
    end_date = datetime.now()
    start_date = end_date - timedelta(days=args.days)
    
    print("=" * 60)
    print("🧬 GODBRAIN QUANTUM BACKTESTING")
    print("=" * 60)
    print(f"Symbols: {args.symbols}")
    print(f"Period: {start_date.date()} to {end_date.date()}")
    print(f"Capital: ${args.capital:,.2f}")
    print("=" * 60)
    
    dm = HistoricalDataManager()
    
    # Download data
    for symbol in args.symbols:
        await dm.download(
            symbol=symbol,
            exchange=args.exchange,
            timeframe=args.timeframe,
            start_date=start_date,
            end_date=end_date
        )
    
    config = BacktestConfig(
        start_date=start_date,
        end_date=end_date,
        initial_capital=args.capital,
        timeframe=args.timeframe
    )
    
    if args.walk_forward:
        print("\n[MODE] Walk-Forward Optimization")
        
        wf_config = WalkForwardConfig(
            in_sample_days=90,
            out_sample_days=30,
            step_days=30,
            metric='sharpe_ratio',
            parameter_grid={
                'rsi_period': [7, 14, 21],
                'rsi_oversold': [25, 30, 35],
                'rsi_overbought': [65, 70, 75]
            }
        )
        
        optimizer = WalkForwardOptimizer(wf_config)
        
        data = {}
        for symbol in args.symbols:
            data[symbol] = await dm.load(symbol, args.timeframe, start_date, end_date)
        
        result = await optimizer.run(GODBRAINStrategy, data, config)
        
        print("\n" + "=" * 60)
        print("WALK-FORWARD RESULTS")
        print("=" * 60)
        print(f"Total Return: {result.total_return:.2%}")
        print(f"Sharpe Ratio: {result.sharpe_ratio:.2f}")
        print(f"Robustness Score: {result.robustness_score:.2%}")
        
    else:
        print("\n[MODE] Simple Backtest")
        
        engine = BacktestEngine(config)
        await engine.load_data(args.symbols, dm)
        
        strategy = GODBRAINStrategy()
        engine.set_strategy(strategy)
        
        result = await engine.run()
        print(result.summary())
        
        # Save results
        result.equity_curve.to_csv('reports/backtest_results/equity_curve.csv')
        print("\n[SAVED] Equity curve to reports/backtest_results/equity_curve.csv")


if __name__ == "__main__":
    asyncio.run(main())
