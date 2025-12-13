# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   ⚛️  QUANTUM RESONANCE LAB v2.1 - INTEGRATED MULTIVERSE ENGINE  ⚛️           ║
║                                                                               ║
║   Entegrasyonlar:                                                             ║
║   ✅ DNA Engine Academy - Mevcut genom sıralaması ile uyumlu                  ║
║   ✅ Resonance Bus - Quantum/Coherent state sinyalleri                        ║
║   ✅ Double Slit Experiment - Interference pattern feedback                   ║
║   ✅ Seraph v2.0 - Otomatik kod deployment                                    ║
║                                                                               ║
║   "Training across infinite parallel universes to find optimal strategies"   ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝

ARCHITECTURE:
=============

┌─────────────────────────────────────────────────────────────────────────────┐
│                    QUANTUM RESONANCE LAB v2.1 (INTEGRATED)                  │
├─────────────────────────────────────────────────────────────────────────────┤
│                                                                             │
│  ┌───────────────────────────────────────────────────────────────────┐     │
│  │                    EXISTING GODBRAIN MODULES                       │     │
│  │  ┌─────────────┐  ┌─────────────┐  ┌─────────────────────────┐   │     │
│  │  │ DNA Academy │  │ Resonance   │  │ Double Slit Experiment  │   │     │
│  │  │ (Rankings)  │  │    Bus      │  │ (Interference Patterns) │   │     │
│  │  └──────┬──────┘  └──────┬──────┘  └────────────┬────────────┘   │     │
│  └─────────┼────────────────┼──────────────────────┼────────────────┘     │
│            │                │                      │                       │
│            └────────────────┴──────────────────────┘                       │
│                             │                                              │
│                             ▼                                              │
│  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐  ┌─────────────┐       │
│  │ Universe-α  │  │ Universe-β  │  │ Universe-γ  │  │ Universe-δ  │ ...  │
│  │ Bull Market │  │ Bear Market │  │ Black Swan  │  │  Sideways   │       │
│  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘  └──────┬──────┘       │
│         └────────────────┴────────────────┴────────────────┘              │
│                                   │                                        │
│                                   ▼                                        │
│                    ┌──────────────────────────────┐                       │
│                    │  GENETIC ALGORITHM ENGINE    │                       │
│                    │  + DNA Academy Sync          │                       │
│                    └──────────────┬───────────────┘                       │
│                                   │                                        │
│                                   ▼                                        │
│                    ┌──────────────────────────────┐                       │
│                    │      WISDOM EXTRACTOR        │                       │
│                    │  → Seraph Commands           │                       │
│                    └──────────────┬───────────────┘                       │
│                                   │                                        │
│                                   ▼                                        │
│                    ┌──────────────────────────────┐                       │
│                    │         SERAPH v2.0          │                       │
│                    │    (Auto Code Deployment)    │                       │
│                    └──────────────┬───────────────┘                       │
│                                   │                                        │
│                                   ▼                                        │
│                    ┌──────────────────────────────┐                       │
│                    │      GODBRAIN LIVE           │                       │
│                    │    (Production Trading)      │                       │
│                    └──────────────────────────────┘                       │
│                                                                            │
└────────────────────────────────────────────────────────────────────────────┘
"""

import os
import sys
import json
import random
import hashlib
import numpy as np
import pandas as pd
from pathlib import Path
from datetime import datetime, timedelta
from dataclasses import dataclass, field, asdict
from typing import Dict, List, Optional, Tuple, Any
from enum import Enum
from collections import defaultdict
import time
import warnings

# Suppress pandas warnings
warnings.filterwarnings('ignore', category=FutureWarning)
warnings.filterwarnings('ignore', category=DeprecationWarning)

# =============================================================================
# PATHS
# =============================================================================

QUANTUM_ROOT = Path("/mnt/c/godbrain-quantum")
UNIVERSE_ROOT = Path("/mnt/c/godbrain-universe")
LAB_DIR = QUANTUM_ROOT / "quantum_lab"
UNIVERSES_DIR = LAB_DIR / "universes"
CONVERGENCE_DIR = LAB_DIR / "convergence"
WISDOM_DIR = LAB_DIR / "wisdom"
LOG_DIR = QUANTUM_ROOT / "logs"

# Create directories
for d in [LAB_DIR, UNIVERSES_DIR, CONVERGENCE_DIR, WISDOM_DIR, LOG_DIR]:
    d.mkdir(parents=True, exist_ok=True)

# =============================================================================
# INTEGRATION WITH EXISTING GODBRAIN MODULES
# =============================================================================

_DNA_ACADEMY_AVAILABLE = False
_RESONANCE_BUS_AVAILABLE = False
_existing_academy = None
_resonance_bus = None

# Add quantum root to path for imports
if str(QUANTUM_ROOT) not in sys.path:
    sys.path.insert(0, str(QUANTUM_ROOT))

try:
    from dna_engine_academy import (
        DNAAcademy as ExistingDNAAcademy, 
        DNAStrategyParams as ExistingDNAParams,
        GenomeRecord,
        run_dna_cycle_from_snapshots
    )
    _DNA_ACADEMY_AVAILABLE = True
except ImportError:
    pass

try:
    from resonance_bus import ResonanceBus, ResonanceState
    _RESONANCE_BUS_AVAILABLE = True
except ImportError:
    pass


def init_integrations():
    """Initialize integrations with existing modules."""
    global _existing_academy, _resonance_bus
    
    print("\n🔗 Mevcut GODBRAIN modülleri ile entegrasyon:")
    
    if _DNA_ACADEMY_AVAILABLE:
        _existing_academy = ExistingDNAAcademy()
        print("  ✅ DNA Engine Academy - Genom ranking sistemi aktif")
    else:
        print("  ⚠️  DNA Engine Academy - Bulunamadı (standalone mod)")
    
    if _RESONANCE_BUS_AVAILABLE:
        neural_stream = LOG_DIR / "neural_stream.log"
        _resonance_bus = ResonanceBus(
            neural_stream_path=neural_stream,
            redis_dsn=os.getenv("GODBRAIN_REDIS_DSN", "")
        )
        print("  ✅ Resonance Bus - Quantum state sinyalleri aktif")
    else:
        print("  ⚠️  Resonance Bus - Bulunamadı (standalone mod)")
    
    # Check double slit experiment
    dslit_log = LOG_DIR / "double_slit_experiment.log"
    if dslit_log.exists():
        print("  ✅ Double Slit Experiment - Interference log bulundu")
    else:
        print("  ⚠️  Double Slit Experiment - Log dosyası yok")
    
    print()


# =============================================================================
# ENUMS & DATA CLASSES
# =============================================================================

class UniverseType(Enum):
    BULL_MARKET = "bull_market"
    BEAR_MARKET = "bear_market"
    BLACK_SWAN = "black_swan"
    SIDEWAYS = "sideways"
    HIGH_VOLATILITY = "high_volatility"
    LOW_VOLATILITY = "low_volatility"
    FLASH_CRASH = "flash_crash"
    PUMP_DUMP = "pump_dump"
    ACCUMULATION = "accumulation"
    DISTRIBUTION = "distribution"


@dataclass
class StrategyGene:
    """Genetic representation of a trading strategy - compatible with DNA Academy."""
    
    # Regime Detection
    regime_cooldown: int = 300
    rsi_overbought: float = 70.0
    rsi_oversold: float = 30.0
    
    # Position Sizing (DNA Academy compatible)
    stop_loss_pct: float = -2.0
    take_profit_pct: float = 4.0
    position_size_factor: float = 0.15
    
    # Risk Management
    trailing_stop_activation: float = 1.5
    trailing_stop_distance: float = 0.8
    max_daily_loss_pct: float = 5.0
    
    # Anti-Whipsaw
    min_trade_interval: int = 120
    reversal_cooldown: int = 300
    max_reversals_per_hour: int = 3
    consecutive_signals_required: int = 3
    
    # Strategy Weights
    trend_weight: float = 0.4
    momentum_weight: float = 0.3
    mean_reversion_weight: float = 0.3
    
    # Conviction
    conviction_threshold: float = 0.6
    
    def to_dna_academy_format(self) -> dict:
        """Convert to DNA Academy compatible format."""
        return {
            "stop_loss_pct": self.stop_loss_pct,
            "take_profit_pct": self.take_profit_pct,
            "rsi_buy_level": self.rsi_oversold,
            "rsi_sell_level": self.rsi_overbought,
            "position_size_factor": self.position_size_factor,
        }
    
    @classmethod
    def from_dna_academy(cls, dna_params) -> 'StrategyGene':
        """Create from DNA Academy parameters."""
        return cls(
            stop_loss_pct=dna_params.stop_loss_pct,
            take_profit_pct=dna_params.take_profit_pct,
            rsi_oversold=dna_params.rsi_buy_level,
            rsi_overbought=dna_params.rsi_sell_level,
            position_size_factor=dna_params.position_size_factor,
        )
    
    def mutate(self, mutation_rate: float = 0.1) -> 'StrategyGene':
        """Create a mutated copy."""
        new_gene = StrategyGene(**asdict(self))
        
        for field_name, value in asdict(self).items():
            if random.random() < mutation_rate:
                if isinstance(value, int):
                    delta = int(value * random.uniform(-0.3, 0.3))
                    setattr(new_gene, field_name, max(1, value + delta))
                elif isinstance(value, float):
                    delta = value * random.uniform(-0.3, 0.3)
                    new_val = value + delta
                    # Clamp certain values
                    if 'pct' in field_name and field_name != 'stop_loss_pct':
                        new_val = max(0.01, new_val)
                    setattr(new_gene, field_name, new_val)
        
        return new_gene
    
    def crossover(self, other: 'StrategyGene') -> 'StrategyGene':
        """Create offspring from two parents."""
        new_gene = StrategyGene()
        for field_name in asdict(self).keys():
            if random.random() < 0.5:
                setattr(new_gene, field_name, getattr(self, field_name))
            else:
                setattr(new_gene, field_name, getattr(other, field_name))
        return new_gene
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'StrategyGene':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    @classmethod
    def random(cls) -> 'StrategyGene':
        """Generate random strategy gene."""
        return cls(
            regime_cooldown=random.randint(60, 900),
            rsi_overbought=random.uniform(65, 85),
            rsi_oversold=random.uniform(15, 35),
            stop_loss_pct=-random.uniform(1.0, 5.0),
            take_profit_pct=random.uniform(2.0, 10.0),
            position_size_factor=random.uniform(0.05, 0.35),
            trailing_stop_activation=random.uniform(0.5, 3.0),
            trailing_stop_distance=random.uniform(0.3, 1.5),
            max_daily_loss_pct=random.uniform(3.0, 10.0),
            min_trade_interval=random.randint(30, 300),
            reversal_cooldown=random.randint(120, 600),
            max_reversals_per_hour=random.randint(2, 6),
            consecutive_signals_required=random.randint(1, 5),
            trend_weight=random.uniform(0.2, 0.6),
            momentum_weight=random.uniform(0.1, 0.5),
            mean_reversion_weight=random.uniform(0.1, 0.5),
            conviction_threshold=random.uniform(0.4, 0.8)
        )


@dataclass
class UniverseResult:
    """Result from universe simulation."""
    universe_id: str
    universe_type: UniverseType
    gene: StrategyGene
    
    total_return_pct: float = 0.0
    sharpe_ratio: float = 0.0
    max_drawdown_pct: float = 0.0
    win_rate: float = 0.0
    profit_factor: float = 0.0
    total_trades: int = 0
    
    fitness: float = 0.0
    
    def calculate_fitness(self):
        """Calculate composite fitness score."""
        return_score = np.tanh(self.total_return_pct / 100) * 30
        sharpe_score = np.tanh(self.sharpe_ratio) * 25
        drawdown_penalty = max(0, self.max_drawdown_pct - 10) * 2
        win_rate_score = self.win_rate * 20
        profit_factor_score = min(self.profit_factor, 3) * 10
        
        self.fitness = (
            return_score + sharpe_score + win_rate_score + 
            profit_factor_score - drawdown_penalty
        )
        return self.fitness


@dataclass
class ConvergedWisdom:
    """Wisdom from multiverse training."""
    timestamp: datetime
    generations_trained: int
    universes_simulated: int
    best_fitness: float
    best_gene: StrategyGene
    optimal_ranges: Dict[str, Tuple[float, float]] = field(default_factory=dict)
    recommended_changes: List[Dict[str, Any]] = field(default_factory=list)
    
    # DNA Academy sync
    academy_rank: str = "CADET"
    academy_score: float = 0.0


# =============================================================================
# MARKET SIMULATOR
# =============================================================================

class MarketSimulator:
    """Generate synthetic market data for different universe types."""
    
    @staticmethod
    def generate_universe(
        universe_type: UniverseType,
        duration_days: int = 180,
        interval_minutes: int = 5
    ) -> pd.DataFrame:
        """Generate OHLCV data."""
        
        num_candles = (duration_days * 24 * 60) // interval_minutes
        
        params = {
            UniverseType.BULL_MARKET: {'trend': 0.0003, 'vol': 0.02},
            UniverseType.BEAR_MARKET: {'trend': -0.0003, 'vol': 0.025},
            UniverseType.BLACK_SWAN: {'trend': 0.0, 'vol': 0.05},
            UniverseType.SIDEWAYS: {'trend': 0.0, 'vol': 0.015},
            UniverseType.HIGH_VOLATILITY: {'trend': 0.0001, 'vol': 0.04},
            UniverseType.LOW_VOLATILITY: {'trend': 0.0001, 'vol': 0.008},
            UniverseType.FLASH_CRASH: {'trend': 0.0001, 'vol': 0.02},
            UniverseType.PUMP_DUMP: {'trend': 0.0, 'vol': 0.03},
            UniverseType.ACCUMULATION: {'trend': 0.0001, 'vol': 0.012},
            UniverseType.DISTRIBUTION: {'trend': -0.0001, 'vol': 0.015},
        }
        
        p = params.get(universe_type, params[UniverseType.SIDEWAYS])
        
        np.random.seed(hash(f"{universe_type.value}_{duration_days}") % (2**32))
        returns = np.random.normal(p['trend'], p['vol'], num_candles)
        
        # Special events
        if universe_type == UniverseType.FLASH_CRASH:
            crash_idx = num_candles // 2
            returns[crash_idx:crash_idx+20] = -0.05
            returns[crash_idx+20:crash_idx+40] = 0.03
        
        if universe_type == UniverseType.PUMP_DUMP:
            pump_idx = num_candles // 3
            returns[pump_idx:pump_idx+50] = 0.02
            returns[pump_idx+50:pump_idx+70] = -0.04
        
        prices = 100 * np.exp(np.cumsum(returns))
        
        df = pd.DataFrame()
        df['timestamp'] = pd.date_range(start='2023-01-01', periods=num_candles, freq=f'{interval_minutes}min')
        df['close'] = prices
        
        noise = np.random.uniform(0.998, 1.002, num_candles)
        df['open'] = np.roll(df['close'].values, 1) * noise
        df.loc[0, 'open'] = df.loc[0, 'close']
        
        df['high'] = df[['open', 'close']].max(axis=1) * np.random.uniform(1.0, 1.01, num_candles)
        df['low'] = df[['open', 'close']].min(axis=1) * np.random.uniform(0.99, 1.0, num_candles)
        df['volume'] = 1000000 * np.random.uniform(0.8, 1.2, num_candles)
        
        return df


# =============================================================================
# BACKTESTER
# =============================================================================

class StrategyBacktester:
    """Backtest strategy gene against market data."""
    
    def __init__(self, gene: StrategyGene, initial_capital: float = 10000):
        self.gene = gene
        self.initial_capital = initial_capital
        self.reset()
    
    def reset(self):
        self.capital = self.initial_capital
        self.position = 0.0
        self.entry_price = 0.0
        self.trades = []
        self.equity_curve = []
        self.last_trade_time = None
        self.last_direction = None
    
    def run(self, df: pd.DataFrame) -> UniverseResult:
        """Run backtest."""
        self.reset()
        
        for idx in range(50, len(df)):
            row = df.iloc[idx]
            close = float(row['close'])
            timestamp = row['timestamp'] if 'timestamp' in row else datetime.now()
            
            # Track equity
            current_equity = self.capital
            if self.position != 0:
                unrealized = self.position * (close - self.entry_price)
                current_equity += unrealized
            self.equity_curve.append(current_equity)
            
            # Check stops for open positions
            if self.position != 0:
                pnl_pct = (close - self.entry_price) / self.entry_price * 100
                if self.position > 0:
                    if pnl_pct <= self.gene.stop_loss_pct:
                        pnl = self.position * (close - self.entry_price)
                        self.capital += pnl
                        self.trades.append({'pnl': pnl, 'reason': 'sl'})
                        self.position = 0.0
                        continue
                    elif pnl_pct >= self.gene.take_profit_pct:
                        pnl = self.position * (close - self.entry_price)
                        self.capital += pnl
                        self.trades.append({'pnl': pnl, 'reason': 'tp'})
                        self.position = 0.0
                        continue
            
            # Simple signal generation
            window = df.iloc[max(0, idx-20):idx+1]
            if len(window) < 20:
                continue
                
            closes = window['close'].values
            
            # RSI calculation
            delta = np.diff(closes)
            gains = np.where(delta > 0, delta, 0)
            losses = np.where(delta < 0, -delta, 0)
            avg_gain = np.mean(gains[-14:]) if len(gains) >= 14 else 0
            avg_loss = np.mean(losses[-14:]) if len(losses) >= 14 else 0.0001
            rsi = 100 - (100 / (1 + avg_gain / avg_loss))
            
            # Signal
            signal = 'HOLD'
            if rsi < self.gene.rsi_oversold:
                signal = 'BUY'
            elif rsi > self.gene.rsi_overbought:
                signal = 'SELL'
            
            # Anti-whipsaw check
            if self.last_trade_time:
                seconds_since = (timestamp - self.last_trade_time).total_seconds()
                if seconds_since < self.gene.min_trade_interval:
                    signal = 'HOLD'
            
            # Execute
            if signal == 'BUY' and self.position <= 0:
                if self.position < 0:
                    pnl = -self.position * (self.entry_price - close)
                    self.capital += pnl
                    self.trades.append({'pnl': pnl, 'reason': 'reversal'})
                
                size = self.capital * self.gene.position_size_factor / close
                self.position = size
                self.entry_price = close
                self.last_trade_time = timestamp
                self.last_direction = 'BUY'
                self.trades.append({'entry': close, 'dir': 'LONG'})
            
            elif signal == 'SELL' and self.position >= 0:
                if self.position > 0:
                    pnl = self.position * (close - self.entry_price)
                    self.capital += pnl
                    self.trades.append({'pnl': pnl, 'reason': 'reversal'})
                
                size = self.capital * self.gene.position_size_factor / close
                self.position = -size
                self.entry_price = close
                self.last_trade_time = timestamp
                self.last_direction = 'SELL'
                self.trades.append({'entry': close, 'dir': 'SHORT'})
        
        # Close remaining
        if self.position != 0:
            close = df.iloc[-1]['close']
            if self.position > 0:
                pnl = self.position * (close - self.entry_price)
            else:
                pnl = -self.position * (self.entry_price - close)
            self.capital += pnl
            self.trades.append({'pnl': pnl, 'reason': 'end'})
        
        return self._calculate_results()
    
    def _calculate_results(self) -> UniverseResult:
        """Calculate performance metrics."""
        equity = np.array(self.equity_curve) if self.equity_curve else np.array([self.initial_capital])
        
        total_return = (self.capital - self.initial_capital) / self.initial_capital * 100
        
        if len(equity) > 1:
            returns = np.diff(equity) / equity[:-1]
            sharpe = np.mean(returns) / (np.std(returns) + 1e-10) * np.sqrt(252 * 24 * 12)
        else:
            sharpe = 0.0
        
        peak = np.maximum.accumulate(equity)
        drawdown = (peak - equity) / peak * 100
        max_dd = np.max(drawdown)
        
        pnls = [t.get('pnl', 0) for t in self.trades if 'pnl' in t]
        wins = [p for p in pnls if p > 0]
        losses = [p for p in pnls if p < 0]
        
        win_rate = len(wins) / len(pnls) if pnls else 0.0
        profit_factor = sum(wins) / abs(sum(losses)) if losses and sum(losses) != 0 else float('inf')
        
        result = UniverseResult(
            universe_id="",
            universe_type=UniverseType.SIDEWAYS,
            gene=self.gene,
            total_return_pct=total_return,
            sharpe_ratio=sharpe,
            max_drawdown_pct=max_dd,
            win_rate=win_rate,
            profit_factor=min(profit_factor, 10),
            total_trades=len([t for t in self.trades if 'entry' in t])
        )
        result.calculate_fitness()
        return result


# =============================================================================
# GENETIC OPTIMIZER
# =============================================================================

class GeneticOptimizer:
    """Genetic algorithm for strategy optimization."""
    
    def __init__(self, population_size: int = 100, elite_count: int = 10):
        self.population_size = population_size
        self.elite_count = elite_count
        self.population: List[StrategyGene] = []
        self.generation = 0
        self.best_fitness_history = []
    
    def initialize_population(self):
        self.population = [StrategyGene.random() for _ in range(self.population_size)]
        self.generation = 0
    
    def evaluate_population(self, universes: List[Tuple[UniverseType, pd.DataFrame]]) -> List[Tuple[StrategyGene, float]]:
        results = []
        for gene in self.population:
            total_fitness = 0.0
            for universe_type, df in universes:
                backtester = StrategyBacktester(gene)
                result = backtester.run(df)
                total_fitness += result.fitness
            avg_fitness = total_fitness / len(universes)
            results.append((gene, avg_fitness))
        return sorted(results, key=lambda x: x[1], reverse=True)
    
    def evolve(self, ranked: List[Tuple[StrategyGene, float]]) -> List[StrategyGene]:
        new_pop = []
        
        # Elitism
        for gene, _ in ranked[:self.elite_count]:
            new_pop.append(gene)
        
        while len(new_pop) < self.population_size:
            tournament = random.sample(ranked, 5)
            parent1 = max(tournament, key=lambda x: x[1])[0]
            tournament = random.sample(ranked, 5)
            parent2 = max(tournament, key=lambda x: x[1])[0]
            
            child = parent1.crossover(parent2)
            if random.random() < 0.15:
                child = child.mutate()
            new_pop.append(child)
        
        self.population = new_pop
        self.generation += 1
        return new_pop


# =============================================================================
# MULTIVERSE ENGINE
# =============================================================================

class MultiverseEngine:
    """Main engine with integrations."""
    
    def __init__(self):
        self.optimizer = GeneticOptimizer()
        self.universes: List[Tuple[UniverseType, pd.DataFrame]] = []
        self.best_gene: Optional[StrategyGene] = None
        self.training_log = []
    
    def generate_universes(self, count_per_type: int = 1, duration_days: int = 180):
        print(f"\n🌌 Generating {len(UniverseType)} universe types x {count_per_type} variations...")
        self.universes = []
        
        for universe_type in UniverseType:
            for i in range(count_per_type):
                print(f"  Creating {universe_type.value} #{i+1}...")
                df = MarketSimulator.generate_universe(universe_type, duration_days)
                self.universes.append((universe_type, df))
        
        print(f"✅ Generated {len(self.universes)} parallel universes")
    
    def train(self, generations: int = 50) -> ConvergedWisdom:
        print(f"\n⚛️ Starting Multiverse Training")
        print(f"   Generations: {generations}")
        print(f"   Population: {self.optimizer.population_size}")
        print(f"   Universes: {len(self.universes)}")
        
        # Get resonance state if available
        if _resonance_bus:
            state = _resonance_bus.get_state()
            print(f"   Resonance: {state.mode} (active={state.active})")
        
        print("=" * 60)
        
        self.optimizer.initialize_population()
        best_overall_fitness = float('-inf')
        best_overall_gene = None
        
        for gen in range(generations):
            start = time.time()
            ranked = self.optimizer.evaluate_population(self.universes)
            
            best_gene, best_fitness = ranked[0]
            avg_fitness = np.mean([f for _, f in ranked])
            
            if best_fitness > best_overall_fitness:
                best_overall_fitness = best_fitness
                best_overall_gene = best_gene
            
            self.optimizer.best_fitness_history.append(best_fitness)
            elapsed = time.time() - start
            
            print(f"\n[Gen {gen+1:3d}/{generations}] "
                  f"Best: {best_fitness:.2f} | Avg: {avg_fitness:.2f} | Time: {elapsed:.1f}s")
            print(f"  └─ Cooldown: {best_gene.regime_cooldown}s | "
                  f"SL: {abs(best_gene.stop_loss_pct):.1f}% | TP: {best_gene.take_profit_pct:.1f}%")
            
            self.training_log.append({
                'generation': gen + 1,
                'best_fitness': best_fitness,
                'best_gene': best_gene.to_dict()
            })
            
            # Sync with DNA Academy if available
            if _existing_academy and best_overall_gene:
                genome_id = hashlib.md5(str(best_overall_gene.to_dict()).encode()).hexdigest()[:8]
                _existing_academy.record_cycle(
                    genome_id=genome_id,
                    family="QUANTUM_LAB_ELITE",
                    equity_change_pct=best_fitness / 10,
                    trades_in_cycle=10
                )
            
            if gen < generations - 1:
                self.optimizer.evolve(ranked)
        
        self.best_gene = best_overall_gene
        wisdom = self._extract_wisdom(generations)
        self._save_wisdom(wisdom)
        return wisdom
    
    def _extract_wisdom(self, generations: int) -> ConvergedWisdom:
        top_genes = [log['best_gene'] for log in self.training_log[-10:]]
        
        optimal_ranges = {}
        for param in ['regime_cooldown', 'stop_loss_pct', 'take_profit_pct', 'conviction_threshold']:
            values = [g[param] for g in top_genes]
            optimal_ranges[param] = (min(values), max(values))
        
        recommended = []
        if self.best_gene:
            recommended.append({
                'file': 'ultimate_pack/regime/regime_detector.py',
                'param': 'COOLDOWN_SEC',
                'old_value': 300,
                'new_value': self.best_gene.regime_cooldown,
                'reason': f'Optimized across {len(self.universes)} universes'
            })
            recommended.append({
                'file': 'ultimate_pack/filters/signal_filter.py',
                'param': 'MIN_SECONDS_BETWEEN_TRADES',
                'old_value': 120,
                'new_value': self.best_gene.min_trade_interval,
                'reason': 'Anti-whipsaw optimization'
            })
        
        # Get academy rank if synced
        academy_rank = "CADET"
        academy_score = 0.0
        if _existing_academy and self.best_gene:
            genome_id = hashlib.md5(str(self.best_gene.to_dict()).encode()).hexdigest()[:8]
            record = _existing_academy.get_record(genome_id)
            if record:
                academy_rank = record.rank
                academy_score = record.last_score
        
        return ConvergedWisdom(
            timestamp=datetime.now(),
            generations_trained=generations,
            universes_simulated=len(self.universes),
            best_fitness=self.optimizer.best_fitness_history[-1] if self.optimizer.best_fitness_history else 0,
            best_gene=self.best_gene,
            optimal_ranges=optimal_ranges,
            recommended_changes=recommended,
            academy_rank=academy_rank,
            academy_score=academy_score
        )
    
    def _save_wisdom(self, wisdom: ConvergedWisdom):
        ts = datetime.now().strftime("%Y%m%d_%H%M%S")
        
        gene_path = WISDOM_DIR / f"best_gene_{ts}.json"
        with open(gene_path, 'w') as f:
            json.dump(wisdom.best_gene.to_dict(), f, indent=2)
        
        log_path = WISDOM_DIR / f"training_log_{ts}.json"
        with open(log_path, 'w') as f:
            json.dump(self.training_log, f, indent=2)
        
        rec_path = WISDOM_DIR / f"recommendations_{ts}.json"
        with open(rec_path, 'w') as f:
            json.dump(wisdom.recommended_changes, f, indent=2)
        
        print(f"\n💾 Wisdom saved to {WISDOM_DIR}")


# =============================================================================
# SERAPH BRIDGE
# =============================================================================

class SeraphBridge:
    """Bridge to Seraph for code deployment."""
    
    def deploy_wisdom(self, wisdom: ConvergedWisdom) -> List[dict]:
        results = []
        
        print("\n🚀 Deploying Multiverse Wisdom to GODBRAIN...")
        print(f"   Academy Rank: {wisdom.academy_rank}")
        print(f"   Academy Score: {wisdom.academy_score:.2f}")
        
        for change in wisdom.recommended_changes:
            cmd = f"{change['param']} = {change['old_value']} satırını {change['param']} = {change['new_value']} olarak değiştir"
            results.append({'change': change, 'seraph_command': cmd})
            
            print(f"\n📝 {change['file']}")
            print(f"   {change['param']}: {change['old_value']} → {change['new_value']}")
            print(f"   Reason: {change['reason']}")
        
        return results


# =============================================================================
# CLI
# =============================================================================

def print_banner():
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   ⚛️  QUANTUM RESONANCE LAB v2.1 - INTEGRATED MULTIVERSE ENGINE  ⚛️           ║
║                                                                               ║
║   "Training across infinite parallel universes to find optimal strategies"   ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)


def main():
    print_banner()
    init_integrations()
    
    print("Commands:")
    print("  1. quick    - Quick training (10 universes, 10 generations)")
    print("  2. standard - Standard training (10 universes, 30 generations)")
    print("  3. deep     - Deep training (20 universes, 100 generations)")
    print("  4. deploy   - Deploy last wisdom to GODBRAIN via Seraph")
    print("  5. status   - Show DNA Academy leaderboard")
    print("  6. exit     - Exit")
    print()
    
    engine = MultiverseEngine()
    bridge = SeraphBridge()
    last_wisdom = None
    
    while True:
        try:
            cmd = input("\n⚛️ QUANTUM> ").strip().lower()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 Quantum Lab shutting down...")
            break
        
        if cmd in ('exit', 'quit', 'q'):
            print("👋 Quantum Lab shutting down...")
            break
        
        elif cmd in ('quick', '1'):
            engine.generate_universes(count_per_type=1, duration_days=90)
            last_wisdom = engine.train(generations=10)
        
        elif cmd in ('standard', '2'):
            engine.generate_universes(count_per_type=1, duration_days=180)
            last_wisdom = engine.train(generations=30)
        
        elif cmd in ('deep', '3'):
            engine.generate_universes(count_per_type=2, duration_days=365)
            last_wisdom = engine.train(generations=100)
        
        elif cmd in ('deploy', '4'):
            if last_wisdom:
                results = bridge.deploy_wisdom(last_wisdom)
                print("\n" + "="*60)
                print("To apply, run Seraph and enter:")
                print("="*60)
                for r in results:
                    print(f"\n🧠 SERAPH> {r['seraph_command']}")
            else:
                print("No wisdom. Run training first.")
        
        elif cmd in ('status', '5'):
            if _existing_academy:
                print("\n📊 DNA Academy Leaderboard:")
                for rec in _existing_academy.leaderboard(10):
                    print(f"  {rec.rank:12s} | {rec.genome_id} | Score: {rec.last_score:.2f} | WR: {rec.win_rate:.1%}")
            else:
                print("DNA Academy not available")
        
        else:
            print("Unknown command. Try: quick, standard, deep, deploy, status, exit")


if __name__ == "__main__":
    main()
