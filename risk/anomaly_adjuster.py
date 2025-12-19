# -*- coding: utf-8 -*-
"""
🎯 ANOMALY RISK ADJUSTER
Reads detected anomalies and adjusts trading parameters accordingly.

Nobel-potential anomalies = Higher risk awareness = Safer trading
"""

import json
import os
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional
from dataclasses import dataclass


@dataclass
class RiskAdjustment:
    """Trading risk adjustment based on anomalies."""
    position_size_multiplier: float  # 0.5 = half position
    stop_loss_multiplier: float      # 0.8 = tighter stop
    take_profit_multiplier: float    # 1.2 = wider TP
    signal_threshold: float          # Only trade top X% signals
    reason: str
    anomaly_source: str
    confidence: float


class AnomalyRiskAdjuster:
    """
    Reads anomalies and produces trading adjustments.
    
    Power Law → Fat tail risk → Reduce position, tighten stops
    Phase Transition → Regime change → Wait or reduce size
    Universal Attractor → Market at equilibrium → Normal trading
    """
    
    def __init__(self, discoveries_dir: str = None, redis_client = None):
        self.discoveries_dir = Path(discoveries_dir or "discoveries")
        self.redis = redis_client
        
        # Default adjustment (no anomalies)
        self.default_adjustment = RiskAdjustment(
            position_size_multiplier=1.0,
            stop_loss_multiplier=1.0,
            take_profit_multiplier=1.0,
            signal_threshold=0.5,  # Trade signals > 50% confidence
            reason="No significant anomalies",
            anomaly_source="none",
            confidence=1.0
        )
    
    def load_recent_anomalies(self, hours: int = 24) -> List[dict]:
        """Load anomalies from last N hours."""
        anomalies = []
        cutoff = datetime.now() - timedelta(hours=hours)
        
        if not self.discoveries_dir.exists():
            return anomalies
        
        for file in self.discoveries_dir.glob("*.json"):
            try:
                with open(file) as f:
                    data = json.load(f)
                
                # Parse timestamp
                ts = data.get("timestamp", "")
                if ts:
                    file_time = datetime.fromisoformat(ts)
                    if file_time > cutoff:
                        anomalies.append(data)
            except:
                continue
        
        return anomalies
    
    def analyze_power_law(self, anomaly: dict) -> RiskAdjustment:
        """
        Power Law detected = Fat tail risk exists.
        
        α < 2: Infinite variance (EXTREME risk)
        α = 2-3: High fat tails (HIGH risk)
        α > 3: Approaching normal (MODERATE risk)
        """
        # Extract alpha from description
        desc = anomaly.get("description", "")
        alpha = 2.33  # Default from our data
        
        if "α=" in desc:
            try:
                alpha = float(desc.split("α=")[1].split(",")[0])
            except:
                pass
        
        confidence = anomaly.get("confidence", 0.5)
        
        if alpha < 2:
            # Infinite variance - EXTREME caution
            return RiskAdjustment(
                position_size_multiplier=0.3,  # 30% of normal
                stop_loss_multiplier=0.5,      # 50% tighter
                take_profit_multiplier=1.5,    # 50% wider
                signal_threshold=0.8,          # Only top 20% signals
                reason=f"Power Law α={alpha:.2f} → Infinite variance! Maximum caution.",
                anomaly_source="power_law",
                confidence=confidence
            )
        elif alpha < 3:
            # High fat tails - caution needed
            return RiskAdjustment(
                position_size_multiplier=0.6,  # 60% of normal
                stop_loss_multiplier=0.7,      # 30% tighter
                take_profit_multiplier=1.3,    # 30% wider
                signal_threshold=0.7,          # Only top 30% signals
                reason=f"Power Law α={alpha:.2f} → Fat tails detected. Reduce exposure.",
                anomaly_source="power_law",
                confidence=confidence
            )
        else:
            # Approaching normal
            return RiskAdjustment(
                position_size_multiplier=0.85,
                stop_loss_multiplier=0.9,
                take_profit_multiplier=1.1,
                signal_threshold=0.6,
                reason=f"Power Law α={alpha:.2f} → Moderate tail risk.",
                anomaly_source="power_law",
                confidence=confidence
            )
    
    def analyze_phase_transition(self, anomaly: dict) -> RiskAdjustment:
        """
        Phase Transition = Regime change.
        Market structure changing - wait or be very careful.
        """
        confidence = anomaly.get("confidence", 0.5)
        
        return RiskAdjustment(
            position_size_multiplier=0.4,  # 40% of normal
            stop_loss_multiplier=0.6,      # 40% tighter
            take_profit_multiplier=1.0,    # Normal TP
            signal_threshold=0.75,         # Only top 25% signals
            reason="Phase Transition → Regime change! Reduce until stable.",
            anomaly_source="phase_transition",
            confidence=confidence
        )
    
    def analyze_attractor(self, anomaly: dict) -> RiskAdjustment:
        """
        Universal Attractor = Market at equilibrium.
        This is actually GOOD - market is stable.
        """
        confidence = anomaly.get("confidence", 0.5)
        
        return RiskAdjustment(
            position_size_multiplier=1.1,  # Slightly larger OK
            stop_loss_multiplier=1.0,      # Normal stop
            take_profit_multiplier=0.9,    # Tighter TP (reversion expected)
            signal_threshold=0.5,          # Normal threshold
            reason="Universal Attractor → Market at equilibrium. Normal trading.",
            anomaly_source="attractor",
            confidence=confidence
        )
    
    def get_adjustment(self) -> RiskAdjustment:
        """
        Get current risk adjustment based on all anomalies.
        Combines multiple anomalies with priority weighting.
        """
        anomalies = self.load_recent_anomalies(hours=6)  # Last 6 hours
        
        if not anomalies:
            return self.default_adjustment
        
        adjustments = []
        
        for anomaly in anomalies:
            atype = anomaly.get("type", "")
            nobel = anomaly.get("nobel_potential", 1)
            
            # Only consider high-potential anomalies
            if nobel < 2:
                continue
            
            if atype == "power_law":
                adj = self.analyze_power_law(anomaly)
                adjustments.append((adj, nobel))
            elif atype == "phase_transition":
                adj = self.analyze_phase_transition(anomaly)
                adjustments.append((adj, nobel))
            elif atype == "universal_attractor":
                adj = self.analyze_attractor(anomaly)
                adjustments.append((adj, nobel))
        
        if not adjustments:
            return self.default_adjustment
        
        # Combine adjustments - take most conservative
        min_position = min(a.position_size_multiplier for a, _ in adjustments)
        min_stop = min(a.stop_loss_multiplier for a, _ in adjustments)
        max_tp = max(a.take_profit_multiplier for a, _ in adjustments)
        max_threshold = max(a.signal_threshold for a, _ in adjustments)
        
        # Get highest priority anomaly reason
        highest = max(adjustments, key=lambda x: x[1])
        
        return RiskAdjustment(
            position_size_multiplier=min_position,
            stop_loss_multiplier=min_stop,
            take_profit_multiplier=max_tp,
            signal_threshold=max_threshold,
            reason=highest[0].reason,
            anomaly_source=highest[0].anomaly_source,
            confidence=highest[0].confidence
        )
    
    def publish_to_redis(self, adjustment: RiskAdjustment):
        """Publish adjustment to Redis for trading system."""
        if not self.redis:
            try:
                import redis
                self.redis = redis.Redis(
                    host=os.getenv("REDIS_HOST", "localhost"),
                    port=int(os.getenv("REDIS_PORT", 16379)),
                    password=os.getenv("REDIS_PASS", "voltran2024"),
                    decode_responses=True
                )
            except:
                return
        
        try:
            data = {
                "position_multiplier": adjustment.position_size_multiplier,
                "stop_loss_multiplier": adjustment.stop_loss_multiplier,
                "take_profit_multiplier": adjustment.take_profit_multiplier,
                "signal_threshold": adjustment.signal_threshold,
                "reason": adjustment.reason,
                "source": adjustment.anomaly_source,
                "confidence": adjustment.confidence,
                "timestamp": datetime.now().isoformat()
            }
            
            self.redis.set(
                "godbrain:anomaly:risk_adjustment",
                json.dumps(data)
            )
            print(f"📊 Risk adjustment published: {adjustment.reason}")
            
        except Exception as e:
            print(f"❌ Redis publish failed: {e}")
    
    def get_trading_params(self, base_params: dict) -> dict:
        """
        Apply anomaly adjustments to base trading parameters.
        
        Example:
            base = {"position_size": 1000, "stop_loss": 0.02, "take_profit": 0.05}
            adjusted = adjuster.get_trading_params(base)
        """
        adjustment = self.get_adjustment()
        
        adjusted = base_params.copy()
        
        if "position_size" in adjusted:
            adjusted["position_size"] *= adjustment.position_size_multiplier
        
        if "stop_loss" in adjusted:
            # Tighter stop = smaller value
            adjusted["stop_loss"] *= adjustment.stop_loss_multiplier
        
        if "take_profit" in adjusted:
            # Wider TP = larger value
            adjusted["take_profit"] *= adjustment.take_profit_multiplier
        
        # Add metadata
        adjusted["_anomaly_adjusted"] = True
        adjusted["_adjustment_reason"] = adjustment.reason
        adjusted["_signal_threshold"] = adjustment.signal_threshold
        
        return adjusted


