# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN NEURAL MESH
The nervous system connecting all organs of the cyber organism.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import json
import asyncio
import threading
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional, Any, Callable
from dataclasses import dataclass, field
from enum import Enum

try:
    import redis
    HAS_REDIS = True
except ImportError:
    HAS_REDIS = False


ROOT = Path(__file__).parent.parent


# =============================================================================
# ORGAN TYPES
# =============================================================================

class OrganType(Enum):
    """Types of organs in GODBRAIN."""
    CORTEX = "cortex"           # Neural prediction
    RL_AGENT = "rl_agent"       # Trading decisions
    GENETICS = "genetics"       # DNA evolution
    SIMULATION = "simulation"   # Parallel universes
    SERAPH = "seraph"          # AI brain
    VOLTRAN = "voltran"        # Trading engine
    MARKET_FEED = "market_feed" # Data stream


@dataclass
class NeuralSignal:
    """Signal passed between organs."""
    source: OrganType
    target: OrganType
    signal_type: str
    payload: Dict[str, Any]
    timestamp: datetime = field(default_factory=datetime.now)
    priority: int = 5  # 1-10, higher = more important
    
    def to_dict(self) -> Dict:
        return {
            "source": self.source.value,
            "target": self.target.value,
            "signal_type": self.signal_type,
            "payload": self.payload,
            "timestamp": self.timestamp.isoformat(),
            "priority": self.priority
        }
    
    @classmethod
    def from_dict(cls, data: Dict) -> "NeuralSignal":
        return cls(
            source=OrganType(data["source"]),
            target=OrganType(data["target"]),
            signal_type=data["signal_type"],
            payload=data["payload"],
            timestamp=datetime.fromisoformat(data["timestamp"]),
            priority=data.get("priority", 5)
        )


# =============================================================================
# NEURAL PATHWAY
# =============================================================================

class NeuralPathway:
    """
    Neural pathway connecting organs.
    
    Uses Redis pub/sub for real-time communication.
    """
    
    CHANNEL_PREFIX = "godbrain:neural:"
    
    def __init__(self, organ_type: OrganType):
        self.organ_type = organ_type
        self._redis = None
        self._pubsub = None
        self._handlers: Dict[str, Callable] = {}
        self._running = False
        self._thread = None
    
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
            except Exception:
                self._redis = None
        return self._redis
    
    def send_signal(self, signal: NeuralSignal) -> bool:
        """Send a signal to another organ."""
        r = self._get_redis()
        if not r:
            return False
        
        try:
            channel = f"{self.CHANNEL_PREFIX}{signal.target.value}"
            r.publish(channel, json.dumps(signal.to_dict()))
            return True
        except Exception:
            return False
    
    def broadcast(self, signal_type: str, payload: Dict) -> bool:
        """Broadcast to all organs."""
        r = self._get_redis()
        if not r:
            return False
        
        try:
            signal = NeuralSignal(
                source=self.organ_type,
                target=self.organ_type,  # Will be broadcast
                signal_type=signal_type,
                payload=payload
            )
            r.publish(f"{self.CHANNEL_PREFIX}broadcast", json.dumps(signal.to_dict()))
            return True
        except Exception:
            return False
    
    def register_handler(self, signal_type: str, handler: Callable):
        """Register a handler for a signal type."""
        self._handlers[signal_type] = handler
    
    def start_listening(self):
        """Start listening for signals."""
        r = self._get_redis()
        if not r:
            return
        
        self._pubsub = r.pubsub()
        self._pubsub.subscribe(
            f"{self.CHANNEL_PREFIX}{self.organ_type.value}",
            f"{self.CHANNEL_PREFIX}broadcast"
        )
        
        self._running = True
        self._thread = threading.Thread(target=self._listen_loop, daemon=True)
        self._thread.start()
    
    def stop_listening(self):
        """Stop listening."""
        self._running = False
        if self._pubsub:
            self._pubsub.close()
    
    def _listen_loop(self):
        """Background listener loop."""
        while self._running:
            try:
                message = self._pubsub.get_message(timeout=1)
                if message and message["type"] == "message":
                    data = json.loads(message["data"])
                    signal = NeuralSignal.from_dict(data)
                    
                    if signal.signal_type in self._handlers:
                        self._handlers[signal.signal_type](signal)
            except Exception:
                time.sleep(0.1)


