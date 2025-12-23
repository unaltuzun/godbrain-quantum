# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN SIMULATION UNIVERSE
Parallel simulation environments for rapid experimentation and learning.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import json
import time
import asyncio
import random
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any, Callable
from dataclasses import dataclass, field
from concurrent.futures import ThreadPoolExecutor, ProcessPoolExecutor
import threading
import multiprocessing as mp


ROOT = Path(__file__).parent.parent


# =============================================================================
# SIMULATION RESULT
# =============================================================================

@dataclass
class SimulationResult:
    """Result from a single simulation run."""
    simulation_id: str
    universe_id: int
    dna: List[int]
    timesteps: int
    final_equity: float
    total_pnl: float
    max_drawdown: float
    sharpe_ratio: float
    win_rate: float
    total_trades: int
    duration_seconds: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def fitness(self) -> float:
        """Calculate fitness score."""
        # Weighted combination of metrics
        sharpe_weight = 0.4
        drawdown_weight = 0.3
        winrate_weight = 0.2
        pnl_weight = 0.1
        
        sharpe_score = min(1.0, max(0, self.sharpe_ratio / 3))
        dd_score = 1.0 - min(1.0, abs(self.max_drawdown) * 5)
        wr_score = self.win_rate
        pnl_score = min(1.0, max(0, self.total_pnl / 1000))
        
        return (
            sharpe_weight * sharpe_score +
            drawdown_weight * dd_score +
            winrate_weight * wr_score +
            pnl_weight * pnl_score
        )
    
    def to_dict(self) -> Dict:
        return {
            "simulation_id": self.simulation_id,
            "universe_id": self.universe_id,
            "dna": self.dna,
            "fitness": self.fitness,
            "final_equity": self.final_equity,
            "sharpe_ratio": self.sharpe_ratio,
            "max_drawdown": self.max_drawdown,
            "win_rate": self.win_rate,
            "total_trades": self.total_trades
        }


# =============================================================================
# MARKET SIMULATOR
# =============================================================================

class MarketSimulator:
    """
    Simulates market price movements for backtesting.
    
    Modes:
    - Random walk
    - Mean reversion
    - Trending
    - Volatile crash
    """
    
    def __init__(self, initial_price: float = 0.32, seed: Optional[int] = None):
        if seed:
            np.random.seed(seed)
        
        self.initial_price = initial_price
        self.price = initial_price
        self.prices = [initial_price]
        self.timestep = 0
        
        # Volatility parameters
        self.base_volatility = 0.002
        self.regime = "neutral"
    
    def step(self) -> float:
        """Generate next price."""
        # Regime changes
        if random.random() < 0.01:
            self.regime = random.choice(["bullish", "bearish", "neutral", "volatile"])
        
        # Calculate return based on regime
        if self.regime == "bullish":
            drift = 0.0002
            vol = self.base_volatility
        elif self.regime == "bearish":
            drift = -0.0002
            vol = self.base_volatility * 1.5
        elif self.regime == "volatile":
            drift = 0
            vol = self.base_volatility * 3
        else:
            drift = 0
            vol = self.base_volatility
        
        # Generate return
        ret = drift + np.random.normal(0, vol)
        
        # Apply to price
        self.price *= (1 + ret)
        self.prices.append(self.price)
        self.timestep += 1
        
        return self.price
    
    def get_ohlcv(self, n_candles: int = 1) -> np.ndarray:
        """Generate OHLCV data."""
        data = []
        for _ in range(n_candles):
            open_p = self.price
            moves = [self.step() for _ in range(4)]
            close_p = self.price
            high_p = max(open_p, close_p, *moves)
            low_p = min(open_p, close_p, *moves)
            volume = random.uniform(1e6, 1e7)
            data.append([open_p, high_p, low_p, close_p, volume])
        return np.array(data)
    
    def reset(self):
        """Reset simulator."""
        self.price = self.initial_price
        self.prices = [self.initial_price]
        self.timestep = 0
        self.regime = "neutral"


# =============================================================================
# TRADING ENVIRONMENT
# =============================================================================

