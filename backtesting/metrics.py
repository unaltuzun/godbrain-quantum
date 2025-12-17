"""
GODBRAIN Performance Metrics Calculator
Institutional-grade metrics for strategy evaluation.
"""

import numpy as np
import pandas as pd
from typing import List, Dict
from datetime import timedelta


class MetricsCalculator:
    """
    Calculate comprehensive performance metrics.
    
    Metrics included:
    - Returns: Total, Annualized, Monthly
    - Risk: Volatility, Downside Vol, VaR, CVaR
    - Risk-Adjusted: Sharpe, Sortino, Calmar
    - Trade: Win Rate, Profit Factor, Expectancy
    - Drawdown: Max DD, DD Duration, Recovery
    """
    
    TRADING_DAYS = 365  # Crypto trades 24/7
    RISK_FREE_RATE = 0.05  # 5% annual
    
    def calculate_all(
        self,
        equity_curve: pd.Series,
        returns: pd.Series,
        trades: List,
        initial_capital: float
    ) -> Dict:
        """Calculate all metrics."""
        
        result = {}
        
        # Returns
        result['total_return'] = (equity_curve.iloc[-1] / initial_capital) - 1
        result['annualized_return'] = self._annualized_return(returns)
        
        # Volatility
        result['volatility'] = self._volatility(returns)
        
        # Drawdown
        dd_info = self._drawdown_analysis(equity_curve)
        result['max_drawdown'] = dd_info['max_drawdown']
        result['max_drawdown_duration'] = dd_info['max_duration']
        
        # Risk-adjusted returns
        result['sharpe_ratio'] = self._sharpe_ratio(returns)
        result['sortino_ratio'] = self._sortino_ratio(returns)
        result['calmar_ratio'] = self._calmar_ratio(
            result['annualized_return'],
            result['max_drawdown']
        )
        
        # VaR
        result['var_95'] = self._var(returns, 0.95)
        result['cvar_95'] = self._cvar(returns, 0.95)
        
        # Trade statistics
        trade_stats = self._trade_statistics(trades)
        result.update(trade_stats)
        
        # Final equity
        result['final_equity'] = equity_curve.iloc[-1]
        
        return result
    
    def _annualized_return(self, returns: pd.Series) -> float:
        """Calculate annualized return."""
        if len(returns) == 0:
            return 0.0
        total_return = (1 + returns).prod() - 1
        years = len(returns) / self.TRADING_DAYS
        if years <= 0:
            return 0.0
        return (1 + total_return) ** (1 / years) - 1
    
    def _volatility(self, returns: pd.Series) -> float:
        """Calculate annualized volatility."""
        if len(returns) == 0:
            return 0.0
        return returns.std() * np.sqrt(self.TRADING_DAYS)
    
    def _downside_volatility(self, returns: pd.Series) -> float:
        """Calculate downside volatility (only negative returns)."""
        negative_returns = returns[returns < 0]
        if len(negative_returns) == 0:
            return 0.0
        return negative_returns.std() * np.sqrt(self.TRADING_DAYS)
    
    def _sharpe_ratio(self, returns: pd.Series) -> float:
        """Calculate Sharpe Ratio."""
        if len(returns) == 0:
            return 0.0
        excess_return = self._annualized_return(returns) - self.RISK_FREE_RATE
        vol = self._volatility(returns)
        if vol == 0:
            return 0.0
        return excess_return / vol
    
    def _sortino_ratio(self, returns: pd.Series) -> float:
        """Calculate Sortino Ratio (uses downside volatility)."""
        if len(returns) == 0:
            return 0.0
        excess_return = self._annualized_return(returns) - self.RISK_FREE_RATE
        downside_vol = self._downside_volatility(returns)
        if downside_vol == 0:
            return 0.0
        return excess_return / downside_vol
    
    def _calmar_ratio(self, annualized_return: float, max_drawdown: float) -> float:
        """Calculate Calmar Ratio."""
        if max_drawdown == 0:
            return 0.0
        return annualized_return / abs(max_drawdown)
    
    def _drawdown_analysis(self, equity_curve: pd.Series) -> Dict:
        """Analyze drawdown characteristics."""
        peak = equity_curve.expanding().max()
        drawdown = (equity_curve - peak) / peak
        
        max_dd = drawdown.min()
        
        # Find longest underwater period
        is_underwater = drawdown < 0
        underwater_periods = []
        current_start = None
        
        for i, underwater in enumerate(is_underwater):
            if underwater and current_start is None:
                current_start = equity_curve.index[i]
            elif not underwater and current_start is not None:
                underwater_periods.append(
                    equity_curve.index[i] - current_start
                )
                current_start = None
        
        max_duration = max(underwater_periods) if underwater_periods else timedelta(0)
        
        return {
            'max_drawdown': max_dd,
            'max_duration': max_duration,
            'drawdown_series': drawdown
        }
    
    def _var(self, returns: pd.Series, confidence: float = 0.95) -> float:
        """Calculate Value at Risk."""
        if len(returns) == 0:
            return 0.0
        return np.percentile(returns, (1 - confidence) * 100)
    
    def _cvar(self, returns: pd.Series, confidence: float = 0.95) -> float:
        """Calculate Conditional Value at Risk (Expected Shortfall)."""
        if len(returns) == 0:
            return 0.0
        var = self._var(returns, confidence)
        tail_returns = returns[returns <= var]
        return tail_returns.mean() if len(tail_returns) > 0 else var
    
    def _trade_statistics(self, trades: List) -> Dict:
        """Calculate trade statistics."""
        if not trades:
            return {
                'total_trades': 0,
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'average_win': 0.0,
                'average_loss': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
                'total_fees': 0.0,
                'total_slippage': 0.0
            }
        
        # Filter exit trades (which have PnL)
        exit_trades = [t for t in trades if hasattr(t, 'pnl') and t.pnl is not None]
        
        if not exit_trades:
            return {
                'total_trades': len(trades),
                'winning_trades': 0,
                'losing_trades': 0,
                'win_rate': 0.0,
                'profit_factor': 0.0,
                'average_win': 0.0,
                'average_loss': 0.0,
                'largest_win': 0.0,
                'largest_loss': 0.0,
                'total_fees': sum(t.fee for t in trades),
                'total_slippage': 0.0
            }
        
        pnls = [t.pnl for t in exit_trades]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        
        total_wins = sum(wins) if wins else 0
        total_losses = abs(sum(losses)) if losses else 0
        
        return {
            'total_trades': len(exit_trades),
            'winning_trades': len(wins),
            'losing_trades': len(losses),
            'win_rate': len(wins) / len(exit_trades) if exit_trades else 0,
            'profit_factor': total_wins / total_losses if total_losses > 0 else float('inf'),
            'average_win': np.mean(wins) if wins else 0,
            'average_loss': np.mean(losses) if losses else 0,
            'largest_win': max(wins) if wins else 0,
            'largest_loss': min(losses) if losses else 0,
            'total_fees': sum(t.fee for t in trades),
            'total_slippage': sum(getattr(t, 'slippage', 0) for t in trades)
        }
