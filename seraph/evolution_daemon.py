#!/usr/bin/env python3
# ==============================================================================
# SERAPH EVOLUTION DAEMON - Continuous Self-Improvement
# ==============================================================================
"""
Weridata Deployment Script

Bu daemon Weridata sunucusunda 7/24 çalışır ve:
1. Local LLM ile sınırsız inference
2. Trading stratejilerini simüle eder
3. Örüntüleri öğrenir
4. DNA parametrelerini evrimleştirir
5. Seraph'ı sürekli geliştirir

Kullanım:
    python evolution_daemon.py

Gereksinimler:
    - Ollama kurulu ve çalışıyor (curl -fsSL https://ollama.com/install.sh | sh)
    - Mistral modeli indirilmiş (ollama pull mistral)
"""

import os
import sys
import time
import signal
import logging
import argparse
from pathlib import Path
from datetime import datetime

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from seraph.brain.local_llm import LocalLLM
from seraph.simulation.self_improve import SelfImprover
from seraph.simulation.trade_sim import TradeSimulator
from seraph.cache.semantic_cache import SemanticCache
from seraph.cache.pattern_db import PatternDB
from seraph.knowledge.codebase import CodebaseIndex
from seraph.knowledge.strategies import StrategyKnowledge

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(Path(__file__).parent.parent / 'logs' / 'evolution.log')
    ]
)
logger = logging.getLogger("seraph.daemon")


