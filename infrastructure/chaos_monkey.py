# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN Chaos Monkey - Resilience Testing Framework
Enterprise-grade fault injection for production readiness validation.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import time
import random
import asyncio
import logging
import threading
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Callable, Any
from dataclasses import dataclass, field
from enum import Enum
from contextlib import contextmanager


logger = logging.getLogger("godbrain.chaos")


class FaultType(Enum):
    """Types of faults that can be injected."""
    LATENCY = "latency"              # Add artificial delay
    ERROR = "error"                   # Raise exception
    TIMEOUT = "timeout"               # Simulate timeout
    RATE_LIMIT = "rate_limit"        # Simulate rate limiting
    PARTIAL_FAILURE = "partial"       # Random partial failures
    NETWORK_PARTITION = "network"     # Simulate network issues
    DATA_CORRUPTION = "corruption"    # Return malformed data


@dataclass
class FaultConfig:
    """Configuration for a fault injection."""
    fault_type: FaultType
    probability: float = 0.1          # 0-1 probability of triggering
    latency_ms: int = 1000            # For LATENCY type
    error_message: str = "Chaos Monkey: Simulated failure"
    duration_seconds: int = 60        # How long fault is active
    target_components: List[str] = field(default_factory=list)  # Empty = all
    
    def should_trigger(self) -> bool:
        """Determine if fault should trigger based on probability."""
        return random.random() < self.probability


@dataclass
class ChaosEvent:
    """Record of a chaos event."""
    timestamp: datetime
    fault_type: FaultType
    component: str
    triggered: bool
    details: str = ""


