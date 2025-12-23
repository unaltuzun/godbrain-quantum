#!/usr/bin/env python3
"""
🔄 GODBRAIN FEEDBACK LOOP
=========================
Connects backtesting results to genetics lab for intelligent DNA evolution.

Flow:
  Backtest Results → Redis → Genetics Lab → Better DNA → Trading

This creates a TRUE LEARNING SYSTEM:
- DNA that performs well in backtest gets higher fitness
- DNA that performs poorly gets lower fitness
- Evolution becomes guided by REAL performance data
"""

import os
import sys
import json
import asyncio
import redis
from datetime import datetime, timedelta
from pathlib import Path
from typing import Dict, Optional

# Add parent to path
sys.path.insert(0, str(Path(__file__).parent.parent))

from backtesting import BacktestEngine, BacktestConfig, GODBRAINStrategy, HistoricalDataManager


class FeedbackLoop:
    """
    Feedback loop that:
    1. Takes DNA from genetics lab
    2. Runs backtest on it
    3. Sends performance metrics back
    4. Genetics uses this as fitness function
    """
    
    # Redis keys
    BEST_DNA_KEY = "godbrain:genetics:best_dna"
    BEST_META_KEY = "godbrain:genetics:best_meta"
    FEEDBACK_KEY = "godbrain:feedback:latest"
    FEEDBACK_HISTORY_KEY = "godbrain:feedback:history"
    
    def __init__(self):
        self.redis = redis.Redis(
            host=os.getenv("REDIS_HOST", "127.0.0.1"),
            port=int(os.getenv("REDIS_PORT", "16379")),
            password=os.getenv("REDIS_PASS", "voltran2024"),
            decode_responses=True
        )
        self.data_manager = HistoricalDataManager()
        
    async def run_feedback_cycle(
        self,
        symbols: list = ["BTC/USDT"],
        days: int = 90,
        capital: float = 10000
    ) -> Dict:
        """
        Run one feedback cycle:
        1. Get current best DNA
        2. Backtest it
        3. Store results
        """
        print("\n" + "=" * 60)
        print("🔄 GODBRAIN FEEDBACK LOOP")
        print("=" * 60)
        
        # 1. Get current DNA
        dna = self._get_current_dna()
        if not dna:
            print("[FEEDBACK] No DNA found in Redis")
            return {"error": "no_dna"}
        
        print(f"[FEEDBACK] DNA Source: {dna.get('source', 'unknown')}")
        print(f"[FEEDBACK] DNA Score: {dna.get('score', 'N/A')}")
        
        # 2. Run backtest
        end_date = datetime.now()
        start_date = end_date - timedelta(days=days)
        
        config = BacktestConfig(
            start_date=start_date,
            end_date=end_date,
            initial_capital=capital,
            timeframe="1h"
        )
        
        engine = BacktestEngine(config)
        
        # Download/load data
        for symbol in symbols:
            try:
                df = await self.data_manager.load(
                    symbol, "1h", start_date, end_date, "binance"
                )
                engine.data[symbol] = df
                print(f"[FEEDBACK] Loaded {len(df)} bars for {symbol}")
            except Exception as e:
                print(f"[FEEDBACK] Error loading {symbol}: {e}")
                return {"error": f"data_load_failed: {e}"}
        
        if not engine.data:
            return {"error": "no_data"}
        
        # Create strategy with Redis DNA
        strategy = GODBRAINStrategy(dna_source="redis")
        engine.set_strategy(strategy)
        
        print(f"\n[FEEDBACK] Running backtest: {start_date.date()} → {end_date.date()}")
        
        try:
            result = await engine.run()
        except Exception as e:
            print(f"[FEEDBACK] Backtest error: {e}")
            return {"error": f"backtest_failed: {e}"}
        
        # 3. Calculate feedback score
        feedback = self._calculate_feedback(result, dna)
        
        # 4. Store feedback in Redis
        self._store_feedback(feedback)
        
        # 5. Print summary
        print(result.summary())
        print("\n" + "=" * 60)
        print("📊 FEEDBACK SCORE")
        print("=" * 60)
        print(f"  DNA Score (Lab):       {dna.get('score', 0):.1f}")
        print(f"  Backtest Return:       {result.total_return:.2%}")
        print(f"  Sharpe Ratio:          {result.sharpe_ratio:.2f}")
        print(f"  Max Drawdown:          {result.max_drawdown:.2%}")
        print(f"  → FEEDBACK SCORE:      {feedback['feedback_score']:.1f}")
        print("=" * 60)
        
        return feedback
    
    def _get_current_dna(self) -> Optional[Dict]:
        """Get current DNA from Redis."""
        try:
            # Try active DNA first
            active = self.redis.get("godbrain:trading:active_dna")
            if active:
                return json.loads(active)
            
            # Fallback to best DNA
            dna = self.redis.get(self.BEST_DNA_KEY)
            meta = self.redis.get(self.BEST_META_KEY)
            
            if dna:
                result = {"dna": json.loads(dna), "source": "genetics"}
                if meta:
                    result.update(json.loads(meta))
                return result
            
            return None
        except Exception as e:
            print(f"[FEEDBACK] Redis error: {e}")
            return None
    
    def _calculate_feedback(self, result: 'BacktestResult', dna: Dict) -> Dict:
        """
        Calculate feedback score from backtest results.
        
        Scoring:
        - Base: 50 points
        - Return bonus/penalty: ±25 points
        - Sharpe bonus: +15 points max
        - Drawdown penalty: -10 points max
        - Win rate bonus: +10 points max
        """
        score = 50.0
        
        # Return component (±25)
        if result.total_return > 0:
            score += min(result.total_return * 100, 25)
        else:
            score += max(result.total_return * 100, -25)
        
        # Sharpe component (+15 max)
        if result.sharpe_ratio > 0:
            score += min(result.sharpe_ratio * 5, 15)
        
        # Drawdown penalty (-10 max)
        score -= min(abs(result.max_drawdown) * 50, 10)
        
        # Win rate bonus (+10 max)
        score += result.win_rate * 10
        
        # Clamp to 0-100
        score = max(0, min(100, score))
        
        return {
            "feedback_score": score,
            "original_score": dna.get("score", 50),
            "total_return": result.total_return,
            "sharpe_ratio": result.sharpe_ratio,
            "sortino_ratio": result.sortino_ratio,
            "max_drawdown": result.max_drawdown,
            "win_rate": result.win_rate,
            "total_trades": result.total_trades,
            "profit_factor": result.profit_factor,
            "final_equity": result.final_equity,
            "dna": dna.get("dna"),
            "timestamp": datetime.now().isoformat()
        }
    
    def _store_feedback(self, feedback: Dict) -> None:
        """Store feedback in Redis for genetics lab to consume."""
        try:
            # Store latest feedback
            self.redis.set(self.FEEDBACK_KEY, json.dumps(feedback))
            
            # Append to history (keep last 100)
            self.redis.lpush(self.FEEDBACK_HISTORY_KEY, json.dumps(feedback))
            self.redis.ltrim(self.FEEDBACK_HISTORY_KEY, 0, 99)
            
            # Update genetics fitness if significantly different
            score_diff = abs(feedback["feedback_score"] - feedback["original_score"])
            if score_diff > 10:
                print(f"[FEEDBACK] Score diff {score_diff:.1f} - updating genetics fitness")
                
                # Update the best_meta with backtest-validated score
                meta = self.redis.get(self.BEST_META_KEY)
                if meta:
                    meta_dict = json.loads(meta)
                    meta_dict["backtest_score"] = feedback["feedback_score"]
                    meta_dict["backtest_return"] = feedback["total_return"]
                    meta_dict["backtest_sharpe"] = feedback["sharpe_ratio"]
                    meta_dict["backtest_time"] = feedback["timestamp"]
                    self.redis.set(self.BEST_META_KEY, json.dumps(meta_dict))
            
            print(f"[FEEDBACK] Stored in Redis: {self.FEEDBACK_KEY}")
            
        except Exception as e:
            print(f"[FEEDBACK] Failed to store: {e}")
    
    async def run_continuous(self, interval_hours: int = 6):
        """Run feedback loop continuously."""
        print(f"""
╔═══════════════════════════════════════════════════════════╗
║           🔄 FEEDBACK LOOP - CONTINUOUS MODE              ║
║           Interval: {interval_hours} hours                               ║
╚═══════════════════════════════════════════════════════════╝
        """)
        
        while True:
            try:
                await self.run_feedback_cycle()
            except Exception as e:
                print(f"[FEEDBACK] Cycle error: {e}")
            
            print(f"\n[FEEDBACK] Next cycle in {interval_hours} hours...")
            await asyncio.sleep(interval_hours * 3600)


async def main():
    import argparse
    
    parser = argparse.ArgumentParser(description='GODBRAIN Feedback Loop')
    parser.add_argument('--symbols', nargs='+', default=['BTC/USDT'])
    parser.add_argument('--days', type=int, default=90)
    parser.add_argument('--capital', type=float, default=10000)
    parser.add_argument('--continuous', action='store_true')
    parser.add_argument('--interval', type=int, default=6, help='Hours between cycles')
    
    args = parser.parse_args()
    
    loop = FeedbackLoop()
    
    if args.continuous:
        await loop.run_continuous(args.interval)
    else:
        result = await loop.run_feedback_cycle(args.symbols, args.days, args.capital)
        print(f"\nResult: {json.dumps(result, indent=2, default=str)}")


if __name__ == "__main__":
    asyncio.run(main())