# =============================================================================
# NEURAL MESH
# =============================================================================

class NeuralMesh:
    """
    The complete nervous system of GODBRAIN.
    
    Connects all organs and enables:
    - Real-time signal propagation
    - Organ state synchronization
    - Collective decision making
    - System-wide awareness
    
    Usage:
        mesh = NeuralMesh()
        mesh.register_organ(OrganType.CORTEX, cortex_instance)
        mesh.register_organ(OrganType.RL_AGENT, agent_instance)
        mesh.start()
        
        # Later
        mesh.send(OrganType.CORTEX, OrganType.RL_AGENT, "prediction", {...})
    """
    
    def __init__(self):
        self.organs: Dict[OrganType, Any] = {}
        self.pathways: Dict[OrganType, NeuralPathway] = {}
        self._running = False
        self._heartbeat_thread = None
    
    def register_organ(self, organ_type: OrganType, instance: Any):
        """Register an organ with the mesh."""
        self.organs[organ_type] = instance
        self.pathways[organ_type] = NeuralPathway(organ_type)
        print(f"🧬 Registered organ: {organ_type.value}")
    
    def send(
        self,
        source: OrganType,
        target: OrganType,
        signal_type: str,
        payload: Dict,
        priority: int = 5
    ) -> bool:
        """Send a signal from one organ to another."""
        if source not in self.pathways:
            return False
        
        signal = NeuralSignal(
            source=source,
            target=target,
            signal_type=signal_type,
            payload=payload,
            priority=priority
        )
        
        return self.pathways[source].send_signal(signal)
    
    def broadcast(self, source: OrganType, signal_type: str, payload: Dict) -> bool:
        """Broadcast a signal to all organs."""
        if source not in self.pathways:
            return False
        
        return self.pathways[source].broadcast(signal_type, payload)
    
    def start(self):
        """Start all pathways and begin neural activity."""
        self._running = True
        
        # Start all pathways
        for organ_type, pathway in self.pathways.items():
            pathway.start_listening()
            print(f"⚡ Started pathway: {organ_type.value}")
        
        # Start heartbeat
        self._heartbeat_thread = threading.Thread(target=self._heartbeat_loop, daemon=True)
        self._heartbeat_thread.start()
        
        print("🧠 Neural Mesh activated!")
    
    def stop(self):
        """Stop all pathways."""
        self._running = False
        
        for pathway in self.pathways.values():
            pathway.stop_listening()
        
        print("🧠 Neural Mesh deactivated")
    
    def _heartbeat_loop(self):
        """Periodic heartbeat to check organ health."""
        while self._running:
            try:
                status = self.get_system_status()
                
                # Broadcast system status
                self.broadcast(
                    OrganType.CORTEX,
                    "system_status",
                    status
                )
                
                time.sleep(30)
            except Exception:
                time.sleep(5)
    
    def get_system_status(self) -> Dict[str, Any]:
        """Get status of all organs."""
        status = {
            "timestamp": datetime.now().isoformat(),
            "organs": {}
        }
        
        for organ_type, instance in self.organs.items():
            organ_status = {"connected": True}
            
            # Try to get stats from organ
            if hasattr(instance, "get_stats"):
                try:
                    organ_status["stats"] = instance.get_stats()
                except Exception:
                    pass
            
            status["organs"][organ_type.value] = organ_status
        
        return status
    
    def get_collective_decision(
        self,
        symbol: str,
        price_data: Any,
        weights: Optional[Dict[OrganType, float]] = None
    ) -> Dict[str, Any]:
        """
        Get collective decision from all relevant organs.
        
        Combines:
        - Neural Cortex prediction
        - RL Agent decision
        - Genetic DNA rules
        """
        if weights is None:
            weights = {
                OrganType.CORTEX: 0.3,
                OrganType.RL_AGENT: 0.4,
                OrganType.GENETICS: 0.3
            }
        
        decisions = {}
        scores = {"BUY": 0, "SELL": 0, "HOLD": 0}
        
        # Get Cortex prediction
        if OrganType.CORTEX in self.organs:
            try:
                cortex = self.organs[OrganType.CORTEX]
                prediction = cortex.predict(symbol, price_data)
                decisions["cortex"] = prediction.trend
                
                if prediction.trend == "UP":
                    scores["BUY"] += weights[OrganType.CORTEX] * prediction.confidence
                elif prediction.trend == "DOWN":
                    scores["SELL"] += weights[OrganType.CORTEX] * prediction.confidence
                else:
                    scores["HOLD"] += weights[OrganType.CORTEX] * prediction.confidence
            except Exception:
                pass
        
        # Get RL Agent action
        if OrganType.RL_AGENT in self.organs:
            try:
                agent = self.organs[OrganType.RL_AGENT]
                state = price_data.flatten()[:63] if len(price_data.flatten()) >= 63 else None
                if state is not None:
                    action = agent.act(state, training=False)
                    action_map = {0: "HOLD", 1: "BUY", 2: "SELL", 3: "HOLD"}
                    decisions["rl_agent"] = action_map[action]
                    scores[action_map[action]] += weights[OrganType.RL_AGENT]
            except Exception:
                pass
        
        # Calculate final decision
        final_action = max(scores, key=scores.get)
        confidence = scores[final_action] / sum(weights.values())
        
        return {
            "symbol": symbol,
            "action": final_action,
            "confidence": confidence,
            "organ_decisions": decisions,
            "scores": scores,
            "timestamp": datetime.now().isoformat()
        }


