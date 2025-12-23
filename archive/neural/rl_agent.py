# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN REINFORCEMENT LEARNING AGENT
Deep Q-Network (DQN) agent that learns to trade through experience.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import json
import random
import numpy as np
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Tuple, Any
from dataclasses import dataclass, field
from collections import deque

try:
    import torch
    import torch.nn as nn
    import torch.optim as optim
    import torch.nn.functional as F
    HAS_TORCH = True
except ImportError:
    HAS_TORCH = False


ROOT = Path(__file__).parent.parent


# =============================================================================
# ENVIRONMENT
# =============================================================================

@dataclass
class TradingState:
    """Current trading state for the agent."""
    prices: np.ndarray  # Recent price history
    position: int  # -1: short, 0: none, 1: long
    equity: float
    unrealized_pnl: float
    entry_price: float = 0.0
    
    def to_tensor(self) -> np.ndarray:
        """Convert to flat array for neural network."""
        # Normalize prices
        price_norm = (self.prices - self.prices.mean()) / (self.prices.std() + 1e-8)
        # Add position info
        return np.concatenate([
            price_norm.flatten(),
            [self.position, self.unrealized_pnl / 100, self.equity / 10000]
        ])


class TradingAction:
    """Possible trading actions."""
    HOLD = 0
    BUY = 1
    SELL = 2
    CLOSE = 3
    
    @classmethod
    def to_string(cls, action: int) -> str:
        return {0: "HOLD", 1: "BUY", 2: "SELL", 3: "CLOSE"}.get(action, "UNKNOWN")


# =============================================================================
# DQN NETWORK
# =============================================================================

if HAS_TORCH:
    
    class DQNetwork(nn.Module):
        """
        Deep Q-Network for trading.
        
        Input: State vector (prices + position info)
        Output: Q-values for each action
        """
        
        def __init__(self, state_size: int, action_size: int = 4):
            super().__init__()
            
            self.fc1 = nn.Linear(state_size, 256)
            self.fc2 = nn.Linear(256, 128)
            self.fc3 = nn.Linear(128, 64)
            self.fc4 = nn.Linear(64, action_size)
            
            self.bn1 = nn.BatchNorm1d(256)
            self.bn2 = nn.BatchNorm1d(128)
        
        def forward(self, x: torch.Tensor) -> torch.Tensor:
            x = F.relu(self.bn1(self.fc1(x)))
            x = F.relu(self.bn2(self.fc2(x)))
            x = F.relu(self.fc3(x))
            return self.fc4(x)
    
    
    class DuelingDQN(nn.Module):
        """
        Dueling DQN - separates value and advantage streams.
        Generally performs better than vanilla DQN.
        """
        
        def __init__(self, state_size: int, action_size: int = 4):
            super().__init__()
            
            self.feature = nn.Sequential(
                nn.Linear(state_size, 256),
                nn.ReLU(),
                nn.Linear(256, 128),
                nn.ReLU()
            )
            
            # Value stream
            self.value = nn.Sequential(
                nn.Linear(128, 64),
                nn.ReLU(),
                nn.Linear(64, 1)
            )
            
            # Advantage stream
            self.advantage = nn.Sequential(
                nn.Linear(128, 64),
                nn.ReLU(),
                nn.Linear(64, action_size)
            )
        
        def forward(self, x: torch.Tensor) -> torch.Tensor:
            features = self.feature(x)
            value = self.value(features)
            advantage = self.advantage(features)
            # Combine: Q = V + (A - mean(A))
            return value + advantage - advantage.mean(dim=1, keepdim=True)


# =============================================================================
# REPLAY BUFFER
# =============================================================================

@dataclass
class Experience:
    """Single experience tuple."""
    state: np.ndarray
    action: int
    reward: float
    next_state: np.ndarray
    done: bool


class ReplayBuffer:
    """Experience replay buffer for stable training."""
    
    def __init__(self, capacity: int = 100000):
        self.buffer = deque(maxlen=capacity)
    
    def push(self, experience: Experience):
        self.buffer.append(experience)
    
    def sample(self, batch_size: int) -> List[Experience]:
        return random.sample(self.buffer, min(batch_size, len(self.buffer)))
    
    def __len__(self):
        return len(self.buffer)