# ═══════════════════════════════════════════════════════════════════════════════
# INTEGRATION HELPER
# ═══════════════════════════════════════════════════════════════════════════════

def get_risk_adjustment() -> RiskAdjustment:
    """Quick helper to get current risk adjustment."""
    adjuster = AnomalyRiskAdjuster()
    return adjuster.get_adjustment()


def apply_anomaly_risk(base_params: dict) -> dict:
    """Quick helper to apply anomaly risk to params."""
    adjuster = AnomalyRiskAdjuster()
    return adjuster.get_trading_params(base_params)


if __name__ == "__main__":
    # Test
    adjuster = AnomalyRiskAdjuster()
    adjustment = adjuster.get_adjustment()
    
    print("=" * 60)
    print("🎯 ANOMALY RISK ADJUSTMENT")
    print("=" * 60)
    print(f"Position Size: {adjustment.position_size_multiplier:.0%}")
    print(f"Stop Loss: {adjustment.stop_loss_multiplier:.0%} of normal")
    print(f"Take Profit: {adjustment.take_profit_multiplier:.0%} of normal")
    print(f"Signal Threshold: Top {(1-adjustment.signal_threshold)*100:.0f}% only")
    print(f"Reason: {adjustment.reason}")
    print(f"Source: {adjustment.anomaly_source}")
    print(f"Confidence: {adjustment.confidence:.1%}")
    
    # Test with base params
    base = {
        "position_size": 1000,
        "stop_loss": 0.02,
        "take_profit": 0.05
    }
    
    adjusted = adjuster.get_trading_params(base)
    print(f"\nBase params: {base}")
    print(f"Adjusted:    {adjusted}")
