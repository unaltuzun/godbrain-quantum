"""
GODBRAIN Backtesting Engine
Professional-grade backtesting with realistic execution modeling.
"""

import numpy as np
import pandas as pd
from dataclasses import dataclass, field
from typing import List, Dict, Optional, Tuple
from datetime import datetime, timedelta
from abc import ABC, abstractmethod

from .models.trade import Trade, TradeType
from .models.position import Position
from .metrics import MetricsCalculator
from .utils.fee_models import TieredFeeModel
from .utils.slippage_models import VolumeSlippageModel


@dataclass
class BacktestConfig:
    """Backtest configuration."""
    
    # Time range
    start_date: datetime
    end_date: datetime
    
    # Capital
    initial_capital: float = 10000.0
    
    # Costs
    maker_fee: float = 0.0002      # 0.02%
    taker_fee: float = 0.0005      # 0.05%
    slippage_pct: float = 0.0001   # 0.01%
    
    # Execution
    fill_model: str = "realistic"   # immediate, realistic, pessimistic
    partial_fills: bool = True
    
    # Risk limits
    max_position_pct: float = 0.25  # 25% of capital per position
    max_drawdown_pct: float = 0.20  # Stop if 20% drawdown
    
    # Data
    timeframe: str = "1h"
    
    # Leverage
    use_leverage: bool = True
    max_leverage: int = 10


@dataclass
class BacktestState:
    """Current state during backtest."""
    
    timestamp: datetime = None
    equity: float = 0.0
    cash: float = 0.0
    positions: Dict[str, Position] = field(default_factory=dict)
    trades: List[Trade] = field(default_factory=list)
    
    # Tracking
    equity_curve: List[Tuple[datetime, float]] = field(default_factory=list)
    peak_equity: float = 0.0
    current_drawdown: float = 0.0


class Strategy(ABC):
    """
    Abstract base class for trading strategies.
    
    Implement this class to create your own strategy.
    """
    
    @abstractmethod
    def init(self, context: 'BacktestContext') -> None:
        """Called once at the start of backtest."""
        pass
    
    @abstractmethod
    def next(self, context: 'BacktestContext') -> Optional[List[Dict]]:
        """
        Called on each new bar.
        
        Returns:
            List of signal dicts:
            [{"action": "BUY"|"SELL"|"CLOSE", "symbol": str, "size": float, ...}]
        """
        pass
    
    def on_trade(self, context: 'BacktestContext', trade: Trade) -> None:
        """Called when a trade is executed."""
        pass
    
    def on_end(self, context: 'BacktestContext') -> None:
        """Called at end of backtest."""
        pass


class BacktestContext:
    """Context object passed to strategy."""
    
    def __init__(
        self,
        data: Dict[str, pd.DataFrame],
        state: BacktestState,
        config: BacktestConfig
    ):
        self.data = data
        self.state = state
        self.config = config
        self._current_idx = 0
    
    @property
    def timestamp(self) -> datetime:
        return self.state.timestamp
    
    @property
    def equity(self) -> float:
        return self.state.equity
    
    @property
    def cash(self) -> float:
        return self.state.cash
    
    @property
    def positions(self) -> Dict[str, Position]:
        return self.state.positions
    
    def get_price(self, symbol: str) -> float:
        """Get current close price for symbol."""
        return self.data[symbol].iloc[self._current_idx]['close']
    
    def get_ohlcv(self, symbol: str, lookback: int = 100) -> pd.DataFrame:
        """Get OHLCV data for symbol with lookback."""
        start_idx = max(0, self._current_idx - lookback)
        return self.data[symbol].iloc[start_idx:self._current_idx + 1]
    
    def get_indicator(self, symbol: str, indicator: str, **kwargs) -> pd.Series:
        """
        Calculate and return indicator values.
        
        Supported: sma, ema, rsi, macd, bbands, atr
        """
        df = self.get_ohlcv(symbol, lookback=kwargs.get('period', 14) * 3)
        
        if indicator == 'sma':
            return df['close'].rolling(kwargs['period']).mean()
        
        elif indicator == 'ema':
            return df['close'].ewm(span=kwargs['period']).mean()
        
        elif indicator == 'rsi':
            delta = df['close'].diff()
            gain = (delta.where(delta > 0, 0)).rolling(kwargs['period']).mean()
            loss = (-delta.where(delta < 0, 0)).rolling(kwargs['period']).mean()
            rs = gain / loss
            return 100 - (100 / (1 + rs))
        
        elif indicator == 'atr':
            high = df['high']
            low = df['low']
            close = df['close'].shift(1)
            tr = pd.concat([
                high - low,
                (high - close).abs(),
                (low - close).abs()
            ], axis=1).max(axis=1)
            return tr.rolling(kwargs['period']).mean()
        
        elif indicator == 'macd':
            fast = df['close'].ewm(span=kwargs.get('fast', 12)).mean()
            slow = df['close'].ewm(span=kwargs.get('slow', 26)).mean()
            macd = fast - slow
            signal = macd.ewm(span=kwargs.get('signal', 9)).mean()
            return pd.DataFrame({'macd': macd, 'signal': signal, 'histogram': macd - signal})
        
        elif indicator == 'bbands':
            period = kwargs.get('period', 20)
            std = kwargs.get('std', 2)
            sma = df['close'].rolling(period).mean()
            rolling_std = df['close'].rolling(period).std()
            return pd.DataFrame({
                'upper': sma + (rolling_std * std),
                'middle': sma,
                'lower': sma - (rolling_std * std)
            })
        
        else:
            raise ValueError(f"Unknown indicator: {indicator}")