# =============================================================================
# GODBRAIN ORGANISM
# =============================================================================

class GodbrainOrganism:
    """
    The complete cyber organism.
    
    Integrates all components:
    - Neural Cortex (prediction)
    - RL Agent (decisions)
    - Simulation Universe (experiments)
    - Genetics (evolution)
    - Seraph (intelligence)
    - VOLTRAN (execution)
    
    Runs 24/7, continuously evolving and improving.
    """
    
    def __init__(self):
        self.mesh = NeuralMesh()
        self.birth_date = datetime.now()
        self._organs_initialized = False
    
    def initialize_organs(self):
        """Initialize all organs."""
        # Import organs
        try:
            from neural.cortex import NeuralCortex
            cortex = NeuralCortex()
            self.mesh.register_organ(OrganType.CORTEX, cortex)
        except Exception as e:
            print(f"⚠️ Cortex init failed: {e}")
        
        try:
            from neural.rl_agent import TradingAgent
            agent = TradingAgent(state_size=63)
            self.mesh.register_organ(OrganType.RL_AGENT, agent)
        except Exception as e:
            print(f"⚠️ RL Agent init failed: {e}")
        
        try:
            from neural.simulation_universe import SimulationUniverse
            universe = SimulationUniverse()
            self.mesh.register_organ(OrganType.SIMULATION, universe)
        except Exception as e:
            print(f"⚠️ Simulation init failed: {e}")
        
        self._organs_initialized = True
        print("🧠 All organs initialized!")
    
    def start(self):
        """Activate the organism."""
        if not self._organs_initialized:
            self.initialize_organs()
        
        self.mesh.start()
        print(f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                         GODBRAIN ORGANISM ACTIVATED                           ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  Birth: {self.birth_date.strftime('%Y-%m-%d %H:%M:%S')}                                             ║
║  Organs: {len(self.mesh.organs)}                                                              ║
║  Status: ONLINE                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
        """)
    
    def stop(self):
        """Deactivate the organism."""
        self.mesh.stop()
        print("💤 GODBRAIN Organism entering sleep mode...")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get organism statistics."""
        age = datetime.now() - self.birth_date
        
        return {
            "birth_date": self.birth_date.isoformat(),
            "age_seconds": age.total_seconds(),
            "organs_count": len(self.mesh.organs),
            "system_status": self.mesh.get_system_status()
        }


# Global instance
_organism: Optional[GodbrainOrganism] = None


def get_organism() -> GodbrainOrganism:
    """Get or create global organism."""
    global _organism
    if _organism is None:
        _organism = GodbrainOrganism()
    return _organism


if __name__ == "__main__":
    print("Neural Mesh Demo")
    print("=" * 60)
    
    organism = GodbrainOrganism()
    organism.initialize_organs()
    
    print(f"\nOrganism stats: {organism.get_stats()}")
    
    # Test collective decision
    import numpy as np
    test_data = np.random.randn(60, 5)
    
    decision = organism.mesh.get_collective_decision("DOGE/USDT", test_data)
    print(f"\nCollective decision: {decision}")
