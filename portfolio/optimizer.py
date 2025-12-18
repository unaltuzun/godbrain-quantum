# -*- coding: utf-8 -*-
"""
📊 PORTFOLIO OPTIMIZER - Markowitz, Kelly, Risk Parity
Optimal portfolio allocation algorithms.
"""

import numpy as np
from typing import Dict, List, Optional
from dataclasses import dataclass
from datetime import datetime


@dataclass
class OptimizationResult:
    weights: Dict[str, float]
    expected_return: float
    expected_volatility: float
    sharpe_ratio: float
    method: str
    timestamp: datetime


class PortfolioOptimizer:
    """
    Portfolio optimization using various methods:
    - Mean-Variance (Markowitz)
    - Minimum Variance
    - Maximum Sharpe
    - Kelly Criterion
    - Risk Parity
    """
    
    def __init__(self, risk_free_rate: float = 0.05):
        self.risk_free_rate = risk_free_rate
    
    def mean_variance(self, returns: np.ndarray, symbols: List[str], 
                      target_return: Optional[float] = None) -> OptimizationResult:
        """
        Markowitz mean-variance optimization.
        
        Args:
            returns: NxM array of returns (N samples, M assets)
            symbols: List of asset symbols
            target_return: Target return (if None, maximize Sharpe)
        """
        n_assets = returns.shape[1]
        
        # Calculate expected returns and covariance
        mean_returns = np.mean(returns, axis=0)
        cov_matrix = np.cov(returns.T)
        
        # Simple optimization - equal risk contribution as starting point
        if target_return is None:
            weights = self._max_sharpe_weights(mean_returns, cov_matrix)
        else:
            weights = self._target_return_weights(mean_returns, cov_matrix, target_return)
        
        # Calculate metrics
        portfolio_return = np.dot(weights, mean_returns)
        portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        sharpe = (portfolio_return - self.risk_free_rate) / portfolio_vol
        
        return OptimizationResult(
            weights={sym: w for sym, w in zip(symbols, weights)},
            expected_return=float(portfolio_return),
            expected_volatility=float(portfolio_vol),
            sharpe_ratio=float(sharpe),
            method="mean_variance",
            timestamp=datetime.now()
        )
    
    def _max_sharpe_weights(self, mean_returns: np.ndarray, cov_matrix: np.ndarray) -> np.ndarray:
        """Calculate maximum Sharpe ratio weights."""
        n = len(mean_returns)
        
        # Excess returns
        excess = mean_returns - self.risk_free_rate
        
        # Solve for optimal weights
        try:
            inv_cov = np.linalg.inv(cov_matrix)
            weights = np.dot(inv_cov, excess)
            weights = weights / np.sum(weights)  # Normalize
            weights = np.maximum(weights, 0)  # No short selling
            weights = weights / np.sum(weights)  # Re-normalize
        except:
            weights = np.ones(n) / n
        
        return weights
    
    def _target_return_weights(self, mean_returns: np.ndarray, 
                                cov_matrix: np.ndarray, target: float) -> np.ndarray:
        """Calculate weights for target return with minimum variance."""
        n = len(mean_returns)
        
        # Simple approach: interpolate between min variance and max return
        min_var_weights = self.min_variance_weights(cov_matrix)
        max_ret_weights = np.zeros(n)
        max_ret_weights[np.argmax(mean_returns)] = 1.0
        
        min_ret = np.dot(min_var_weights, mean_returns)
        max_ret = np.max(mean_returns)
        
        if max_ret == min_ret:
            return min_var_weights
        
        alpha = (target - min_ret) / (max_ret - min_ret)
        alpha = np.clip(alpha, 0, 1)
        
        weights = (1 - alpha) * min_var_weights + alpha * max_ret_weights
        return weights
    
    def min_variance(self, returns: np.ndarray, symbols: List[str]) -> OptimizationResult:
        """Minimum variance portfolio."""
        cov_matrix = np.cov(returns.T)
        mean_returns = np.mean(returns, axis=0)
        
        weights = self.min_variance_weights(cov_matrix)
        
        portfolio_return = np.dot(weights, mean_returns)
        portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        sharpe = (portfolio_return - self.risk_free_rate) / portfolio_vol
        
        return OptimizationResult(
            weights={sym: w for sym, w in zip(symbols, weights)},
            expected_return=float(portfolio_return),
            expected_volatility=float(portfolio_vol),
            sharpe_ratio=float(sharpe),
            method="min_variance",
            timestamp=datetime.now()
        )
    
    def min_variance_weights(self, cov_matrix: np.ndarray) -> np.ndarray:
        """Calculate minimum variance weights."""
        n = cov_matrix.shape[0]
        try:
            inv_cov = np.linalg.inv(cov_matrix)
            ones = np.ones(n)
            weights = np.dot(inv_cov, ones) / np.dot(ones, np.dot(inv_cov, ones))
            weights = np.maximum(weights, 0)
            weights = weights / np.sum(weights)
        except:
            weights = np.ones(n) / n
        return weights
    
    def max_sharpe(self, returns: np.ndarray, symbols: List[str]) -> OptimizationResult:
        """Maximum Sharpe ratio portfolio."""
        return self.mean_variance(returns, symbols, target_return=None)
    
    def kelly_criterion(self, win_rate: float, win_loss_ratio: float) -> float:
        """
        Kelly Criterion for optimal bet sizing.
        
        f* = (p * b - q) / b
        where:
        - p = win probability
        - q = loss probability (1 - p)
        - b = win/loss ratio
        
        Returns:
            Optimal fraction of capital to bet
        """
        p = win_rate
        q = 1 - win_rate
        b = win_loss_ratio
        
        if b <= 0:
            return 0
        
        kelly = (p * b - q) / b
        return max(0, min(kelly, 1))  # Clamp to [0, 1]
    
    def risk_parity(self, returns: np.ndarray, symbols: List[str]) -> OptimizationResult:
        """
        Risk parity - each asset contributes equally to portfolio risk.
        """
        cov_matrix = np.cov(returns.T)
        mean_returns = np.mean(returns, axis=0)
        n = len(symbols)
        
        # Simplified risk parity: weight inversely to volatility
        vols = np.sqrt(np.diag(cov_matrix))
        inv_vols = 1 / vols
        weights = inv_vols / np.sum(inv_vols)
        
        portfolio_return = np.dot(weights, mean_returns)
        portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        sharpe = (portfolio_return - self.risk_free_rate) / portfolio_vol
        
        return OptimizationResult(
            weights={sym: w for sym, w in zip(symbols, weights)},
            expected_return=float(portfolio_return),
            expected_volatility=float(portfolio_vol),
            sharpe_ratio=float(sharpe),
            method="risk_parity",
            timestamp=datetime.now()
        )
    
    def black_litterman(self, returns: np.ndarray, symbols: List[str], 
                        views: Dict[str, float]) -> OptimizationResult:
        """
        Black-Litterman model with investor views.
        
        Args:
            views: Dict of symbol -> expected return view
        """
        # Simplified: blend market equilibrium with views
        cov_matrix = np.cov(returns.T)
        mean_returns = np.mean(returns, axis=0)
        n = len(symbols)
        
        # Adjust expected returns based on views
        adjusted_returns = mean_returns.copy()
        for i, sym in enumerate(symbols):
            if sym in views:
                # Blend: 50% market, 50% view
                adjusted_returns[i] = 0.5 * mean_returns[i] + 0.5 * views[sym]
        
        # Use adjusted returns for optimization
        weights = self._max_sharpe_weights(adjusted_returns, cov_matrix)
        
        portfolio_return = np.dot(weights, adjusted_returns)
        portfolio_vol = np.sqrt(np.dot(weights.T, np.dot(cov_matrix, weights)))
        sharpe = (portfolio_return - self.risk_free_rate) / portfolio_vol
        
        return OptimizationResult(
            weights={sym: w for sym, w in zip(symbols, weights)},
            expected_return=float(portfolio_return),
            expected_volatility=float(portfolio_vol),
            sharpe_ratio=float(sharpe),
            method="black_litterman",
            timestamp=datetime.now()
        )