class ChaosMonkey:
    """
    Chaos Monkey for GODBRAIN resilience testing.
    
    Injects faults into the system to test:
    - Circuit breaker activation
    - Retry mechanism behavior
    - Rate limiter response
    - Panic mode triggering
    - Graceful degradation
    
    Usage:
        chaos = ChaosMonkey()
        
        # Enable specific fault
        chaos.enable_fault(FaultConfig(
            fault_type=FaultType.LATENCY,
            probability=0.3,
            latency_ms=2000
        ))
        
        # Use decorator for automatic fault injection
        @chaos.inject("exchange_api")
        async def fetch_price(symbol):
            ...
        
        # Or use context manager
        with chaos.fault_context("order_execution"):
            execute_trade(...)
    """
    
    def __init__(self, enabled: bool = False):
        self.enabled = enabled
        self.faults: Dict[str, FaultConfig] = {}
        self.events: List[ChaosEvent] = []
        self._lock = threading.Lock()
        self._max_events = 1000
    
    def enable(self) -> None:
        """Enable chaos monkey."""
        self.enabled = True
        logger.warning("🐒 CHAOS MONKEY ENABLED - Fault injection active!")
    
    def disable(self) -> None:
        """Disable chaos monkey."""
        self.enabled = False
        logger.info("🐒 Chaos Monkey disabled")
    
    def enable_fault(self, config: FaultConfig, name: Optional[str] = None) -> str:
        """
        Enable a fault configuration.
        
        Returns fault ID.
        """
        fault_id = name or f"{config.fault_type.value}_{int(time.time())}"
        
        with self._lock:
            self.faults[fault_id] = config
        
        logger.warning(f"🐒 Fault enabled: {fault_id} ({config.fault_type.value}, {config.probability*100:.0f}% probability)")
        return fault_id
    
    def disable_fault(self, fault_id: str) -> bool:
        """Disable a specific fault."""
        with self._lock:
            if fault_id in self.faults:
                del self.faults[fault_id]
                logger.info(f"🐒 Fault disabled: {fault_id}")
                return True
        return False
    
    def clear_all_faults(self) -> None:
        """Clear all fault configurations."""
        with self._lock:
            self.faults.clear()
        logger.info("🐒 All faults cleared")
    
    def _record_event(self, event: ChaosEvent) -> None:
        """Record a chaos event."""
        with self._lock:
            self.events.append(event)
            if len(self.events) > self._max_events:
                self.events = self.events[-self._max_events:]
    
    def _check_faults(self, component: str) -> Optional[FaultConfig]:
        """Check if any fault should trigger for this component."""
        if not self.enabled:
            return None
        
        with self._lock:
            for fault_id, config in self.faults.items():
                # Check if component matches
                if config.target_components and component not in config.target_components:
                    continue
                
                if config.should_trigger():
                    self._record_event(ChaosEvent(
                        timestamp=datetime.now(),
                        fault_type=config.fault_type,
                        component=component,
                        triggered=True,
                        details=f"Fault {fault_id} triggered"
                    ))
                    return config
        
        return None
    
    def _apply_fault(self, config: FaultConfig) -> None:
        """Apply a synchronous fault."""
        if config.fault_type == FaultType.LATENCY:
            time.sleep(config.latency_ms / 1000)
        
        elif config.fault_type == FaultType.ERROR:
            raise Exception(config.error_message)
        
        elif config.fault_type == FaultType.TIMEOUT:
            time.sleep(30)  # Long sleep to trigger timeout
            raise TimeoutError(config.error_message)
        
        elif config.fault_type == FaultType.RATE_LIMIT:
            raise Exception("429: Rate limit exceeded (Chaos Monkey)")
    
    async def _apply_fault_async(self, config: FaultConfig) -> None:
        """Apply an async fault."""
        if config.fault_type == FaultType.LATENCY:
            await asyncio.sleep(config.latency_ms / 1000)
        
        elif config.fault_type == FaultType.ERROR:
            raise Exception(config.error_message)
        
        elif config.fault_type == FaultType.TIMEOUT:
            await asyncio.sleep(30)
            raise asyncio.TimeoutError(config.error_message)
        
        elif config.fault_type == FaultType.RATE_LIMIT:
            raise Exception("429: Rate limit exceeded (Chaos Monkey)")
    
    @contextmanager
    def fault_context(self, component: str):
        """
        Context manager for fault injection.
        
        Usage:
            with chaos.fault_context("api_call"):
                response = api.call()
        """
        config = self._check_faults(component)
        
        if config:
            logger.warning(f"🐒 Injecting {config.fault_type.value} into {component}")
            self._apply_fault(config)
        
        yield
    
    def inject(self, component: str) -> Callable:
        """
        Decorator for automatic fault injection.
        
        Usage:
            @chaos.inject("exchange")
            def fetch_balance():
                ...
        """
        def decorator(func: Callable) -> Callable:
            if asyncio.iscoroutinefunction(func):
                async def async_wrapper(*args, **kwargs):
                    config = self._check_faults(component)
                    if config:
                        logger.warning(f"🐒 Injecting {config.fault_type.value} into {component}")
                        await self._apply_fault_async(config)
                    return await func(*args, **kwargs)
                return async_wrapper
            else:
                def sync_wrapper(*args, **kwargs):
                    config = self._check_faults(component)
                    if config:
                        logger.warning(f"🐒 Injecting {config.fault_type.value} into {component}")
                        self._apply_fault(config)
                    return func(*args, **kwargs)
                return sync_wrapper
        return decorator
    
    def get_stats(self) -> Dict[str, Any]:
        """Get chaos monkey statistics."""
        with self._lock:
            triggered = [e for e in self.events if e.triggered]
            by_type = {}
            for e in triggered:
                t = e.fault_type.value
                by_type[t] = by_type.get(t, 0) + 1
            
            return {
                "enabled": self.enabled,
                "active_faults": len(self.faults),
                "total_events": len(self.events),
                "triggered_events": len(triggered),
                "by_fault_type": by_type,
                "fault_configs": {
                    k: {"type": v.fault_type.value, "probability": v.probability}
                    for k, v in self.faults.items()
                }
            }


# ==============================================================================
# Pre-defined Chaos Scenarios
# ==============================================================================