class TradingEnvironment:
    """
    Trading environment for simulation.
    
    Simulates:
    - Market data generation
    - Order execution with slippage
    - Position management
    - PnL calculation
    """
    
    def __init__(
        self,
        initial_equity: float = 10000,
        position_size_pct: float = 0.1,
        slippage_pct: float = 0.001,
        seed: Optional[int] = None
    ):
        self.initial_equity = initial_equity
        self.position_size_pct = position_size_pct
        self.slippage_pct = slippage_pct
        
        self.market = MarketSimulator(seed=seed)
        self.reset()
    
    def reset(self):
        """Reset environment."""
        self.market.reset()
        self.equity = self.initial_equity
        self.position = 0  # -1: short, 0: none, 1: long
        self.entry_price = 0
        self.trades = []
        self.equity_curve = [self.initial_equity]
    
    def step(self, action: int) -> Tuple[float, float, bool]:
        """
        Take an action and return (reward, price, done).
        
        Actions: 0=hold, 1=buy, 2=sell, 3=close
        """
        price = self.market.step()
        reward = 0
        
        # Calculate unrealized PnL
        if self.position != 0:
            unrealized = (price - self.entry_price) / self.entry_price * self.position
        else:
            unrealized = 0
        
        # Execute action
        if action == 1 and self.position <= 0:  # BUY
            if self.position == -1:  # Close short first
                reward = self._close_position(price)
            self._open_position(price, 1)
        
        elif action == 2 and self.position >= 0:  # SELL
            if self.position == 1:  # Close long first
                reward = self._close_position(price)
            self._open_position(price, -1)
        
        elif action == 3 and self.position != 0:  # CLOSE
            reward = self._close_position(price)
        
        # Update equity curve
        current_equity = self.equity
        if self.position != 0:
            current_equity += unrealized * self.equity * self.position_size_pct
        self.equity_curve.append(current_equity)
        
        # Check if done (bankrupt or max steps)
        done = current_equity < self.initial_equity * 0.5 or self.market.timestep > 10000
        
        return reward, price, done
    
    def _open_position(self, price: float, direction: int):
        """Open a position."""
        slippage = price * self.slippage_pct * (1 if direction == 1 else -1)
        self.entry_price = price + slippage
        self.position = direction
    
    def _close_position(self, price: float) -> float:
        """Close position and return PnL."""
        slippage = price * self.slippage_pct * (-1 if self.position == 1 else 1)
        exit_price = price + slippage
        
        pnl_pct = (exit_price - self.entry_price) / self.entry_price * self.position
        pnl_usd = pnl_pct * self.equity * self.position_size_pct
        
        self.equity += pnl_usd
        self.trades.append({
            "entry": self.entry_price,
            "exit": exit_price,
            "direction": self.position,
            "pnl": pnl_usd
        })
        
        self.position = 0
        self.entry_price = 0
        
        return pnl_pct * 100  # Return as percentage for reward
    
    def get_metrics(self) -> Dict[str, float]:
        """Calculate performance metrics."""
        equity_curve = np.array(self.equity_curve)
        returns = np.diff(equity_curve) / equity_curve[:-1]
        
        # Sharpe ratio (annualized)
        if len(returns) > 1 and returns.std() > 0:
            sharpe = np.sqrt(252) * returns.mean() / returns.std()
        else:
            sharpe = 0
        
        # Max drawdown
        peak = np.maximum.accumulate(equity_curve)
        drawdown = (equity_curve - peak) / peak
        max_dd = drawdown.min()
        
        # Win rate
        if self.trades:
            wins = sum(1 for t in self.trades if t["pnl"] > 0)
            win_rate = wins / len(self.trades)
        else:
            win_rate = 0
        
        return {
            "final_equity": self.equity,
            "total_pnl": self.equity - self.initial_equity,
            "sharpe_ratio": sharpe,
            "max_drawdown": max_dd,
            "win_rate": win_rate,
            "total_trades": len(self.trades)
        }


# =============================================================================
# SIMULATION UNIVERSE
# =============================================================================