class BacktestEngine:
    """
    Core backtesting engine.
    
    Features:
    - Realistic execution modeling (fees, slippage)
    - Multiple position management
    - Stop-loss and take-profit handling
    - Equity curve tracking
    - Drawdown monitoring
    """
    
    def __init__(self, config: BacktestConfig):
        self.config = config
        self.data: Dict[str, pd.DataFrame] = {}
        self.strategy: Optional[Strategy] = None
        self.state: Optional[BacktestState] = None
        self.metrics_calc = MetricsCalculator()
        
        # Fee and slippage models
        self.fee_model = TieredFeeModel(
            maker_fee=config.maker_fee,
            taker_fee=config.taker_fee
        )
        self.slippage_model = VolumeSlippageModel(
            base_slippage=config.slippage_pct
        )
    
    async def load_data(
        self,
        symbols: List[str],
        data_manager: 'HistoricalDataManager' = None
    ) -> None:
        """Load historical data for all symbols."""
        from .data_manager import HistoricalDataManager
        
        dm = data_manager or HistoricalDataManager()
        
        for symbol in symbols:
            print(f"[BACKTEST] Loading {symbol}...")
            df = await dm.load(
                symbol,
                self.config.timeframe,
                self.config.start_date,
                self.config.end_date
            )
            self.data[symbol] = df
            print(f"[BACKTEST] Loaded {len(df)} bars for {symbol}")
    
    def set_strategy(self, strategy: Strategy) -> None:
        """Set the strategy to backtest."""
        self.strategy = strategy
    
    def set_data(self, data: Dict[str, pd.DataFrame]) -> None:
        """Set data directly (for walk-forward)."""
        self.data = data
    
    async def run(self) -> 'BacktestResult':
        """Run the backtest."""
        if not self.strategy:
            raise ValueError("No strategy set")
        
        if not self.data:
            raise ValueError("No data loaded")
        
        # Initialize state
        self.state = BacktestState(
            cash=self.config.initial_capital,
            equity=self.config.initial_capital,
            peak_equity=self.config.initial_capital
        )
        
        # Get common index
        common_index = None
        for symbol, df in self.data.items():
            if common_index is None:
                common_index = df.index
            else:
                common_index = common_index.intersection(df.index)
        
        context = BacktestContext(self.data, self.state, self.config)
        self.strategy.init(context)
        
        print(f"[BACKTEST] Running {len(common_index)} bars")
        
        # Main loop
        for i, timestamp in enumerate(common_index):
            context._current_idx = i
            self.state.timestamp = timestamp
            
            self._update_equity()
            self._check_exit_orders()
            
            # Max drawdown check
            if self.state.current_drawdown > self.config.max_drawdown_pct:
                print(f"[BACKTEST] Max drawdown hit at {timestamp}")
                self._close_all_positions()
                break
            
            # Get signals
            signals = self.strategy.next(context)
            if signals:
                for signal in signals:
                    self._process_signal(signal)
            
            self.state.equity_curve.append((timestamp, self.state.equity))
            
            if i % 1000 == 0:
                print(f"[BACKTEST] {i}/{len(common_index)} | ${self.state.equity:,.2f}")
        
        self.strategy.on_end(context)
        self._close_all_positions()
        
        return self._calculate_results()
    
    def _update_equity(self) -> None:
        """Update equity based on positions."""
        position_value = 0.0
        
        for symbol, position in self.state.positions.items():
            idx = self.data[symbol].index.get_loc(self.state.timestamp)
            current_price = self.data[symbol].iloc[idx]['close']
            pnl = (current_price - position.entry_price) * position.size
            if position.side == 'short':
                pnl = -pnl
            position_value += position.size * position.entry_price + pnl
        
        self.state.equity = self.state.cash + position_value
        
        if self.state.equity > self.state.peak_equity:
            self.state.peak_equity = self.state.equity
        
        self.state.current_drawdown = (
            (self.state.peak_equity - self.state.equity) / self.state.peak_equity
            if self.state.peak_equity > 0 else 0
        )
    
    def _process_signal(self, signal: Dict) -> None:
        """Process trading signal."""
        action = signal.get('action', '').upper()
        symbol = signal.get('symbol')
        
        if action == 'BUY':
            self._open_position(symbol, 'long', signal)
        elif action == 'SELL':
            self._open_position(symbol, 'short', signal)
        elif action == 'CLOSE':
            self._close_position(symbol)
    
    def _open_position(self, symbol: str, side: str, signal: Dict) -> None:
        """Open position."""
        if symbol in self.state.positions:
            return
        
        idx = self.data[symbol].index.get_loc(self.state.timestamp)
        current_price = self.data[symbol].iloc[idx]['close']
        
        size_pct = min(signal.get('size', 0.1), self.config.max_position_pct)
        position_value = self.state.equity * size_pct
        
        slippage = self.slippage_model.calculate(current_price, position_value, side)
        entry_price = current_price * (1 + slippage if side == 'long' else 1 - slippage)
        
        fee = self.fee_model.calculate(position_value, 'taker')
        size = position_value / entry_price
        
        position = Position(
            symbol=symbol,
            side=side,
            size=size,
            entry_price=entry_price,
            entry_time=self.state.timestamp,
            stop_loss=signal.get('stop_loss'),
            take_profit=signal.get('take_profit')
        )
        
        self.state.positions[symbol] = position
        self.state.cash -= position_value + fee
        
        trade = Trade(
            symbol=symbol,
            side=side,
            type=TradeType.ENTRY,
            price=entry_price,
            size=size,
            fee=fee,
            timestamp=self.state.timestamp
        )
        self.state.trades.append(trade)
    
    def _close_position(self, symbol: str) -> None:
        """Close position."""
        if symbol not in self.state.positions:
            return
        
        position = self.state.positions[symbol]
        idx = self.data[symbol].index.get_loc(self.state.timestamp)
        current_price = self.data[symbol].iloc[idx]['close']
        
        exit_side = 'sell' if position.side == 'long' else 'buy'
        slippage = self.slippage_model.calculate(current_price, position.size * current_price, exit_side)
        exit_price = current_price * (1 - slippage if position.side == 'long' else 1 + slippage)
        
        if position.side == 'long':
            pnl = (exit_price - position.entry_price) * position.size
        else:
            pnl = (position.entry_price - exit_price) * position.size
        
        position_value = position.size * exit_price
        fee = self.fee_model.calculate(position_value, 'taker')
        
        self.state.cash += position_value - fee
        
        trade = Trade(
            symbol=symbol,
            side=exit_side,
            type=TradeType.EXIT,
            price=exit_price,
            size=position.size,
            fee=fee,
            pnl=pnl - fee,
            timestamp=self.state.timestamp
        )
        self.state.trades.append(trade)
        del self.state.positions[symbol]
    
    def _check_exit_orders(self) -> None:
        """Check SL/TP."""
        to_close = []
        
        for symbol, position in self.state.positions.items():
            idx = self.data[symbol].index.get_loc(self.state.timestamp)
            current_price = self.data[symbol].iloc[idx]['close']
            
            if position.stop_loss:
                if position.side == 'long' and current_price <= position.stop_loss:
                    to_close.append(symbol)
                elif position.side == 'short' and current_price >= position.stop_loss:
                    to_close.append(symbol)
            
            if position.take_profit:
                if position.side == 'long' and current_price >= position.take_profit:
                    to_close.append(symbol)
                elif position.side == 'short' and current_price <= position.take_profit:
                    to_close.append(symbol)
        
        for symbol in to_close:
            self._close_position(symbol)
    
    def _close_all_positions(self) -> None:
        """Close all positions."""
        for symbol in list(self.state.positions.keys()):
            self._close_position(symbol)
    
    def _calculate_results(self) -> 'BacktestResult':
        """Calculate metrics."""
        equity_curve = pd.Series(
            [e[1] for e in self.state.equity_curve],
            index=[e[0] for e in self.state.equity_curve]
        )
        
        returns = equity_curve.pct_change().dropna()
        
        metrics = self.metrics_calc.calculate_all(
            equity_curve=equity_curve,
            returns=returns,
            trades=self.state.trades,
            initial_capital=self.config.initial_capital
        )
        
        return BacktestResult(
            **metrics,
            equity_curve=equity_curve,
            trades=self.state.trades,
            config=self.config
        )