class ChaosScenarios:
    """Pre-defined chaos scenarios for common tests."""
    
    @staticmethod
    def exchange_latency(chaos: ChaosMonkey, severity: str = "medium") -> None:
        """Simulate exchange API latency issues."""
        latency_map = {"low": 500, "medium": 2000, "high": 5000}
        
        chaos.enable_fault(FaultConfig(
            fault_type=FaultType.LATENCY,
            probability=0.3,
            latency_ms=latency_map.get(severity, 2000),
            target_components=["exchange", "api", "okx"]
        ), "exchange_latency")
    
    @staticmethod
    def rate_limit_storm(chaos: ChaosMonkey) -> None:
        """Simulate rate limiting from exchange."""
        chaos.enable_fault(FaultConfig(
            fault_type=FaultType.RATE_LIMIT,
            probability=0.5,
            error_message="429: Too Many Requests",
            target_components=["exchange", "api"]
        ), "rate_limit_storm")
    
    @staticmethod
    def network_instability(chaos: ChaosMonkey) -> None:
        """Simulate network connection issues."""
        chaos.enable_fault(FaultConfig(
            fault_type=FaultType.ERROR,
            probability=0.2,
            error_message="ConnectionError: Network unreachable",
            target_components=["network", "websocket", "api"]
        ), "network_instability")
    
    @staticmethod
    def redis_failure(chaos: ChaosMonkey) -> None:
        """Simulate Redis connection failure."""
        chaos.enable_fault(FaultConfig(
            fault_type=FaultType.ERROR,
            probability=0.4,
            error_message="RedisConnectionError: Connection refused",
            target_components=["redis", "cache", "state"]
        ), "redis_failure")
    
    @staticmethod
    def market_crash(chaos: ChaosMonkey) -> None:
        """Simulate extreme market volatility scenario."""
        # High latency + errors
        chaos.enable_fault(FaultConfig(
            fault_type=FaultType.LATENCY,
            probability=0.6,
            latency_ms=3000,
            target_components=["exchange"]
        ), "crash_latency")
        
        chaos.enable_fault(FaultConfig(
            fault_type=FaultType.ERROR,
            probability=0.3,
            error_message="Exchange overloaded - try again later",
            target_components=["exchange"]
        ), "crash_errors")
    
    @staticmethod
    def full_chaos(chaos: ChaosMonkey) -> None:
        """Enable all chaos scenarios at once (for stress testing)."""
        ChaosScenarios.exchange_latency(chaos, "high")
        ChaosScenarios.rate_limit_storm(chaos)
        ChaosScenarios.network_instability(chaos)


# Global instance
_chaos: Optional[ChaosMonkey] = None


def get_chaos_monkey() -> ChaosMonkey:
    """Get or create global chaos monkey instance."""
    global _chaos
    if _chaos is None:
        # Only enabled if CHAOS_ENABLED env var is set
        enabled = os.getenv("CHAOS_ENABLED", "false").lower() == "true"
        _chaos = ChaosMonkey(enabled=enabled)
    return _chaos


if __name__ == "__main__":
    import asyncio
    
    logging.basicConfig(level=logging.INFO)
    
    print("🐒 Chaos Monkey Demo")
    print("=" * 60)
    
    chaos = ChaosMonkey(enabled=True)
    
    # Enable latency fault
    ChaosScenarios.exchange_latency(chaos, "medium")
    
    # Test with decorator
    @chaos.inject("exchange")
    def fetch_price():
        print("Fetching price...")
        return 0.32
    
    # Run 10 times to see chaos in action
    for i in range(10):
        try:
            start = time.time()
            price = fetch_price()
            elapsed = (time.time() - start) * 1000
            print(f"  [{i+1}] Price: {price}, Time: {elapsed:.0f}ms")
        except Exception as e:
            print(f"  [{i+1}] ERROR: {e}")
    
    print("\nStats:", chaos.get_stats())
