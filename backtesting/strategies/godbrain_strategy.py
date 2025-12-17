"""
GODBRAIN Strategy for Backtesting
Integrates Physics Lab DNA with backtesting engine.
"""

import numpy as np
import json
from pathlib import Path
from typing import Optional, List, Dict
import redis
import os

from ..engine import Strategy, BacktestContext


class GODBRAINStrategy(Strategy):
    """
    Strategy using GODBRAIN Physics Lab DNA.
    
    Reads evolved DNA from genome vault and uses it for trading decisions.
    
    Parameters:
        dna_source: Path to DNA file, "redis", or "latest"
        rsi_period: RSI indicator period
        rsi_oversold: RSI oversold threshold
        rsi_overbought: RSI overbought threshold
        atr_period: ATR period for stops
        atr_multiplier: ATR multiplier for stop-loss
    """
    
    def __init__(
        self,
        dna_source: str = "redis",
        rsi_period: int = 14,
        rsi_oversold: float = 30,
        rsi_overbought: float = 70,
        atr_period: int = 14,
        atr_multiplier: float = 2.0,
        base_position_size: float = 0.1
    ):
        self.dna_source = dna_source
        self.rsi_period = rsi_period
        self.rsi_oversold = rsi_oversold
        self.rsi_overbought = rsi_overbought
        self.atr_period = atr_period
        self.atr_multiplier = atr_multiplier
        self.base_position_size = base_position_size
        
        self.dna = None
        self.symbols = []
    
    def init(self, context: BacktestContext) -> None:
        """Initialize strategy."""
        self.symbols = list(context.data.keys())
        self._load_dna()
        
        print(f"[GODBRAIN Strategy] Symbols: {self.symbols}")
        if self.dna:
            print(f"[GODBRAIN Strategy] DNA: {self.dna.get('source', 'unknown')}")
    
    def _load_dna(self) -> None:
        """Load DNA from source."""
        try:
            if self.dna_source == "redis":
                self._load_from_redis()
            elif self.dna_source == "latest":
                self._load_from_file()
            else:
                # Load from specific file
                with open(self.dna_source) as f:
                    self.dna = json.load(f)
        except Exception as e:
            print(f"[GODBRAIN Strategy] DNA load error: {e}, using defaults")
            self.dna = self._default_dna()
    
    def _load_from_redis(self) -> None:
        """Load DNA from Redis."""
        try:
            r = redis.Redis(
                host=os.getenv("REDIS_HOST", "127.0.0.1"),
                port=int(os.getenv("REDIS_PORT", "16379")),
                password=os.getenv("REDIS_PASS", "voltran2024"),
                decode_responses=True
            )
            
            # Try active DNA first
            active = r.get("godbrain:trading:active_dna")
            if active:
                self.dna = json.loads(active)
                return
            
            # Fallback to best DNA
            best = r.get("godbrain:genetics:best_dna")
            if best:
                self.dna = {"dna": json.loads(best), "source": "genetics"}
                return
            
            self.dna = self._default_dna()
        except Exception as e:
            print(f"[GODBRAIN Strategy] Redis error: {e}")
            self.dna = self._default_dna()
    
    def _load_from_file(self) -> None:
        """Load DNA from file."""
        paths = [
            Path("quantum_lab/lab_state.json"),
            Path("genetics/best_dna.json")
        ]
        
        for path in paths:
            if path.exists():
                with open(path) as f:
                    self.dna = json.load(f)
                return
        
        self.dna = self._default_dna()
    
    def _default_dna(self) -> Dict:
        """Default DNA configuration."""
        return {
            'source': 'default',
            'dna': [10, 258, 394, 458, 476, 500],
            'score': 50.0
        }
    
    def _get_position_size(self) -> float:
        """Calculate position size based on DNA score."""
        score = self.dna.get('score', 50) if self.dna else 50
        
        # Higher score = larger positions allowed
        score_factor = min(score / 100, 1.0)
        size = self.base_position_size * (0.5 + score_factor * 0.5)
        
        return min(max(size, 0.05), 0.25)
    
    def next(self, context: BacktestContext) -> Optional[List[Dict]]:
        """Generate trading signals."""
        signals = []
        
        for symbol in self.symbols:
            signal = self._analyze_symbol(context, symbol)
            if signal:
                signals.append(signal)
        
        return signals if signals else None
    
    def _analyze_symbol(self, context: BacktestContext, symbol: str) -> Optional[Dict]:
        """Analyze single symbol for trading signal."""
        try:
            rsi = context.get_indicator(symbol, 'rsi', period=self.rsi_period)
            atr = context.get_indicator(symbol, 'atr', period=self.atr_period)
        except Exception:
            return None
        
        if rsi is None or len(rsi) < 2 or rsi.iloc[-1] != rsi.iloc[-1]:  # NaN check
            return None
        
        current_rsi = rsi.iloc[-1]
        current_atr = atr.iloc[-1] if atr is not None and len(atr) > 0 else 0
        current_price = context.get_price(symbol)
        
        has_position = symbol in context.positions
        
        if not has_position:
            # Entry signals
            if current_rsi < self.rsi_oversold:
                return {
                    'action': 'BUY',
                    'symbol': symbol,
                    'size': self._get_position_size(),
                    'order_type': 'market',
                    'stop_loss': current_price - (current_atr * self.atr_multiplier) if current_atr else None,
                    'take_profit': current_price + (current_atr * self.atr_multiplier * 2) if current_atr else None
                }
            
            elif current_rsi > self.rsi_overbought:
                return {
                    'action': 'SELL',
                    'symbol': symbol,
                    'size': self._get_position_size(),
                    'order_type': 'market',
                    'stop_loss': current_price + (current_atr * self.atr_multiplier) if current_atr else None,
                    'take_profit': current_price - (current_atr * self.atr_multiplier * 2) if current_atr else None
                }
        else:
            # Exit signals
            position = context.positions[symbol]
            
            if position.side == 'long' and current_rsi > 70:
                return {'action': 'CLOSE', 'symbol': symbol}
            
            if position.side == 'short' and current_rsi < 30:
                return {'action': 'CLOSE', 'symbol': symbol}
        
        return None
    
    def on_trade(self, context: BacktestContext, trade) -> None:
        """Log trade execution."""
        pnl_str = f" PnL: ${trade.pnl:.2f}" if trade.pnl else ""
        print(f"[TRADE] {trade.side.upper()} {trade.symbol} @ ${trade.price:.2f}{pnl_str}")
    
    def on_end(self, context: BacktestContext) -> None:
        """End of backtest."""
        print(f"[GODBRAIN Strategy] Complete | Final: ${context.equity:,.2f}")
