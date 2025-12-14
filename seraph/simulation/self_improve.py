# ==============================================================================
# SELF IMPROVER - Autonomous Evolution Engine
# ==============================================================================
"""
Seraph's self-improvement engine.

The core idea:
1. Generate variations of responses/strategies
2. Simulate outcomes
3. Select best performers
4. Learn from patterns
5. Repeat (evolution)

This runs continuously on Weridata, improving Seraph
without using Claude API credits.
"""

import json
import time
import random
import logging
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass, asdict
from pathlib import Path
from datetime import datetime
import threading

logger = logging.getLogger("seraph.simulation.improve")


@dataclass
class Lesson:
    """A learned lesson from simulation"""
    id: str
    category: str  # "trading", "response", "strategy"
    insight: str
    confidence: float  # 0-1
    evidence_count: int
    timestamp: str
    source: str  # "simulation", "feedback", "manual"


@dataclass
class EvolutionRun:
    """Record of an evolution run"""
    id: str
    start_time: str
    end_time: Optional[str]
    generations: int
    simulations: int
    lessons_learned: int
    best_fitness: float
    improvements: List[str]


class SelfImprover:
    """
    Autonomous self-improvement engine.
    
    Runs continuous evolution:
    1. Pattern Discovery - Find patterns in successful interactions
    2. Strategy Evolution - Evolve DNA parameters through simulation
    3. Response Optimization - Learn better response templates
    4. Knowledge Distillation - Extract insights from Claude responses
    
    This uses LOCAL LLM (Ollama) for all inference - zero API cost.
    """
    
    def __init__(
        self,
        lessons_dir: Optional[Path] = None,
        local_llm=None  # Optional LocalLLM instance
    ):
        self.lessons_dir = lessons_dir or Path(__file__).parent.parent.parent / "logs" / "lessons"
        self.lessons_dir.mkdir(parents=True, exist_ok=True)
        
        self.local_llm = local_llm
        
        # Learned lessons
        self._lessons: Dict[str, Lesson] = {}
        self._load_lessons()
        
        # Evolution state
        self._running = False
        self._thread: Optional[threading.Thread] = None
        self._stats = {
            "total_simulations": 0,
            "total_lessons": 0,
            "evolution_runs": 0,
            "last_run": None
        }
    
    def _load_lessons(self):
        """Load learned lessons from disk"""
        lessons_file = self.lessons_dir / "lessons.json"
        if lessons_file.exists():
            try:
                with open(lessons_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for lesson_data in data.get("lessons", []):
                        lesson = Lesson(**lesson_data)
                        self._lessons[lesson.id] = lesson
                logger.info(f"Loaded {len(self._lessons)} lessons")
            except Exception as e:
                logger.warning(f"Failed to load lessons: {e}")
    
    def _save_lessons(self):
        """Save lessons to disk"""
        lessons_file = self.lessons_dir / "lessons.json"
        try:
            data = {
                "lessons": [asdict(l) for l in self._lessons.values()],
                "stats": self._stats
            }
            with open(lessons_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save lessons: {e}")
    
    def add_lesson(
        self,
        category: str,
        insight: str,
        confidence: float = 0.5,
        source: str = "simulation"
    ) -> Lesson:
        """
        Add a new learned lesson.
        
        Args:
            category: Lesson category
            insight: What was learned
            confidence: Confidence level (0-1)
            source: Where this came from
        
        Returns:
            Created Lesson
        """
        lesson_id = f"{category}_{int(time.time())}_{random.randint(1000, 9999)}"
        
        lesson = Lesson(
            id=lesson_id,
            category=category,
            insight=insight,
            confidence=confidence,
            evidence_count=1,
            timestamp=datetime.now().isoformat(),
            source=source
        )
        
        self._lessons[lesson_id] = lesson
        self._stats["total_lessons"] += 1
        self._save_lessons()
        
        logger.info(f"New lesson learned: {insight[:50]}...")
        return lesson
    
    def reinforce_lesson(self, lesson_id: str):
        """Reinforce a lesson with new evidence"""
        if lesson_id in self._lessons:
            lesson = self._lessons[lesson_id]
            lesson.evidence_count += 1
            lesson.confidence = min(1.0, lesson.confidence + 0.1)
            self._save_lessons()
    
    def get_lessons(self, category: Optional[str] = None, min_confidence: float = 0.5) -> List[Lesson]:
        """Get lessons, optionally filtered"""
        lessons = self._lessons.values()
        
        if category:
            lessons = [l for l in lessons if l.category == category]
        
        lessons = [l for l in lessons if l.confidence >= min_confidence]
        
        return sorted(lessons, key=lambda l: l.confidence, reverse=True)
    
    def run_evolution_cycle(
        self,
        n_generations: int = 10,
        population_size: int = 20
    ) -> EvolutionRun:
        """
        Run one evolution cycle.
        
        This:
        1. Generates variations of strategies
        2. Simulates each strategy
        3. Selects best performers
        4. Extracts lessons
        
        Returns:
            EvolutionRun record
        """
        from .trade_sim import TradeSimulator
        
        run_id = f"evo_{int(time.time())}"
        run = EvolutionRun(
            id=run_id,
            start_time=datetime.now().isoformat(),
            end_time=None,
            generations=0,
            simulations=0,
            lessons_learned=0,
            best_fitness=0,
            improvements=[]
        )
        
        simulator = TradeSimulator()
        
        # Initial population - random DNA variations
        population = [
            {
                "stop_loss_pct": random.uniform(1.0, 5.0),
                "take_profit_pct": random.uniform(2.0, 10.0),
                "rsi_buy_level": random.uniform(20, 40),
                "rsi_sell_level": random.uniform(60, 80),
                "position_size_factor": random.uniform(0.5, 2.0)
            }
            for _ in range(population_size)
        ]
        
        for gen in range(n_generations):
            run.generations = gen + 1
            
            # Evaluate population
            results = simulator.compare_dna_params(population, n_trades=50)
            run.simulations += population_size * 50
            self._stats["total_simulations"] += population_size * 50
            
            # Best performer
            best = results[0]
            run.best_fitness = max(run.best_fitness, best["sharpe"])
            
            # Extract lessons from best performers
            if best["sharpe"] > 1.5:
                lesson = self.add_lesson(
                    category="trading",
                    insight=f"High Sharpe ({best['sharpe']:.2f}) with SL={best['params']['stop_loss_pct']:.1f}%, TP={best['params']['take_profit_pct']:.1f}%",
                    confidence=0.6 + best["sharpe"] / 10,
                    source="simulation"
                )
                run.lessons_learned += 1
                run.improvements.append(f"Gen {gen+1}: Sharpe {best['sharpe']:.2f}")
            
            # Selection - keep top 50%
            survivors = [r["params"] for r in results[:population_size // 2]]
            
            # Crossover and mutation
            new_population = survivors.copy()
            while len(new_population) < population_size:
                # Select two parents
                p1, p2 = random.sample(survivors, 2)
                
                # Crossover
                child = {}
                for key in p1.keys():
                    child[key] = random.choice([p1[key], p2[key]])
                    
                    # Mutation (10% chance)
                    if random.random() < 0.1:
                        child[key] *= random.uniform(0.8, 1.2)
                
                new_population.append(child)
            
            population = new_population
        
        run.end_time = datetime.now().isoformat()
        self._stats["evolution_runs"] += 1
        self._stats["last_run"] = run.end_time
        self._save_lessons()
        
        logger.info(f"Evolution complete: {run.generations} gen, {run.lessons_learned} lessons, best Sharpe {run.best_fitness:.2f}")
        
        return run
    
    def start_continuous_evolution(self, interval_seconds: int = 300):
        """
        Start continuous evolution in background.
        
        Runs evolution cycles every `interval_seconds`.
        Use on Weridata for 24/7 self-improvement.
        """
        if self._running:
            logger.warning("Evolution already running")
            return
        
        self._running = True
        
        def evolution_loop():
            while self._running:
                try:
                    logger.info("Starting evolution cycle...")
                    self.run_evolution_cycle(n_generations=5, population_size=10)
                except Exception as e:
                    logger.error(f"Evolution error: {e}")
                
                # Wait for next cycle
                for _ in range(interval_seconds):
                    if not self._running:
                        break
                    time.sleep(1)
        
        self._thread = threading.Thread(target=evolution_loop, daemon=True)
        self._thread.start()
        logger.info(f"Continuous evolution started (interval: {interval_seconds}s)")
    
    def stop_continuous_evolution(self):
        """Stop continuous evolution"""
        self._running = False
        if self._thread:
            self._thread.join(timeout=5)
        logger.info("Evolution stopped")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get self-improvement statistics"""
        return {
            **self._stats,
            "total_lessons_stored": len(self._lessons),
            "lessons_by_category": {
                cat: len([l for l in self._lessons.values() if l.category == cat])
                for cat in set(l.category for l in self._lessons.values())
            },
            "high_confidence_lessons": len([l for l in self._lessons.values() if l.confidence > 0.8])
        }