class EvolutionDaemon:
    """
    Main evolution daemon.
    
    Orchestrates all self-improvement processes.
    """
    
    def __init__(self):
        self.running = False
        
        # Initialize components
        logger.info("Initializing Seraph Evolution Engine...")
        
        self.local_llm = LocalLLM(model="mistral")
        self.cache = SemanticCache()
        self.patterns = PatternDB()
        self.codebase = CodebaseIndex()
        self.strategies = StrategyKnowledge()
        self.improver = SelfImprover(local_llm=self.local_llm)
        self.simulator = TradeSimulator()
        
        # Stats
        self.start_time = None
        self.cycles_completed = 0
        
    def check_ollama(self) -> bool:
        """Check if Ollama is available"""
        if self.local_llm.is_available():
            models = self.local_llm.list_models()
            logger.info(f"Ollama available. Models: {models}")
            return True
        else:
            logger.warning("Ollama not available. Install with: curl -fsSL https://ollama.com/install.sh | sh")
            return False
    
    def run_cycle(self):
        """Run one improvement cycle"""
        cycle_start = time.time()
        logger.info(f"=== Cycle {self.cycles_completed + 1} starting ===")
        
        # 1. Evolution - Evolve DNA parameters
        try:
            logger.info("Phase 1: DNA Evolution")
            evo_run = self.improver.run_evolution_cycle(n_generations=5, population_size=10)
            logger.info(f"  - Generations: {evo_run.generations}")
            logger.info(f"  - Lessons: {evo_run.lessons_learned}")
            logger.info(f"  - Best Sharpe: {evo_run.best_fitness:.2f}")
        except Exception as e:
            logger.error(f"Evolution error: {e}")
        
        # 2. Strategy Testing - Test current strategies
        try:
            logger.info("Phase 2: Strategy Testing")
            strategies = self.strategies.recommend_for_regime("ALL")[:3]
            for strategy in strategies:
                result = self.simulator.run_simulation(strategy.dna_params, n_trades=50)
                self.strategies.record_performance(
                    strategy.id,
                    trades=result.total_trades,
                    wins=result.winning_trades,
                    total_pnl_pct=sum(t.pnl_pct for t in result.trades),
                    max_drawdown=result.max_drawdown
                )
                logger.info(f"  - {strategy.name}: Sharpe {result.sharpe_ratio:.2f}, PnL ${result.total_pnl:.2f}")
        except Exception as e:
            logger.error(f"Strategy testing error: {e}")
        
        # 3. Pattern Learning - Learn from codebase
        try:
            logger.info("Phase 3: Codebase Analysis")
            critical = self.codebase.get_critical_functions()
            logger.info(f"  - Critical functions: {len(critical)}")
        except Exception as e:
            logger.error(f"Codebase analysis error: {e}")
        
        # 4. Local LLM Training (if available)
        if self.local_llm.is_available():
            try:
                logger.info("Phase 4: Local LLM Query")
                lessons = self.improver.get_lessons(min_confidence=0.7)
                if lessons:
                    prompt = f"Based on {len(lessons)} learned lessons, what trading insight can you provide?"
                    response = self.local_llm.generate(prompt, max_tokens=200)
                    if response.success:
                        logger.info(f"  - LLM insight: {response.content[:100]}...")
            except Exception as e:
                logger.error(f"Local LLM error: {e}")
        
        # 5. Save state
        self.cache.save()
        
        cycle_time = time.time() - cycle_start
        self.cycles_completed += 1
        
        logger.info(f"=== Cycle {self.cycles_completed} complete ({cycle_time:.1f}s) ===")
        
        return {
            "cycle": self.cycles_completed,
            "duration_seconds": cycle_time,
            "lessons": len(self.improver.get_lessons())
        }
    
    def run(self, interval_minutes: int = 5, max_cycles: int = None):
        """
        Run daemon continuously.
        
        Args:
            interval_minutes: Time between cycles
            max_cycles: Max cycles (None = infinite)
        """
        self.running = True
        self.start_time = datetime.now()
        
        logger.info("=" * 60)
        logger.info("SERAPH EVOLUTION DAEMON STARTING")
        logger.info(f"Interval: {interval_minutes} minutes")
        logger.info(f"Max cycles: {max_cycles or 'infinite'}")
        logger.info("=" * 60)
        
        # Check Ollama
        ollama_ok = self.check_ollama()
        if not ollama_ok:
            logger.warning("Running without local LLM - limited functionality")
        
        # Signal handling for graceful shutdown
        def signal_handler(signum, frame):
            logger.info("Shutdown signal received")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Main loop
        while self.running:
            try:
                self.run_cycle()
            except Exception as e:
                logger.exception(f"Cycle error: {e}")
            
            # Check max cycles
            if max_cycles and self.cycles_completed >= max_cycles:
                logger.info(f"Max cycles ({max_cycles}) reached")
                break
            
            # Wait for next cycle
            logger.info(f"Sleeping {interval_minutes} minutes until next cycle...")
            for _ in range(interval_minutes * 60):
                if not self.running:
                    break
                time.sleep(1)
        
        # Cleanup
        logger.info("Daemon shutting down...")
        self.cache.save()
        
        # Final stats
        uptime = datetime.now() - self.start_time
        stats = {
            "uptime": str(uptime),
            "cycles_completed": self.cycles_completed,
            "total_lessons": len(self.improver.get_lessons()),
            "cache_entries": self.cache.get_stats()["entries"],
            "strategies": len(self.strategies._strategies)
        }
        
        logger.info("Final Statistics:")
        for key, value in stats.items():
            logger.info(f"  {key}: {value}")
        
        logger.info("SERAPH EVOLUTION DAEMON STOPPED")


def main():
    parser = argparse.ArgumentParser(description="Seraph Evolution Daemon")
    parser.add_argument("--interval", type=int, default=5, help="Minutes between cycles (default: 5)")
    parser.add_argument("--cycles", type=int, default=None, help="Max cycles (default: infinite)")
    parser.add_argument("--once", action="store_true", help="Run once and exit")
    
    args = parser.parse_args()
    
    daemon = EvolutionDaemon()
    
    if args.once:
        daemon.run_cycle()
    else:
        daemon.run(interval_minutes=args.interval, max_cycles=args.cycles)


if __name__ == "__main__":
    main()

