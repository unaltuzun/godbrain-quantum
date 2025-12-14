# ==============================================================================
# STRATEGY KNOWLEDGE - Trading Strategy Database
# ==============================================================================
"""
Database of trading strategies and their performance.

Seraph learns:
- Which strategies work in which regimes
- Historical performance of DNA parameters
- Successful trading patterns
"""

import json
import time
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger("seraph.knowledge.strategies")


@dataclass
class StrategyRecord:
    """Record of a strategy's performance"""
    id: str
    name: str
    description: str
    dna_params: Dict[str, float]
    regime: str  # "BULL", "BEAR", "SIDEWAYS", "ALL"
    total_trades: int
    win_rate: float
    avg_pnl_pct: float
    sharpe_ratio: float
    max_drawdown: float
    last_used: str
    created: str
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "StrategyRecord":
        return cls(**data)


class StrategyKnowledge:
    """
    Knowledge base of trading strategies.
    
    Enables Seraph to:
    - Recommend strategies for current regime
    - Learn from strategy performance
    - Evolve better strategies
    """
    
    # Built-in strategy templates
    TEMPLATES = [
        StrategyRecord(
            id="conservative",
            name="Conservative",
            description="Low risk, steady returns. Tight stop loss, moderate take profit.",
            dna_params={"stop_loss_pct": 1.5, "take_profit_pct": 3.0, "position_size_factor": 0.5},
            regime="ALL",
            total_trades=0, win_rate=0, avg_pnl_pct=0, sharpe_ratio=0, max_drawdown=0,
            last_used="", created="2024-01-01"
        ),
        StrategyRecord(
            id="aggressive",
            name="Aggressive Bull",
            description="High risk, high reward for bull markets.",
            dna_params={"stop_loss_pct": 3.0, "take_profit_pct": 8.0, "position_size_factor": 1.5},
            regime="BULL",
            total_trades=0, win_rate=0, avg_pnl_pct=0, sharpe_ratio=0, max_drawdown=0,
            last_used="", created="2024-01-01"
        ),
        StrategyRecord(
            id="scalper",
            name="Scalper",
            description="Quick trades, small profits. Works in sideways markets.",
            dna_params={"stop_loss_pct": 0.5, "take_profit_pct": 1.0, "position_size_factor": 2.0},
            regime="SIDEWAYS",
            total_trades=0, win_rate=0, avg_pnl_pct=0, sharpe_ratio=0, max_drawdown=0,
            last_used="", created="2024-01-01"
        ),
        StrategyRecord(
            id="bear_survivor",
            name="Bear Survivor",
            description="Defensive strategy for bear markets. Wide stops, quick exits.",
            dna_params={"stop_loss_pct": 5.0, "take_profit_pct": 2.0, "position_size_factor": 0.3},
            regime="BEAR",
            total_trades=0, win_rate=0, avg_pnl_pct=0, sharpe_ratio=0, max_drawdown=0,
            last_used="", created="2024-01-01"
        )
    ]
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path(__file__).parent.parent.parent / "logs" / "strategies.json"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        self._strategies: Dict[str, StrategyRecord] = {}
        
        # Load templates
        for template in self.TEMPLATES:
            self._strategies[template.id] = template
        
        # Load learned strategies
        self._load()
    
    def _load(self):
        """Load strategies from disk"""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for strategy_data in data.get("strategies", []):
                        strategy = StrategyRecord.from_dict(strategy_data)
                        self._strategies[strategy.id] = strategy
                logger.info(f"Loaded {len(self._strategies)} strategies")
            except Exception as e:
                logger.warning(f"Failed to load strategies: {e}")
    
    def _save(self):
        """Save strategies to disk"""
        try:
            data = {
                "strategies": [s.to_dict() for s in self._strategies.values()]
            }
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save strategies: {e}")
    
    def get_strategy(self, strategy_id: str) -> Optional[StrategyRecord]:
        """Get strategy by ID"""
        return self._strategies.get(strategy_id)
    
    def recommend_for_regime(self, regime: str) -> List[StrategyRecord]:
        """
        Recommend strategies for current regime.
        
        Args:
            regime: Market regime ("BULL", "BEAR", "SIDEWAYS")
        
        Returns:
            Recommended strategies, sorted by Sharpe ratio
        """
        matching = [s for s in self._strategies.values() 
                   if s.regime == regime or s.regime == "ALL"]
        
        # Sort by Sharpe ratio (higher is better)
        matching.sort(key=lambda s: s.sharpe_ratio, reverse=True)
        
        return matching
    
    def record_performance(
        self,
        strategy_id: str,
        trades: int,
        wins: int,
        total_pnl_pct: float,
        max_drawdown: float
    ):
        """Record strategy performance"""
        if strategy_id not in self._strategies:
            return
        
        strategy = self._strategies[strategy_id]
        
        # Update running averages
        total_trades = strategy.total_trades + trades
        if total_trades > 0:
            # Weighted average
            old_weight = strategy.total_trades / total_trades
            new_weight = trades / total_trades
            
            strategy.win_rate = strategy.win_rate * old_weight + (wins / trades) * new_weight
            strategy.avg_pnl_pct = strategy.avg_pnl_pct * old_weight + (total_pnl_pct / trades) * new_weight
            strategy.max_drawdown = max(strategy.max_drawdown, max_drawdown)
        
        strategy.total_trades = total_trades
        strategy.last_used = time.strftime("%Y-%m-%d %H:%M:%S")
        
        self._save()
    
    def add_strategy(
        self,
        name: str,
        description: str,
        dna_params: Dict[str, float],
        regime: str = "ALL"
    ) -> StrategyRecord:
        """Add a new strategy"""
        strategy_id = f"custom_{len(self._strategies)}_{int(time.time())}"
        
        strategy = StrategyRecord(
            id=strategy_id,
            name=name,
            description=description,
            dna_params=dna_params,
            regime=regime,
            total_trades=0,
            win_rate=0,
            avg_pnl_pct=0,
            sharpe_ratio=0,
            max_drawdown=0,
            last_used="",
            created=time.strftime("%Y-%m-%d")
        )
        
        self._strategies[strategy_id] = strategy
        self._save()
        
        return strategy
    
    def get_stats(self) -> Dict[str, Any]:
        """Get strategy statistics"""
        return {
            "total_strategies": len(self._strategies),
            "by_regime": {
                regime: len([s for s in self._strategies.values() if s.regime == regime])
                for regime in ["BULL", "BEAR", "SIDEWAYS", "ALL"]
            },
            "best_performers": sorted(
                [(s.id, s.sharpe_ratio) for s in self._strategies.values()],
                key=lambda x: x[1],
                reverse=True
            )[:5]
        }

