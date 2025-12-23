# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN EMERGENCY SHUTDOWN - Global Panic Button Protocol
═══════════════════════════════════════════════════════════════════════════════

Features:
- One-click shutdown from Dashboard
- Seraph voice commands: "durdur", "kapat", "panik"
- Close all open positions (market orders)
- Cancel all pending orders
- Set system to HALT mode
- Send Telegram alerts
- Graceful or immediate shutdown options

Usage:
    from core.emergency_shutdown import EmergencyShutdown, get_emergency_shutdown
    
    es = get_emergency_shutdown()
    success = es.trigger_shutdown(reason="Manual panic")
"""

import os
import json
import time
import asyncio
from dataclasses import dataclass, asdict
from datetime import datetime
from typing import Dict, Any, Optional, List
from enum import Enum
import redis


# =============================================================================
# SHUTDOWN TYPES
# =============================================================================

class ShutdownType(Enum):
    """Types of emergency shutdown."""
    GRACEFUL = "graceful"      # Close positions at limit orders
    IMMEDIATE = "immediate"    # Close all at market price
    HALT_ONLY = "halt_only"    # Stop trading but keep positions


@dataclass
class ShutdownEvent:
    """Record of a shutdown event."""
    timestamp: float
    reason: str
    shutdown_type: str
    positions_closed: int
    orders_cancelled: int
    triggered_by: str  # "manual", "seraph", "auto_drawdown", "auto_loss_streak"
    success: bool
    error_message: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)


# =============================================================================
# EMERGENCY SHUTDOWN
# =============================================================================

class EmergencyShutdown:
    """
    Global emergency shutdown protocol for GODBRAIN.
    
    Provides multiple shutdown modes:
    - GRACEFUL: Close positions at favorable prices (limit orders)
    - IMMEDIATE: Close all positions NOW at market price
    - HALT_ONLY: Stop trading but maintain positions
    """
    
    REDIS_KEY_SHUTDOWN_LOG = "godbrain:emergency:log"
    REDIS_KEY_SYSTEM_MODE = "system:mode"
    REDIS_CHANNEL_BROADCAST = "godbrain:broadcast"
    
    # Seraph trigger keywords
    TRIGGER_KEYWORDS = [
        "durdur", "kapat", "panik", "panic", 
        "emergency", "acil", "stop", "shutdown",
        "her şeyi kapat", "pozisyonları kapat"
    ]
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self._redis = redis_client
        self._shutdown_history: List[ShutdownEvent] = []
        self._load_history()
    
    # -------------------------------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------------------------------
    
    def trigger_shutdown(
        self,
        reason: str = "Manual emergency shutdown",
        shutdown_type: ShutdownType = ShutdownType.IMMEDIATE,
        triggered_by: str = "manual",
    ) -> Dict[str, Any]:
        """
        Trigger emergency shutdown.
        
        Args:
            reason: Why shutdown was triggered
            shutdown_type: GRACEFUL, IMMEDIATE, or HALT_ONLY
            triggered_by: Who/what triggered it (manual, seraph, auto)
        
        Returns:
            Dict with shutdown results
        """
        print(f"\n{'='*60}")
        print(f"🚨 EMERGENCY SHUTDOWN TRIGGERED 🚨")
        print(f"Reason: {reason}")
        print(f"Type: {shutdown_type.value}")
        print(f"Triggered by: {triggered_by}")
        print(f"{'='*60}\n")
        
        result = {
            "success": True,
            "positions_closed": 0,
            "orders_cancelled": 0,
            "error": None,
        }
        
        try:
            # Step 1: Set system to HALT mode
            self._set_system_halt(reason)
            
            # Step 2: Cancel all pending orders
            result["orders_cancelled"] = self._cancel_all_orders()
            
            # Step 3: Close positions based on shutdown type
            if shutdown_type != ShutdownType.HALT_ONLY:
                result["positions_closed"] = self._close_all_positions(shutdown_type)
            
            # Step 4: Broadcast shutdown event
            self._broadcast_shutdown(reason, shutdown_type)
            
            # Step 5: Send Telegram alert
            self._send_telegram_alert(reason, result)
            
        except Exception as e:
            result["success"] = False
            result["error"] = str(e)
            print(f"[EMERGENCY] Error during shutdown: {e}")
        
        # Log the event
        event = ShutdownEvent(
            timestamp=time.time(),
            reason=reason,
            shutdown_type=shutdown_type.value,
            positions_closed=result["positions_closed"],
            orders_cancelled=result["orders_cancelled"],
            triggered_by=triggered_by,
            success=result["success"],
            error_message=result.get("error", ""),
        )
        self._log_event(event)
        
        return result
    
    def check_seraph_trigger(self, message: str) -> bool:
        """
        Check if a Seraph message contains shutdown trigger keywords.
        
        Args:
            message: User message to Seraph
        
        Returns:
            True if message contains shutdown trigger
        """
        message_lower = message.lower()
        for keyword in self.TRIGGER_KEYWORDS:
            if keyword in message_lower:
                return True
        return False
    
    def handle_seraph_shutdown(self, message: str) -> Dict[str, Any]:
        """
        Handle shutdown triggered by Seraph command.
        
        Args:
            message: User message that triggered shutdown
        
        Returns:
            Shutdown result
        """
        # Determine shutdown type from message
        if any(kw in message.lower() for kw in ["acil", "panic", "panik", "immediate"]):
            shutdown_type = ShutdownType.IMMEDIATE
        elif any(kw in message.lower() for kw in ["sadece durdur", "halt", "bekle"]):
            shutdown_type = ShutdownType.HALT_ONLY
        else:
            shutdown_type = ShutdownType.IMMEDIATE  # Default to IMMEDIATE for safety
        
        return self.trigger_shutdown(
            reason=f"Seraph command: {message[:100]}",
            shutdown_type=shutdown_type,
            triggered_by="seraph",
        )
    
    def get_status(self) -> Dict[str, Any]:
        """Get current shutdown system status."""
        return {
            "is_active": self._is_system_halted(),
            "last_shutdown": self._get_last_shutdown(),
            "history_count": len(self._shutdown_history),
            "trigger_keywords": self.TRIGGER_KEYWORDS,
        }
    
    def get_history(self, limit: int = 10) -> List[Dict[str, Any]]:
        """Get shutdown event history."""
        return [e.to_dict() for e in self._shutdown_history[-limit:]]
    
    def resume_system(self, reason: str = "Manual resume") -> bool:
        """
        Resume system after shutdown.
        
        Args:
            reason: Why system is being resumed
        
        Returns:
            True if successful
        """
        try:
            if self._redis:
                self._redis.set(self.REDIS_KEY_SYSTEM_MODE, json.dumps({
                    "mode": "ACTIVE",
                    "resume_reason": reason,
                    "resume_time": time.time(),
                }))
                self._redis.publish(self.REDIS_CHANNEL_BROADCAST, json.dumps({
                    "type": "SYSTEM_RESUME",
                    "reason": reason,
                    "timestamp": time.time(),
                }))
            print(f"[EMERGENCY] ✅ System resumed: {reason}")
            return True
        except Exception as e:
            print(f"[EMERGENCY] Error resuming system: {e}")
            return False
    
    # -------------------------------------------------------------------------
    # INTERNAL METHODS
    # -------------------------------------------------------------------------
    
    def _set_system_halt(self, reason: str) -> None:
        """Set system mode to HALT."""
        if self._redis:
            try:
                self._redis.set(self.REDIS_KEY_SYSTEM_MODE, json.dumps({
                    "mode": "HALT",
                    "reason": reason,
                    "halt_time": time.time(),
                }))
                # Also set legacy keys for compatibility
                self._redis.set("synthia:ai_mode", "EMERGENCY_HALT")
                self._redis.set("system:emergency_halt", "true")
            except Exception as e:
                print(f"[EMERGENCY] Error setting halt mode: {e}")
    
    def _is_system_halted(self) -> bool:
        """Check if system is currently halted."""
        if not self._redis:
            return False
        try:
            data = self._redis.get(self.REDIS_KEY_SYSTEM_MODE)
            if data:
                mode_data = json.loads(data)
                return mode_data.get("mode") == "HALT"
        except Exception:
            pass
        return False
    
    def _cancel_all_orders(self) -> int:
        """
        Cancel all pending orders.
        
        Returns:
            Number of orders cancelled
        """
        cancelled = 0
        if self._redis:
            try:
                # Publish cancel command to trading engine
                self._redis.publish("godbrain:commands", json.dumps({
                    "command": "CANCEL_ALL_ORDERS",
                    "timestamp": time.time(),
                }))
                
                # Get pending orders count for reporting
                pending = self._redis.get("trading:pending_orders")
                if pending:
                    cancelled = int(pending)
                    self._redis.set("trading:pending_orders", "0")
                
                print(f"[EMERGENCY] Cancelled {cancelled} pending orders")
            except Exception as e:
                print(f"[EMERGENCY] Error cancelling orders: {e}")
        
        return cancelled
    
    def _close_all_positions(self, shutdown_type: ShutdownType) -> int:
        """
        Close all open positions.
        
        Returns:
            Number of positions closed
        """
        closed = 0
        if self._redis:
            try:
                order_type = "MARKET" if shutdown_type == ShutdownType.IMMEDIATE else "LIMIT"
                
                # Publish close command to trading engine
                self._redis.publish("godbrain:commands", json.dumps({
                    "command": "CLOSE_ALL_POSITIONS",
                    "order_type": order_type,
                    "timestamp": time.time(),
                }))
                
                # Get open positions count for reporting
                positions = self._redis.get("trading:open_positions")
                if positions:
                    closed = int(positions)
                    self._redis.set("trading:open_positions", "0")
                
                print(f"[EMERGENCY] Closed {closed} positions ({order_type})")
            except Exception as e:
                print(f"[EMERGENCY] Error closing positions: {e}")
        
        return closed
    
    def _broadcast_shutdown(self, reason: str, shutdown_type: ShutdownType) -> None:
        """Broadcast shutdown event to all subscribers."""
        if self._redis:
            try:
                self._redis.publish(self.REDIS_CHANNEL_BROADCAST, json.dumps({
                    "type": "EMERGENCY_SHUTDOWN",
                    "reason": reason,
                    "shutdown_type": shutdown_type.value,
                    "timestamp": time.time(),
                }))
            except Exception as e:
                print(f"[EMERGENCY] Error broadcasting shutdown: {e}")
    
    def _send_telegram_alert(self, reason: str, result: Dict[str, Any]) -> None:
        """Send Telegram alert about shutdown."""
        try:
            from infrastructure.telegram_alerts import get_telegram_alerter
            
            alerter = get_telegram_alerter()
            if alerter:
                message = (
                    f"🚨 *EMERGENCY SHUTDOWN*\n\n"
                    f"Reason: {reason}\n"
                    f"Positions Closed: {result['positions_closed']}\n"
                    f"Orders Cancelled: {result['orders_cancelled']}\n"
                    f"Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}"
                )
                asyncio.create_task(alerter.send_message(message))
        except Exception as e:
            print(f"[EMERGENCY] Telegram alert failed: {e}")
    
    def _log_event(self, event: ShutdownEvent) -> None:
        """Log shutdown event to Redis and memory."""
        self._shutdown_history.append(event)
        
        if self._redis:
            try:
                self._redis.lpush(
                    self.REDIS_KEY_SHUTDOWN_LOG,
                    json.dumps(event.to_dict())
                )
                # Keep only last 100 events
                self._redis.ltrim(self.REDIS_KEY_SHUTDOWN_LOG, 0, 99)
            except Exception as e:
                print(f"[EMERGENCY] Error logging event: {e}")
    
    def _load_history(self) -> None:
        """Load shutdown history from Redis."""
        if not self._redis:
            return
        try:
            events = self._redis.lrange(self.REDIS_KEY_SHUTDOWN_LOG, 0, 99)
            self._shutdown_history = [
                ShutdownEvent(**json.loads(e)) for e in events
            ]
        except Exception as e:
            print(f"[EMERGENCY] Error loading history: {e}")
    
    def _get_last_shutdown(self) -> Optional[Dict[str, Any]]:
        """Get last shutdown event."""
        if self._shutdown_history:
            return self._shutdown_history[-1].to_dict()
        return None


# =============================================================================
# SINGLETON ACCESSOR
# =============================================================================

_emergency_shutdown_instance: Optional[EmergencyShutdown] = None


def get_emergency_shutdown(redis_client: Optional[redis.Redis] = None) -> EmergencyShutdown:
    """
    Get or create the singleton Emergency Shutdown instance.
    
    Usage:
        es = get_emergency_shutdown()
        es.trigger_shutdown(reason="Panic!")
    """
    global _emergency_shutdown_instance
    
    if _emergency_shutdown_instance is None:
        # Try to create Redis client if not provided
        if redis_client is None:
            try:
                redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
                redis_port = int(os.getenv("REDIS_PORT", "6379"))
                redis_pass = os.getenv("REDIS_PASS", None)
                redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    password=redis_pass,
                    decode_responses=True,
                )
                redis_client.ping()
            except Exception as e:
                print(f"[EMERGENCY] Redis not available: {e}")
                redis_client = None
        
        _emergency_shutdown_instance = EmergencyShutdown(redis_client)
    
    return _emergency_shutdown_instance


# =============================================================================
# CLI TESTING
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("GODBRAIN EMERGENCY SHUTDOWN TEST")
    print("=" * 60)
    
    es = get_emergency_shutdown()
    
    # Show current status
    status = es.get_status()
    print(f"\nCurrent Status:")
    print(f"  Is Active (Halted): {status['is_active']}")
    print(f"  History Count: {status['history_count']}")
    print(f"  Trigger Keywords: {status['trigger_keywords'][:5]}...")
    
    # Test trigger detection
    test_messages = [
        "sistemi durdur",
        "normal soru",
        "panik! her şeyi kapat",
        "merhaba seraph",
        "emergency stop now",
    ]
    
    print(f"\nTrigger Detection Test:")
    for msg in test_messages:
        is_trigger = es.check_seraph_trigger(msg)
        print(f"  '{msg}' -> Trigger: {is_trigger}")
    
    print("\n" + "=" * 60)
    print("✅ Emergency Shutdown Test Complete")
    print("NOTE: Actual shutdown was NOT triggered (test mode)")