@dataclass
class BacktestResult:
    """Backtest result with all metrics."""
    
    total_return: float
    annualized_return: float
    sharpe_ratio: float
    sortino_ratio: float
    calmar_ratio: float
    max_drawdown: float
    max_drawdown_duration: timedelta
    volatility: float
    var_95: float
    cvar_95: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate: float
    profit_factor: float
    average_win: float
    average_loss: float
    largest_win: float
    largest_loss: float
    total_fees: float
    total_slippage: float
    final_equity: float
    equity_curve: pd.Series
    trades: List[Trade]
    config: BacktestConfig
    
    def summary(self) -> str:
        """Return summary string."""
        return f"""
╔══════════════════════════════════════════════════════════════════╗
║                    BACKTEST RESULTS                              ║
╠══════════════════════════════════════════════════════════════════╣
║  Period: {self.config.start_date.date()} to {self.config.end_date.date()}
║  Initial: ${self.config.initial_capital:,.2f} → Final: ${self.final_equity:,.2f}
╠══════════════════════════════════════════════════════════════════╣
║  RETURNS                                                         ║
║  ├── Total: {self.total_return:,.2%} | Annualized: {self.annualized_return:,.2%}
║  └── Volatility: {self.volatility:,.2%}
╠══════════════════════════════════════════════════════════════════╣
║  RISK METRICS                                                    ║
║  ├── Sharpe: {self.sharpe_ratio:.2f} | Sortino: {self.sortino_ratio:.2f} | Calmar: {self.calmar_ratio:.2f}
║  ├── Max DD: {self.max_drawdown:,.2%}
║  └── VaR 95%: {self.var_95:,.2%} | CVaR 95%: {self.cvar_95:,.2%}
╠══════════════════════════════════════════════════════════════════╣
║  TRADES                                                          ║
║  ├── Total: {self.total_trades} | Win Rate: {self.win_rate:,.2%}
║  ├── Profit Factor: {self.profit_factor:.2f}
║  └── Fees: ${self.total_fees:,.2f}
╚══════════════════════════════════════════════════════════════════╝
"""
    
    def to_dict(self) -> Dict:
        """Convert to dictionary."""
        return {
            'total_return': self.total_return,
            'annualized_return': self.annualized_return,
            'sharpe_ratio': self.sharpe_ratio,
            'sortino_ratio': self.sortino_ratio,
            'max_drawdown': self.max_drawdown,
            'win_rate': self.win_rate,
            'profit_factor': self.profit_factor,
            'final_equity': self.final_equity,
            'total_trades': self.total_trades
        }
