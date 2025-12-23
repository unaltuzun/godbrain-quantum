# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN NEURAL TRAINER
24/7 continuous training daemon for neural networks.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import json
import time
import asyncio
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any
import numpy as np

try:
    import torch
    import torch.nn as nn
    HAS_TORCH = True
    DEVICE = torch.device("cuda" if torch.cuda.is_available() else "cpu")
except ImportError:
    HAS_TORCH = False
    DEVICE = None

try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False


ROOT = Path(__file__).parent.parent


class NeuralTrainer:
    """
    Continuous neural network trainer.
    
    Features:
    - 24/7 training loop
    - Automatic data collection from Redis
    - Model checkpointing
    - Performance tracking
    - GPU optimization
    
    Usage:
        trainer = NeuralTrainer()
        trainer.run()  # Runs forever
    """
    
    MODEL_DIR = ROOT / "models" / "neural"
    CHECKPOINT_INTERVAL = 100  # Save every N batches
    
    def __init__(self):
        if not HAS_TORCH:
            raise ImportError("PyTorch required for NeuralTrainer")
        
        self.device = DEVICE
        self.training_steps = 0
        self.best_loss = float('inf')
        
        # Redis connection
        self._redis = None
        
        # Initialize models
        from neural.cortex import NeuralCortex
        from neural.rl_agent import TradingAgent
        
        self.cortex = NeuralCortex(device=str(self.device))
        self.agent = TradingAgent(state_size=63, device=str(self.device))
        
        # Load existing models
        self.cortex.load_models()
        self.agent.load()
        
        self.MODEL_DIR.mkdir(parents=True, exist_ok=True)
        
        print(f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                      GODBRAIN NEURAL TRAINER                                  ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  Device: {str(self.device):<67} ║
║  CUDA Available: {str(torch.cuda.is_available()):<59} ║
║  GPU Name: {torch.cuda.get_device_name(0) if torch.cuda.is_available() else 'N/A':<65} ║
╚═══════════════════════════════════════════════════════════════════════════════╝
        """)
    
    def _get_redis(self):
        """Get Redis connection."""
        if self._redis is None and HAS_REDIS:
            try:
                self._redis = redis.Redis(
                    host=os.getenv("REDIS_HOST", "localhost"),
                    port=int(os.getenv("REDIS_PORT", 6379)),
                    password=os.getenv("REDIS_PASS", ""),
                    decode_responses=True
                )
                self._redis.ping()
            except Exception as e:
                print(f"Redis connection failed: {e}")
                self._redis = None
        return self._redis
    
    def collect_training_data(self) -> Optional[Dict]:
        """Collect training data from Redis."""
        r = self._get_redis()
        if not r:
            return None
        
        try:
            # Get recent price data
            prices = r.lrange("market:prices:DOGE/USDT", 0, 100)
            if not prices:
                return None
            
            price_data = [json.loads(p) for p in prices]
            
            # Convert to numpy
            data = np.array([
                [p.get("open", 0), p.get("high", 0), p.get("low", 0), 
                 p.get("close", 0), p.get("volume", 0)]
                for p in price_data
            ])
            
            return {"prices": data, "symbol": "DOGE/USDT"}
        
        except Exception as e:
            print(f"Data collection error: {e}")
            return None
    
    def train_cortex_step(self, data: np.ndarray) -> float:
        """Train cortex on price data."""
        if len(data) < 61:
            return 0.0
        
        # Create training samples
        total_loss = 0.0
        n_samples = 0
        
        for i in range(len(data) - 61):
            x = data[i:i+60]
            y = (data[i+60, 3] - data[i+59, 3]) / data[i+59, 3] * 100  # % change
            
            loss = self.cortex.train_step(x, y)
            total_loss += loss
            n_samples += 1
        
        return total_loss / max(1, n_samples)
    
    def train_agent_step(self, data: np.ndarray) -> float:
        """Train RL agent on simulated trades."""
        if len(data) < 64:
            return 0.0
        
        # Simulate trading episode
        from neural.simulation_universe import TradingEnvironment
        
        env = TradingEnvironment()
        state = data[:63].flatten()
        
        for step in range(100):
            action = self.agent.act(state, training=True)
            reward, price, done = env.step(action)
            
            next_state = np.roll(state, -5)
            next_state[-5:] = [price, price, price, price, 1e6]
            
            self.agent.remember(state, action, reward, next_state, done)
            loss = self.agent.train()
            
            state = next_state
            if done:
                break
        
        self.agent.episodes += 1
        return loss or 0.0
    
    def save_checkpoint(self, tag: str = "latest"):
        """Save all model checkpoints."""
        self.cortex.save_models(tag)
        self.agent.save(tag)
        
        # Save training stats
        stats = {
            "training_steps": self.training_steps,
            "best_loss": self.best_loss,
            "timestamp": datetime.now().isoformat(),
            "device": str(self.device)
        }
        
        with open(self.MODEL_DIR / "training_stats.json", "w") as f:
            json.dump(stats, f, indent=2)
        
        print(f"💾 Checkpoint saved at step {self.training_steps}")
    
    def run(self):
        """Main training loop - runs forever."""
        print("🚀 Starting continuous training...")
        
        while True:
            try:
                # Collect data
                data = self.collect_training_data()
                
                if data is not None and len(data.get("prices", [])) > 60:
                    prices = data["prices"]
                    
                    # Train cortex
                    cortex_loss = self.train_cortex_step(prices)
                    
                    # Train agent
                    agent_loss = self.train_agent_step(prices)
                    
                    self.training_steps += 1
                    
                    # Log progress
                    if self.training_steps % 10 == 0:
                        print(f"Step {self.training_steps}: Cortex Loss={cortex_loss:.6f}, Agent Loss={agent_loss:.6f}")
                    
                    # Checkpoint
                    if self.training_steps % self.CHECKPOINT_INTERVAL == 0:
                        self.save_checkpoint()
                    
                    # Track best
                    if cortex_loss < self.best_loss:
                        self.best_loss = cortex_loss
                        self.save_checkpoint("best")
                
                else:
                    # No data, generate synthetic training
                    synthetic = np.random.randn(100, 5) * 0.01 + 0.32
                    synthetic[:, 4] = np.abs(synthetic[:, 4]) * 1e6
                    
                    cortex_loss = self.train_cortex_step(synthetic)
                    self.training_steps += 1
                    
                    if self.training_steps % 50 == 0:
                        print(f"Step {self.training_steps} (synthetic): Loss={cortex_loss:.6f}")
                
                # Brief pause
                time.sleep(1)
            
            except KeyboardInterrupt:
                print("\n🛑 Training interrupted. Saving...")
                self.save_checkpoint()
                break
            
            except Exception as e:
                print(f"❌ Training error: {e}")
                time.sleep(10)


def main():
    """Entry point for neural trainer."""
    trainer = NeuralTrainer()
    trainer.run()


if __name__ == "__main__":
    main()
