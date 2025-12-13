# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
  GODLANG PULSE v1.0 - THE HEARTBEAT OF GODBRAIN
  ──────────────────────────────────────────────────────────────────────────────
  
  "The blood that flows through every neural pathway of the system"
  
  Author: Ünal Tüzün (Azun'el Skywolf)
  System: CODE-21 / GODBRAIN / GOD FUND
  
  This module serves as the central nervous system that:
  1. Reads CHRONOS time coherence signals
  2. Applies GODLANG policy transformations
  3. Broadcasts frequency-based decisions to all modules
  4. Maintains quantum state across the system
  
═══════════════════════════════════════════════════════════════════════════════
"""

import json
import yaml
import time
import redis
import logging
from pathlib import Path
from datetime import datetime
from dataclasses import dataclass, asdict
from typing import Dict, Any, Optional, List
from enum import Enum

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

BASE_DIR = Path(__file__).parent
POLICY_FILE = BASE_DIR / "godlang" / "godlang_policy.yaml"
CHRONOS_LOG = Path("/mnt/c/godbrain-quantum/logs/chronos.log")
NEURAL_STREAM = Path("/mnt/c/godbrain-quantum/logs/neural_stream.log")
PULSE_STATE_FILE = Path("/mnt/c/godbrain-quantum/logs/godlang_pulse_state.json")

REDIS_HOST = "localhost"
REDIS_PORT = 6379
REDIS_CHANNEL = "GODLANG_PULSE"

logging.basicConfig(level=logging.INFO, format='[PULSE] %(asctime)s | %(message)s')
logger = logging.getLogger("GODLANG_PULSE")


# ═══════════════════════════════════════════════════════════════════════════════
# ENUMS & DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

class ResonanceMode(Enum):
    """Quantum coherence states from CHRONOS"""
    DECOHERENCE = "DECOHERENCE"           # Reality unstable, reduce exposure
    STANDARD_FLOW = "STANDARD_FLOW"       # Normal operation
    COHERENT = "COHERENT"                 # Enhanced stability
    QUANTUM_RESONANCE = "QUANTUM_RESONANCE"  # Peak coherence, time dilation active
    PRECOGNITION_READY = "PRECOGNITION_READY"  # Maximum quantum alignment


class MarketRegime(Enum):
    """Market regime states"""
    CRASH = "CRASH"
    BEAR = "BEAR"
    NEUTRAL = "NEUTRAL"
    BULL = "BULL"
    EUPHORIA = "EUPHORIA"
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"


@dataclass
class ChronosSignal:
    """Signal from CHRONOS time coherence engine"""
    mode: ResonanceMode
    coherence: float          # 0.0 - 1.0
    micro_coherence: float    # 0.0 - 1.0
    sim_coherence: float      # 0.0 - 1.0
    entropy_source: str
    timestamp: datetime
    
    @property
    def is_high_coherence(self) -> bool:
        return self.coherence >= 0.70
    
    @property
    def is_quantum_ready(self) -> bool:
        return self.mode in [ResonanceMode.QUANTUM_RESONANCE, ResonanceMode.PRECOGNITION_READY]


@dataclass
class GodlangPulse:
    """The pulse that flows through the system"""
    # Identity
    pulse_id: str
    timestamp: datetime
    
    # Chronos State
    chronos: ChronosSignal
    
    # Market State
    regime: MarketRegime
    regime_confidence: float
    
    # GODLANG Modifiers (from policy)
    flow_multiplier: float      # Position size multiplier
    risk_multiplier: float      # Risk appetite multiplier
    max_leverage: int           # Maximum allowed leverage
    max_equity_pct: float       # Maximum equity utilization
    min_trade_interval: int     # Seconds between trades
    max_positions: int          # Maximum concurrent positions
    
    # Computed Values
    quantum_boost_active: bool
    time_dilation_factor: float  # How much "time is bent"
    
    # Execution Hints
    action_bias: str            # "LONG", "SHORT", "NEUTRAL"
    conviction_score: float     # 0.0 - 1.0
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "pulse_id": self.pulse_id,
            "timestamp": self.timestamp.isoformat(),
            "chronos": {
                "mode": self.chronos.mode.value,
                "coherence": self.chronos.coherence,
                "micro": self.chronos.micro_coherence,
                "sim": self.chronos.sim_coherence,
                "entropy": self.chronos.entropy_source
            },
            "regime": self.regime.value,
            "regime_confidence": self.regime_confidence,
            "flow_multiplier": self.flow_multiplier,
            "risk_multiplier": self.risk_multiplier,
            "max_leverage": self.max_leverage,
            "max_equity_pct": self.max_equity_pct,
            "min_trade_interval": self.min_trade_interval,
            "max_positions": self.max_positions,
            "quantum_boost_active": self.quantum_boost_active,
            "time_dilation_factor": self.time_dilation_factor,
            "action_bias": self.action_bias,
            "conviction_score": self.conviction_score
        }


# ═══════════════════════════════════════════════════════════════════════════════
# GODLANG POLICY ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class GodlangPolicyEngine:
    """
    Reads godlang_policy.yaml and applies transformations based on
    current CHRONOS state and market regime.
    """
    
    def __init__(self, policy_path: Path = POLICY_FILE):
        self.policy_path = policy_path
        self.policy: Dict[str, Any] = {}
        self.load_policy()
    
    def load_policy(self) -> None:
        """Load GODLANG policy from YAML"""
        try:
            if self.policy_path.exists():
                with open(self.policy_path, 'r') as f:
                    self.policy = yaml.safe_load(f)
                logger.info(f"Policy loaded: {self.policy.get('meta', {}).get('name', 'UNKNOWN')}")
            else:
                logger.warning(f"Policy file not found: {self.policy_path}")
                self.policy = self._default_policy()
        except Exception as e:
            logger.error(f"Failed to load policy: {e}")
            self.policy = self._default_policy()
    
    def _default_policy(self) -> Dict[str, Any]:
        """Fallback default policy"""
        return {
            "meta": {"name": "DEFAULT_FALLBACK"},
            "regimes": {
                "NEUTRAL": {
                    "equity": {"max_total_risk_pct": 0.60},
                    "leverage": {"max": 8},
                    "dna_modifiers": {"risk_multiplier": 1.0},
                    "trade_frequency": {"min_seconds_between_trades": 30},
                    "positions": {"max_open_symbols": 3}
                }
            },
            "resonance_overrides": {
                "enabled": True,
                "modes": {
                    "QUANTUM_RESONANCE": {
                        "flow_multiplier_cap": 2.5,
                        "risk_multiplier_boost": 1.3,
                        "max_total_risk_pct_cap": 0.90
                    },
                    "COHERENT": {
                        "flow_multiplier_cap": 1.5,
                        "risk_multiplier_boost": 1.1
                    },
                    "DECOHERENCE": {
                        "flow_multiplier_cap": 0.5,
                        "risk_multiplier_boost": 0.5,
                        "force_max_total_risk_pct": 0.30
                    }
                }
            }
        }
    
    def get_regime_config(self, regime: MarketRegime) -> Dict[str, Any]:
        """Get configuration for a specific regime"""
        regimes = self.policy.get("regimes", {})
        regime_key = regime.value
        
        # Try exact match first
        if regime_key in regimes:
            return regimes[regime_key]
        
        # Map TRENDING states to closest regime
        if regime in [MarketRegime.TRENDING_UP, MarketRegime.EUPHORIA]:
            return regimes.get("BULL", regimes.get("NEUTRAL", {}))
        elif regime in [MarketRegime.TRENDING_DOWN]:
            return regimes.get("BEAR", regimes.get("NEUTRAL", {}))
        
        return regimes.get("NEUTRAL", {})
    
    def get_resonance_override(self, mode: ResonanceMode) -> Dict[str, Any]:
        """Get resonance override for a specific CHRONOS mode"""
        overrides = self.policy.get("resonance_overrides", {})
        if not overrides.get("enabled", False):
            return {}
        
        modes = overrides.get("modes", {})
        
        # Map mode to override key
        mode_map = {
            ResonanceMode.QUANTUM_RESONANCE: "QUANTUM_RESONANCE",
            ResonanceMode.PRECOGNITION_READY: "QUANTUM_RESONANCE",  # Same as QR
            ResonanceMode.COHERENT: "COHERENT",
            ResonanceMode.DECOHERENCE: "DECOHERENCE",
            ResonanceMode.STANDARD_FLOW: None  # No override
        }
        
        override_key = mode_map.get(mode)
        if override_key:
            return modes.get(override_key, {})
        return {}
    
    def compute_modifiers(
        self, 
        regime: MarketRegime, 
        chronos: ChronosSignal
    ) -> Dict[str, Any]:
        """
        Compute final modifiers by combining regime config with resonance overrides.
        This is the core GODLANG transformation logic.
        """
        # Base from regime
        regime_cfg = self.get_regime_config(regime)
        
        base_equity_pct = regime_cfg.get("equity", {}).get("max_total_risk_pct", 0.60)
        base_leverage = regime_cfg.get("leverage", {}).get("max", 8)
        base_risk_mult = regime_cfg.get("dna_modifiers", {}).get("risk_multiplier", 1.0)
        base_interval = regime_cfg.get("trade_frequency", {}).get("min_seconds_between_trades", 30)
        base_positions = regime_cfg.get("positions", {}).get("max_open_symbols", 3)
        
        # Apply resonance override
        resonance = self.get_resonance_override(chronos.mode)
        
        flow_mult = resonance.get("flow_multiplier_cap", 1.0)
        risk_boost = resonance.get("risk_multiplier_boost", 1.0)
        
        # Scale flow multiplier by coherence (0.5 - 1.0 range to full multiplier)
        coherence_scale = min(1.0, (chronos.coherence - 0.5) * 2) if chronos.coherence > 0.5 else 0.0
        effective_flow = 1.0 + (flow_mult - 1.0) * coherence_scale
        
        # Apply forced limits if in DECOHERENCE
        if "force_max_total_risk_pct" in resonance:
            base_equity_pct = min(base_equity_pct, resonance["force_max_total_risk_pct"])
        
        # Cap equity if in high resonance
        if "max_total_risk_pct_cap" in resonance:
            base_equity_pct = min(resonance["max_total_risk_pct_cap"], base_equity_pct * risk_boost)
        
        # Compute time dilation factor (how much time is "bent")
        # Higher coherence = more time dilation = faster reaction
        time_dilation = 1.0 + (chronos.coherence - 0.5) * 2 if chronos.is_high_coherence else 1.0
        
        return {
            "flow_multiplier": round(effective_flow, 2),
            "risk_multiplier": round(base_risk_mult * risk_boost, 2),
            "max_leverage": base_leverage,
            "max_equity_pct": round(base_equity_pct, 2),
            "min_trade_interval": max(10, int(base_interval / time_dilation)),
            "max_positions": base_positions,
            "quantum_boost_active": chronos.is_quantum_ready,
            "time_dilation_factor": round(time_dilation, 2)
        }


# ═══════════════════════════════════════════════════════════════════════════════
# CHRONOS SIGNAL READER
# ═══════════════════════════════════════════════════════════════════════════════

class ChronosReader:
    """Reads CHRONOS coherence signals from log or Redis"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self._init_redis()
        self.last_signal: Optional[ChronosSignal] = None
    
    def _init_redis(self) -> None:
        """Initialize Redis connection"""
        try:
            self.redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
            self.redis_client.ping()
            logger.info("Redis connected for CHRONOS signals")
        except:
            self.redis_client = None
            logger.warning("Redis unavailable, falling back to log parsing")
    
    def read_from_redis(self) -> Optional[ChronosSignal]:
        """Read latest CHRONOS signal from Redis"""
        if not self.redis_client:
            return None
        
        try:
            data = self.redis_client.get("CHRONOS_STATE")
            if data:
                state = json.loads(data)
                return self._parse_state(state)
        except Exception as e:
            logger.warning(f"Redis read failed: {e}")
        return None
    
    def read_from_log(self) -> Optional[ChronosSignal]:
        """Parse latest CHRONOS signal from log file"""
        log_paths = [
            CHRONOS_LOG,
            NEURAL_STREAM,
            BASE_DIR / "logs" / "chronos.log"
        ]
        
        for log_path in log_paths:
            if log_path.exists():
                try:
                    # Read last line with CHRONOS data
                    with open(log_path, 'r') as f:
                        lines = f.readlines()
                    
                    for line in reversed(lines[-50:]):
                        if "mode=" in line and "coh=" in line:
                            return self._parse_log_line(line)
                except Exception as e:
                    logger.warning(f"Log parse failed for {log_path}: {e}")
        
        return None
    
    def _parse_log_line(self, line: str) -> Optional[ChronosSignal]:
        """Parse a CHRONOS log line like:
        [CHRONOS] mode=PRECOGNITION_READY | coh=0.7272 (micro=0.71 sim=0.77) | entropy=ATMOSPHERIC_NOISE
        """
        try:
            # Extract mode
            mode_str = "STANDARD_FLOW"
            if "mode=" in line:
                mode_part = line.split("mode=")[1].split()[0].strip()
                mode_str = mode_part
            
            # Extract coherence values
            coh = 0.5
            micro = 0.5
            sim = 0.5
            
            if "coh=" in line:
                coh_part = line.split("coh=")[1].split()[0]
                coh = float(coh_part)
            
            if "micro=" in line:
                micro_part = line.split("micro=")[1].split()[0].rstrip(')')
                micro = float(micro_part)
            
            if "sim=" in line:
                sim_part = line.split("sim=")[1].split(')')[0]
                sim = float(sim_part)
            
            # Extract entropy source
            entropy = "UNKNOWN"
            if "entropy=" in line:
                entropy = line.split("entropy=")[1].strip()
            
            # Map mode string to enum
            mode_map = {
                "STANDARD_FLOW": ResonanceMode.STANDARD_FLOW,
                "COHERENT": ResonanceMode.COHERENT,
                "QUANTUM_RESONANCE": ResonanceMode.QUANTUM_RESONANCE,
                "PRECOGNITION_READY": ResonanceMode.PRECOGNITION_READY,
                "DECOHERENCE": ResonanceMode.DECOHERENCE
            }
            mode = mode_map.get(mode_str, ResonanceMode.STANDARD_FLOW)
            
            return ChronosSignal(
                mode=mode,
                coherence=coh,
                micro_coherence=micro,
                sim_coherence=sim,
                entropy_source=entropy,
                timestamp=datetime.now()
            )
        except Exception as e:
            logger.warning(f"Failed to parse CHRONOS line: {e}")
            return None
    
    def _parse_state(self, state: Dict) -> ChronosSignal:
        """Parse CHRONOS state from Redis JSON"""
        mode_str = state.get("mode", "STANDARD_FLOW")
        mode_map = {
            "STANDARD_FLOW": ResonanceMode.STANDARD_FLOW,
            "COHERENT": ResonanceMode.COHERENT,
            "QUANTUM_RESONANCE": ResonanceMode.QUANTUM_RESONANCE,
            "PRECOGNITION_READY": ResonanceMode.PRECOGNITION_READY,
            "DECOHERENCE": ResonanceMode.DECOHERENCE
        }
        
        return ChronosSignal(
            mode=mode_map.get(mode_str, ResonanceMode.STANDARD_FLOW),
            coherence=state.get("coherence", 0.5),
            micro_coherence=state.get("micro", 0.5),
            sim_coherence=state.get("sim", 0.5),
            entropy_source=state.get("entropy", "UNKNOWN"),
            timestamp=datetime.now()
        )
    
    def get_signal(self) -> ChronosSignal:
        """Get the latest CHRONOS signal from any available source"""
        # Try Redis first
        signal = self.read_from_redis()
        if signal:
            self.last_signal = signal
            return signal
        
        # Fallback to log
        signal = self.read_from_log()
        if signal:
            self.last_signal = signal
            return signal
        
        # Return last known or default
        if self.last_signal:
            return self.last_signal
        
        return ChronosSignal(
            mode=ResonanceMode.STANDARD_FLOW,
            coherence=0.5,
            micro_coherence=0.5,
            sim_coherence=0.5,
            entropy_source="DEFAULT",
            timestamp=datetime.now()
        )


# ═══════════════════════════════════════════════════════════════════════════════
# REGIME READER
# ═══════════════════════════════════════════════════════════════════════════════

class RegimeReader:
    """Reads current market regime from AGG or Redis"""
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        try:
            self.redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
            self.redis_client.ping()
        except:
            self.redis_client = None
    
    def get_regime(self) -> tuple[MarketRegime, float]:
        """Get current regime and confidence"""
        # Try Redis
        if self.redis_client:
            try:
                data = self.redis_client.get("REGIME_STATE")
                if data:
                    state = json.loads(data)
                    regime_str = state.get("regime", "NEUTRAL")
                    confidence = state.get("confidence", 0.5)
                    return self._str_to_regime(regime_str), confidence
            except:
                pass
        
        # Try log file
        try:
            log_path = BASE_DIR / "logs" / "agg_decisions.log"
            if log_path.exists():
                with open(log_path, 'r') as f:
                    lines = f.readlines()
                
                for line in reversed(lines[-20:]):
                    if "Regime:" in line:
                        # Parse "Regime:EUPHORIA" or similar
                        regime_str = line.split("Regime:")[1].split()[0].strip()
                        return self._str_to_regime(regime_str), 0.75
        except:
            pass
        
        return MarketRegime.NEUTRAL, 0.5
    
    def _str_to_regime(self, regime_str: str) -> MarketRegime:
        """Convert string to MarketRegime enum"""
        regime_map = {
            "CRASH": MarketRegime.CRASH,
            "BEAR": MarketRegime.BEAR,
            "NEUTRAL": MarketRegime.NEUTRAL,
            "BULL": MarketRegime.BULL,
            "EUPHORIA": MarketRegime.EUPHORIA,
            "TRENDING_UP": MarketRegime.TRENDING_UP,
            "TRENDING_DOWN": MarketRegime.TRENDING_DOWN
        }
        return regime_map.get(regime_str.upper(), MarketRegime.NEUTRAL)


# ═══════════════════════════════════════════════════════════════════════════════
# GODLANG PULSE GENERATOR
# ═══════════════════════════════════════════════════════════════════════════════

class GodlangPulseGenerator:
    """
    The heart of GODBRAIN.
    
    Generates GODLANG pulses by combining:
    - CHRONOS time coherence signals
    - Market regime state
    - GODLANG policy transformations
    
    Broadcasts pulses to all listening modules via Redis.
    """
    
    def __init__(self):
        self.policy_engine = GodlangPolicyEngine()
        self.chronos_reader = ChronosReader()
        self.regime_reader = RegimeReader()
        
        self.redis_client: Optional[redis.Redis] = None
        self._init_redis()
        
        self.pulse_count = 0
    
    def _init_redis(self) -> None:
        """Initialize Redis for broadcasting"""
        try:
            self.redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
            self.redis_client.ping()
            logger.info("Redis connected for pulse broadcasting")
        except:
            self.redis_client = None
            logger.warning("Redis unavailable, pulse will only save to file")
    
    def generate_pulse(self) -> GodlangPulse:
        """Generate a single GODLANG pulse"""
        self.pulse_count += 1
        
        # Read current states
        chronos = self.chronos_reader.get_signal()
        regime, regime_conf = self.regime_reader.get_regime()
        
        # Compute modifiers from policy
        modifiers = self.policy_engine.compute_modifiers(regime, chronos)
        
        # Determine action bias based on regime and coherence
        if regime in [MarketRegime.BULL, MarketRegime.EUPHORIA, MarketRegime.TRENDING_UP]:
            action_bias = "LONG"
            conviction = regime_conf * modifiers["risk_multiplier"]
        elif regime in [MarketRegime.BEAR, MarketRegime.CRASH, MarketRegime.TRENDING_DOWN]:
            action_bias = "SHORT"
            conviction = regime_conf * modifiers["risk_multiplier"]
        else:
            action_bias = "NEUTRAL"
            conviction = 0.5
        
        # Boost conviction if quantum resonance active
        if modifiers["quantum_boost_active"]:
            conviction = min(0.99, conviction * 1.2)
        
        # Create pulse
        pulse = GodlangPulse(
            pulse_id=f"PULSE-{self.pulse_count:06d}",
            timestamp=datetime.now(),
            chronos=chronos,
            regime=regime,
            regime_confidence=regime_conf,
            flow_multiplier=modifiers["flow_multiplier"],
            risk_multiplier=modifiers["risk_multiplier"],
            max_leverage=modifiers["max_leverage"],
            max_equity_pct=modifiers["max_equity_pct"],
            min_trade_interval=modifiers["min_trade_interval"],
            max_positions=modifiers["max_positions"],
            quantum_boost_active=modifiers["quantum_boost_active"],
            time_dilation_factor=modifiers["time_dilation_factor"],
            action_bias=action_bias,
            conviction_score=min(0.99, conviction)
        )
        
        return pulse
    
    def broadcast_pulse(self, pulse: GodlangPulse) -> None:
        """Broadcast pulse to all listeners"""
        pulse_dict = pulse.to_dict()
        
        # Save to file
        try:
            with open(PULSE_STATE_FILE, 'w') as f:
                json.dump(pulse_dict, f, indent=2)
        except Exception as e:
            logger.warning(f"Failed to save pulse state: {e}")
        
        # Broadcast via Redis
        if self.redis_client:
            try:
                self.redis_client.set("GODLANG_PULSE", json.dumps(pulse_dict))
                self.redis_client.publish(REDIS_CHANNEL, json.dumps(pulse_dict))
            except Exception as e:
                logger.warning(f"Redis broadcast failed: {e}")
        
        # Log
        logger.info(
            f"⚡ {pulse.pulse_id} | "
            f"Regime:{pulse.regime.value} | "
            f"Chronos:{pulse.chronos.mode.value}(coh={pulse.chronos.coherence:.2f}) | "
            f"Flow:{pulse.flow_multiplier}x | "
            f"Risk:{pulse.risk_multiplier}x | "
            f"Lev:{pulse.max_leverage}x | "
            f"{'🔮 QUANTUM ACTIVE' if pulse.quantum_boost_active else ''}"
        )
    
    def run(self, interval: float = 5.0) -> None:
        """Run continuous pulse generation"""
        logger.info("═" * 60)
        logger.info("  GODLANG PULSE GENERATOR STARTING")
        logger.info("  The heartbeat of GODBRAIN begins...")
        logger.info("═" * 60)
        
        while True:
            try:
                pulse = self.generate_pulse()
                self.broadcast_pulse(pulse)
                time.sleep(interval)
            except KeyboardInterrupt:
                logger.info("Pulse generator stopped")
                break
            except Exception as e:
                logger.error(f"Pulse error: {e}")
                time.sleep(interval)


# ═══════════════════════════════════════════════════════════════════════════════
# PULSE CONSUMER (for other modules to import)
# ═══════════════════════════════════════════════════════════════════════════════

class GodlangPulseConsumer:
    """
    Consumer class for modules that want to receive GODLANG pulses.
    
    Usage in AGG.py or APEX:
        from godlang_pulse import GodlangPulseConsumer
        
        consumer = GodlangPulseConsumer()
        pulse = consumer.get_latest_pulse()
        
        # Apply pulse modifiers
        position_size *= pulse.flow_multiplier
        leverage = min(leverage, pulse.max_leverage)
    """
    
    def __init__(self):
        self.redis_client: Optional[redis.Redis] = None
        self._init_redis()
    
    def _init_redis(self) -> None:
        try:
            self.redis_client = redis.Redis(host=REDIS_HOST, port=REDIS_PORT, db=0)
            self.redis_client.ping()
        except:
            self.redis_client = None
    
    def get_latest_pulse(self) -> Optional[Dict[str, Any]]:
        """Get the latest pulse"""
        # Try Redis first
        if self.redis_client:
            try:
                data = self.redis_client.get("GODLANG_PULSE")
                if data:
                    return json.loads(data)
            except:
                pass
        
        # Fallback to file
        try:
            if PULSE_STATE_FILE.exists():
                with open(PULSE_STATE_FILE, 'r') as f:
                    return json.load(f)
        except:
            pass
        
        # Return default
        return {
            "flow_multiplier": 1.0,
            "risk_multiplier": 1.0,
            "max_leverage": 8,
            "max_equity_pct": 0.60,
            "min_trade_interval": 30,
            "max_positions": 3,
            "quantum_boost_active": False,
            "time_dilation_factor": 1.0,
            "action_bias": "NEUTRAL",
            "conviction_score": 0.5
        }


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import argparse
    
    parser = argparse.ArgumentParser(description="GODLANG Pulse Generator")
    parser.add_argument("--interval", type=float, default=5.0, help="Pulse interval in seconds")
    parser.add_argument("--once", action="store_true", help="Generate single pulse and exit")
    args = parser.parse_args()
    
    generator = GodlangPulseGenerator()
    
    if args.once:
        pulse = generator.generate_pulse()
        generator.broadcast_pulse(pulse)
        print(json.dumps(pulse.to_dict(), indent=2))
    else:
        generator.run(interval=args.interval)