class SimulationUniverse:
    """
    Parallel simulation environment manager.
    
    Features:
    - Run multiple simulations in parallel
    - Different market conditions
    - DNA/Agent evaluation
    - Continuous background evolution
    
    Usage:
        universe = SimulationUniverse(n_workers=4)
        
        # Run parallel simulations
        results = await universe.run_parallel_simulations(
            dna_population=[[10, 10, 200], [20, 15, 300], ...],
            episodes_per_dna=10
        )
        
        # Get best performer
        best = universe.get_best_result()
    """
    
    RESULTS_DIR = ROOT / "data" / "simulations"
    
    def __init__(self, n_workers: int = 4):
        self.n_workers = n_workers
        self.results: List[SimulationResult] = []
        self._lock = threading.Lock()
        self._running = False
        
        self.RESULTS_DIR.mkdir(parents=True, exist_ok=True)
    
    def _run_single_simulation(
        self,
        universe_id: int,
        dna: List[int],
        episodes: int = 1,
        steps_per_episode: int = 1000
    ) -> SimulationResult:
        """Run a single simulation with given DNA."""
        start_time = time.time()
        
        all_metrics = []
        
        for ep in range(episodes):
            env = TradingEnvironment(seed=universe_id * 1000 + ep)
            
            for step in range(steps_per_episode):
                # Simple DNA-based strategy
                prices = env.market.prices[-60:] if len(env.market.prices) >= 60 else env.market.prices
                
                if len(prices) >= 2:
                    # Use DNA to make decisions
                    short_ma = np.mean(prices[-dna[0]:]) if len(prices) >= dna[0] else prices[-1]
                    long_ma = np.mean(prices[-dna[1]:]) if len(prices) >= dna[1] else prices[-1]
                    
                    if short_ma > long_ma * (1 + dna[2] / 10000):
                        action = 1  # BUY
                    elif short_ma < long_ma * (1 - dna[2] / 10000):
                        action = 2  # SELL
                    else:
                        action = 0  # HOLD
                else:
                    action = 0
                
                _, _, done = env.step(action)
                if done:
                    break
            
            metrics = env.get_metrics()
            metrics["timesteps"] = step + 1
            all_metrics.append(metrics)
        
        # Average metrics across episodes
        avg_metrics = {
            k: np.mean([m[k] for m in all_metrics])
            for k in all_metrics[0].keys()
        }
        
        duration = time.time() - start_time
        
        return SimulationResult(
            simulation_id=f"sim_{universe_id}_{int(time.time())}",
            universe_id=universe_id,
            dna=dna,
            timesteps=int(avg_metrics["timesteps"]),
            final_equity=avg_metrics["final_equity"],
            total_pnl=avg_metrics["total_pnl"],
            max_drawdown=avg_metrics["max_drawdown"],
            sharpe_ratio=avg_metrics["sharpe_ratio"],
            win_rate=avg_metrics["win_rate"],
            total_trades=int(avg_metrics["total_trades"]),
            duration_seconds=duration
        )
    
    async def run_parallel_simulations(
        self,
        dna_population: List[List[int]],
        episodes_per_dna: int = 5,
        steps_per_episode: int = 1000
    ) -> List[SimulationResult]:
        """
        Run simulations in parallel for DNA population.
        
        Args:
            dna_population: List of DNA configurations to test
            episodes_per_dna: Episodes per DNA
            steps_per_episode: Steps per episode
        
        Returns:
            List of simulation results
        """
        loop = asyncio.get_event_loop()
        
        with ThreadPoolExecutor(max_workers=self.n_workers) as executor:
            tasks = [
                loop.run_in_executor(
                    executor,
                    self._run_single_simulation,
                    i, dna, episodes_per_dna, steps_per_episode
                )
                for i, dna in enumerate(dna_population)
            ]
            
            results = await asyncio.gather(*tasks)
        
        with self._lock:
            self.results.extend(results)
        
        return results
    
    def run_evolution_cycle(
        self,
        population_size: int = 20,
        generations: int = 10,
        episodes_per_dna: int = 3
    ) -> List[SimulationResult]:
        """
        Run a full evolution cycle.
        
        Uses genetic algorithm to evolve DNA population.
        """
        # Initialize random population
        population = [
            [random.randint(5, 50), random.randint(20, 100), random.randint(50, 500)]
            for _ in range(population_size)
        ]
        
        best_results = []
        
        for gen in range(generations):
            # Evaluate population
            results = asyncio.run(
                self.run_parallel_simulations(population, episodes_per_dna)
            )
            
            # Sort by fitness
            results.sort(key=lambda r: r.fitness, reverse=True)
            best_results.append(results[0])
            
            print(f"Gen {gen+1}: Best fitness = {results[0].fitness:.4f}, DNA = {results[0].dna}")
            
            # Selection - top 50%
            survivors = [r.dna for r in results[:population_size // 2]]
            
            # Crossover and mutation
            new_population = survivors.copy()
            while len(new_population) < population_size:
                parent1, parent2 = random.sample(survivors, 2)
                child = [
                    random.choice([p1, p2])
                    for p1, p2 in zip(parent1, parent2)
                ]
                # Mutation
                if random.random() < 0.3:
                    idx = random.randint(0, len(child) - 1)
                    child[idx] = max(1, child[idx] + random.randint(-20, 20))
                new_population.append(child)
            
            population = new_population
        
        return best_results
    
    def get_best_result(self) -> Optional[SimulationResult]:
        """Get the best result so far."""
        with self._lock:
            if not self.results:
                return None
            return max(self.results, key=lambda r: r.fitness)
    
    def save_results(self, filename: str = None):
        """Save results to file."""
        if filename is None:
            filename = f"sim_results_{datetime.now().strftime('%Y%m%d_%H%M%S')}.json"
        
        path = self.RESULTS_DIR / filename
        
        with self._lock:
            data = [r.to_dict() for r in self.results]
        
        with open(path, "w") as f:
            json.dump(data, f, indent=2, default=str)
        
        print(f"💾 Results saved to {path}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get universe statistics."""
        with self._lock:
            if not self.results:
                return {"total_simulations": 0}
            
            return {
                "total_simulations": len(self.results),
                "best_fitness": max(r.fitness for r in self.results),
                "avg_fitness": sum(r.fitness for r in self.results) / len(self.results),
                "total_trades": sum(r.total_trades for r in self.results)
            }


# =============================================================================
# BACKGROUND EVOLUTION DAEMON
# =============================================================================

class EvolutionDaemon:
    """
    Background daemon that continuously runs simulations and evolves.
    
    Runs 24/7 in the background, constantly improving DNA.
    """
    
    def __init__(self, universe: SimulationUniverse):
        self.universe = universe
        self._running = False
        self._thread = None
    
    def start(self):
        """Start the evolution daemon."""
        self._running = True
        self._thread = threading.Thread(target=self._run_loop, daemon=True)
        self._thread.start()
        print("🧬 Evolution daemon started")
    
    def stop(self):
        """Stop the daemon."""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        print("🧬 Evolution daemon stopped")
    
    def _run_loop(self):
        """Main evolution loop."""
        cycle = 0
        while self._running:
            try:
                cycle += 1
                print(f"\n🌌 Starting evolution cycle {cycle}...")
                
                results = self.universe.run_evolution_cycle(
                    population_size=10,
                    generations=5,
                    episodes_per_dna=2
                )
                
                best = results[-1] if results else None
                if best:
                    print(f"✨ Cycle {cycle} complete. Best: {best.fitness:.4f}")
                
                # Save periodically
                if cycle % 5 == 0:
                    self.universe.save_results()
                
                # Sleep between cycles
                time.sleep(60)
            
            except Exception as e:
                print(f"❌ Evolution error: {e}")
                time.sleep(10)


# Global instances
_universe: Optional[SimulationUniverse] = None
_daemon: Optional[EvolutionDaemon] = None


def get_simulation_universe() -> SimulationUniverse:
    """Get or create global simulation universe."""
    global _universe
    if _universe is None:
        _universe = SimulationUniverse()
    return _universe


def start_evolution_daemon():
    """Start the background evolution daemon."""
    global _universe, _daemon
    if _universe is None:
        _universe = SimulationUniverse()
    if _daemon is None:
        _daemon = EvolutionDaemon(_universe)
    _daemon.start()


if __name__ == "__main__":
    print("Simulation Universe Demo")
    print("=" * 60)
    
    universe = SimulationUniverse(n_workers=4)
    
    # Quick evolution
    print("\nRunning quick evolution (3 generations)...")
    results = universe.run_evolution_cycle(
        population_size=10,
        generations=3,
        episodes_per_dna=2
    )
    
    print(f"\nBest result: {universe.get_best_result()}")
    print(f"Stats: {universe.get_stats()}")
