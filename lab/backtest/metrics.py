import pandas as pd
import numpy as np
from dataclasses import dataclass, field
from typing import List, Dict
from collections import deque

from .parser import TradeEvent
from .price_provider import PriceProvider

@dataclass
class BacktestReport:
    total_pnl: float = 0.0
    total_pnl_pct: float = 0.0
    win_rate: float = 0.0
    max_drawdown: float = 0.0
    sharpe: float = 0.0
    trade_count: int = 0
    start_date: str = ""
    end_date: str = ""
    equity_curve: List[float] = field(default_factory=list)
    per_symbol: Dict[str, dict] = field(default_factory=dict)

    def __str__(self) -> str:
        return (
            f"\n--- GODBRAIN BACKTEST REPORT ---\n"
            f"Period       : {self.start_date} to {self.end_date}\n"
            f"Trades       : {self.trade_count}\n"
            f"Total PnL    : ${self.total_pnl:,.2f} ({self.total_pnl_pct:.2f}%)\n"
            f"Win Rate     : {self.win_rate*100:.1f}%\n"
            f"Max Drawdown : {self.max_drawdown*100:.2f}%\n"
            f"Sharpe Ratio : {self.sharpe:.2f}\n"
        )

class FifoPositionTracker:
    """Tracks inventory for a single symbol using FIFO to calculate Realized PnL."""
    def __init__(self, symbol: str):
        self.symbol = symbol
        self.inventory = deque()  # (entry_price, amount)
        self.realized_pnl = 0.0
        self.closed_trades = 0
        self.winning_trades = 0
        self.total_volume = 0.0
        self.current_position_size = 0.0

    def process_trade(self, action: str, price: float, size_usd: float) -> float:
        if price <= 0:
            return 0.0

        amount = size_usd / price
        trade_pnl = 0.0
        is_buy = action.upper() in ["BUY", "STRONG_BUY"]

        if is_buy:
            self.inventory.append((price, amount))
            self.current_position_size += amount
            self.total_volume += size_usd
        else:
            amount_to_sell = amount
            self.total_volume += size_usd

            while amount_to_sell > 0 and self.inventory:
                entry_price, entry_amount = self.inventory[0]

                if entry_amount > amount_to_sell:
                    matched_amount = amount_to_sell
                    self.inventory[0] = (entry_price, entry_amount - matched_amount)
                    amount_to_sell = 0
                else:
                    matched_amount = entry_amount
                    amount_to_sell -= entry_amount
                    self.inventory.popleft()

                chunk_pnl = (price - entry_price) * matched_amount
                trade_pnl += chunk_pnl
                self.current_position_size -= matched_amount

            self.realized_pnl += trade_pnl
            if trade_pnl != 0:
                self.closed_trades += 1
                if trade_pnl > 0:
                    self.winning_trades += 1

        return trade_pnl

def run_metrics_engine(
    events: List[TradeEvent],
    price_provider: PriceProvider,
    initial_capital: float = 1000.0
) -> BacktestReport:
    if not events:
        return BacktestReport()

    events = sorted(events, key=lambda e: e.timestamp)
    trackers: Dict[str, FifoPositionTracker] = {}
    equity = initial_capital
    equity_curve: List[float] = []
    timestamps: List = []
    total_trades = 0

    start_date = events[0].timestamp
    end_date = events[-1].timestamp

    for event in events:
        if event.symbol not in trackers:
            trackers[event.symbol] = FifoPositionTracker(event.symbol)

        price = price_provider.get_price(event.symbol, event.timestamp)
        if price > 0:
            pnl_delta = trackers[event.symbol].process_trade(
                event.action, price, event.size_usd
            )
            equity += pnl_delta
            total_trades += 1

        equity_curve.append(equity)
        timestamps.append(event.timestamp)

    # Win rate
    total_closed = sum(t.closed_trades for t in trackers.values())
    total_wins = sum(t.winning_trades for t in trackers.values())
    win_rate = (total_wins / total_closed) if total_closed > 0 else 0.0

    # Max drawdown
    eq_series = pd.Series(equity_curve)
    rolling_max = eq_series.cummax()
    drawdown = (eq_series - rolling_max) / rolling_max
    max_dd = drawdown.min() if not drawdown.empty else 0.0

    # Sharpe (daily)
    sharpe = 0.0
    if len(equity_curve) > 1:
        df_eq = pd.DataFrame({"equity": equity_curve, "ts": timestamps}).set_index("ts")
        df_daily = df_eq.resample("D").last().ffill()
        df_daily["returns"] = df_daily["equity"].pct_change()

        mean_ret = df_daily["returns"].mean()
        std_ret = df_daily["returns"].std()
        if std_ret and std_ret > 0:
            sharpe = (mean_ret / std_ret) * np.sqrt(365)

    per_symbol_stats: Dict[str, dict] = {}
    for sym, tracker in trackers.items():
        per_symbol_stats[sym] = {
            "pnl": tracker.realized_pnl,
            "trades": tracker.closed_trades,
            "wins": tracker.winning_trades,
        }

    return BacktestReport(
        total_pnl=equity - initial_capital,
        total_pnl_pct=((equity - initial_capital) / initial_capital) * 100 if initial_capital > 0 else 0.0,
        win_rate=win_rate,
        max_drawdown=abs(max_dd),
        sharpe=sharpe,
        trade_count=total_trades,
        start_date=start_date.isoformat(),
        end_date=end_date.isoformat(),
        equity_curve=equity_curve,
        per_symbol=per_symbol_stats,
    )