# =============================================================================
# RL AGENT
# =============================================================================

class TradingAgent:
    """
    Deep Q-Learning agent for trading.
    
    Features:
    - Dueling DQN architecture
    - Experience replay
    - Target network (soft update)
    - Epsilon-greedy exploration
    - Prioritized experience replay (optional)
    
    Usage:
        agent = TradingAgent(state_size=63)
        
        # Training loop
        for episode in range(1000):
            state = env.reset()
            while not done:
                action = agent.act(state)
                next_state, reward, done = env.step(action)
                agent.remember(state, action, reward, next_state, done)
                agent.train()
                state = next_state
    """
    
    MODEL_DIR = ROOT / "models" / "rl"
    
    def __init__(
        self,
        state_size: int,
        action_size: int = 4,
        learning_rate: float = 0.0001,
        gamma: float = 0.99,
        epsilon_start: float = 1.0,
        epsilon_end: float = 0.01,
        epsilon_decay: float = 0.995,
        batch_size: int = 64,
        tau: float = 0.001,
        device: str = "auto"
    ):
        if not HAS_TORCH:
            raise ImportError("PyTorch required for TradingAgent")
        
        self.state_size = state_size
        self.action_size = action_size
        self.gamma = gamma
        self.epsilon = epsilon_start
        self.epsilon_end = epsilon_end
        self.epsilon_decay = epsilon_decay
        self.batch_size = batch_size
        self.tau = tau
        
        # Device
        if device == "auto":
            self.device = torch.device("cuda" if torch.cuda.is_available() else "cpu")
        else:
            self.device = torch.device(device)
        
        # Networks
        self.policy_net = DuelingDQN(state_size, action_size).to(self.device)
        self.target_net = DuelingDQN(state_size, action_size).to(self.device)
        self.target_net.load_state_dict(self.policy_net.state_dict())
        self.target_net.eval()
        
        # Optimizer
        self.optimizer = optim.Adam(self.policy_net.parameters(), lr=learning_rate)
        
        # Replay buffer
        self.memory = ReplayBuffer()
        
        # Stats
        self.training_steps = 0
        self.episodes = 0
        self.total_reward = 0
        
        self.MODEL_DIR.mkdir(parents=True, exist_ok=True)
    
    def act(self, state: np.ndarray, training: bool = True) -> int:
        """
        Choose an action using epsilon-greedy policy.
        
        Args:
            state: Current state
            training: If True, use exploration
        
        Returns:
            Action index
        """
        if training and random.random() < self.epsilon:
            return random.randrange(self.action_size)
        
        self.policy_net.eval()
        with torch.no_grad():
            state_tensor = torch.FloatTensor(state).unsqueeze(0).to(self.device)
            q_values = self.policy_net(state_tensor)
            return q_values.argmax().item()
    
    def remember(
        self,
        state: np.ndarray,
        action: int,
        reward: float,
        next_state: np.ndarray,
        done: bool
    ):
        """Store experience in replay buffer."""
        self.memory.push(Experience(state, action, reward, next_state, done))
    
    def train(self) -> Optional[float]:
        """
        Train on a batch of experiences.
        
        Returns:
            Loss value or None if not enough samples
        """
        if len(self.memory) < self.batch_size:
            return None
        
        self.policy_net.train()
        
        # Sample batch
        batch = self.memory.sample(self.batch_size)
        
        states = torch.FloatTensor([e.state for e in batch]).to(self.device)
        actions = torch.LongTensor([e.action for e in batch]).to(self.device)
        rewards = torch.FloatTensor([e.reward for e in batch]).to(self.device)
        next_states = torch.FloatTensor([e.next_state for e in batch]).to(self.device)
        dones = torch.BoolTensor([e.done for e in batch]).to(self.device)
        
        # Current Q values
        current_q = self.policy_net(states).gather(1, actions.unsqueeze(1))
        
        # Next Q values (Double DQN)
        with torch.no_grad():
            next_actions = self.policy_net(next_states).argmax(1)
            next_q = self.target_net(next_states).gather(1, next_actions.unsqueeze(1))
            target_q = rewards.unsqueeze(1) + (self.gamma * next_q * (~dones).unsqueeze(1))
        
        # Loss
        loss = F.smooth_l1_loss(current_q, target_q)
        
        # Optimize
        self.optimizer.zero_grad()
        loss.backward()
        torch.nn.utils.clip_grad_norm_(self.policy_net.parameters(), 1.0)
        self.optimizer.step()
        
        # Soft update target network
        self._soft_update()
        
        # Decay epsilon
        self.epsilon = max(self.epsilon_end, self.epsilon * self.epsilon_decay)
        
        self.training_steps += 1
        
        return loss.item()
    
    def _soft_update(self):
        """Soft update target network."""
        for target_param, policy_param in zip(
            self.target_net.parameters(),
            self.policy_net.parameters()
        ):
            target_param.data.copy_(
                self.tau * policy_param.data + (1 - self.tau) * target_param.data
            )
    
    def save(self, tag: str = "latest"):
        """Save model to disk."""
        save_path = self.MODEL_DIR / tag
        save_path.mkdir(parents=True, exist_ok=True)
        
        torch.save({
            "policy_net": self.policy_net.state_dict(),
            "target_net": self.target_net.state_dict(),
            "optimizer": self.optimizer.state_dict(),
            "epsilon": self.epsilon,
            "training_steps": self.training_steps,
            "episodes": self.episodes,
        }, save_path / "agent.pt")
        
        print(f"💾 Agent saved to {save_path}")
    
    def load(self, tag: str = "latest") -> bool:
        """Load model from disk."""
        load_path = self.MODEL_DIR / tag / "agent.pt"
        
        if not load_path.exists():
            return False
        
        try:
            checkpoint = torch.load(load_path, map_location=self.device)
            self.policy_net.load_state_dict(checkpoint["policy_net"])
            self.target_net.load_state_dict(checkpoint["target_net"])
            self.optimizer.load_state_dict(checkpoint["optimizer"])
            self.epsilon = checkpoint.get("epsilon", self.epsilon_end)
            self.training_steps = checkpoint.get("training_steps", 0)
            self.episodes = checkpoint.get("episodes", 0)
            print(f"🤖 Agent loaded from {load_path}")
            return True
        except Exception as e:
            print(f"❌ Failed to load agent: {e}")
            return False
    
    def get_stats(self) -> Dict[str, Any]:
        """Get agent statistics."""
        return {
            "device": str(self.device),
            "epsilon": self.epsilon,
            "training_steps": self.training_steps,
            "episodes": self.episodes,
            "memory_size": len(self.memory),
            "parameters": sum(p.numel() for p in self.policy_net.parameters())
        }


# Global instance
_agent: Optional[TradingAgent] = None


def get_trading_agent(state_size: int = 63) -> TradingAgent:
    """Get or create global trading agent."""
    global _agent
    if _agent is None:
        _agent = TradingAgent(state_size=state_size)
    return _agent


if __name__ == "__main__":
    if HAS_TORCH:
        print("Trading Agent Demo")
        print("=" * 60)
        
        agent = TradingAgent(state_size=63)
        print(f"Device: {agent.device}")
        print(f"Stats: {agent.get_stats()}")
        
        # Simulate some experiences
        for i in range(100):
            state = np.random.randn(63)
            action = agent.act(state)
            next_state = np.random.randn(63)
            reward = np.random.randn() * 0.1
            done = i == 99
            
            agent.remember(state, action, reward, next_state, done)
        
        # Train
        for _ in range(10):
            loss = agent.train()
            if loss:
                print(f"Loss: {loss:.4f}")
        
        print(f"\nFinal stats: {agent.get_stats()}")
    else:
        print("PyTorch not installed. Run: pip install torch")
