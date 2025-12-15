# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN Circuit Breaker Pattern
Prevents cascade failures when external services are unavailable.
═══════════════════════════════════════════════════════════════════════════════
"""

import time
import threading
from enum import Enum
from dataclasses import dataclass, field
from typing import Any, Callable, Optional, TypeVar, Generic
from functools import wraps

from .logging_config import get_logger
from .exceptions import CircuitBreakerOpenError

logger = get_logger(__name__)

T = TypeVar("T")


class CircuitState(Enum):
    """Circuit breaker states."""
    CLOSED = "closed"       # Normal operation, requests pass through
    OPEN = "open"           # Requests fail fast, no calls to service
    HALF_OPEN = "half_open" # Testing if service recovered


@dataclass
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5          # Failures before opening
    success_threshold: int = 2          # Successes before closing from half-open
    timeout_seconds: float = 60.0       # Time before moving from open to half-open
    half_open_max_calls: int = 3        # Max concurrent calls in half-open state
    excluded_exceptions: tuple = ()     # Exceptions that don't count as failures


@dataclass
class CircuitStats:
    """Circuit breaker statistics."""
    total_calls: int = 0
    total_failures: int = 0
    total_successes: int = 0
    consecutive_failures: int = 0
    consecutive_successes: int = 0
    last_failure_time: Optional[float] = None
    last_success_time: Optional[float] = None
    state_changes: int = 0


class CircuitBreaker(Generic[T]):
    """
    Circuit breaker implementation for external service calls.
    
    Usage:
        cb = CircuitBreaker("okx_api")
        
        @cb.protect
        def call_okx_api():
            # ... API call
            
        # Or manually:
        with cb:
            result = call_okx_api()
    """
    
    def __init__(
        self,
        name: str,
        config: Optional[CircuitBreakerConfig] = None,
        fallback: Optional[Callable[[], T]] = None
    ):
        self.name = name
        self.config = config or CircuitBreakerConfig()
        self.fallback = fallback
        
        self._state = CircuitState.CLOSED
        self._stats = CircuitStats()
        self._lock = threading.RLock()
        self._last_state_change = time.time()
        self._half_open_calls = 0
    
    @property
    def state(self) -> CircuitState:
        """Get current circuit state, with automatic transition check."""
        with self._lock:
            if self._state == CircuitState.OPEN:
                # Check if timeout elapsed
                if time.time() - self._last_state_change >= self.config.timeout_seconds:
                    self._transition_to(CircuitState.HALF_OPEN)
            return self._state
    
    @property
    def stats(self) -> CircuitStats:
        """Get circuit statistics."""
        return self._stats
    
    def _transition_to(self, new_state: CircuitState) -> None:
        """Transition to a new state."""
        old_state = self._state
        self._state = new_state
        self._last_state_change = time.time()
        self._stats.state_changes += 1
        
        if new_state == CircuitState.HALF_OPEN:
            self._half_open_calls = 0
        
        logger.info(
            f"Circuit '{self.name}' state change: {old_state.value} -> {new_state.value}",
            extra={"extra": {"circuit": self.name, "old_state": old_state.value, "new_state": new_state.value}}
        )
    
    def _record_success(self) -> None:
        """Record a successful call."""
        with self._lock:
            self._stats.total_calls += 1
            self._stats.total_successes += 1
            self._stats.consecutive_successes += 1
            self._stats.consecutive_failures = 0
            self._stats.last_success_time = time.time()
            
            if self._state == CircuitState.HALF_OPEN:
                if self._stats.consecutive_successes >= self.config.success_threshold:
                    self._transition_to(CircuitState.CLOSED)
    
    def _record_failure(self, error: Exception) -> None:
        """Record a failed call."""
        with self._lock:
            # Check if this exception should be excluded
            if isinstance(error, self.config.excluded_exceptions):
                return
            
            self._stats.total_calls += 1
            self._stats.total_failures += 1
            self._stats.consecutive_failures += 1
            self._stats.consecutive_successes = 0
            self._stats.last_failure_time = time.time()
            
            if self._state == CircuitState.CLOSED:
                if self._stats.consecutive_failures >= self.config.failure_threshold:
                    self._transition_to(CircuitState.OPEN)
            elif self._state == CircuitState.HALF_OPEN:
                self._transition_to(CircuitState.OPEN)
    
    def _can_execute(self) -> bool:
        """Check if a call can be executed."""
        state = self.state  # This may trigger state transition
        
        if state == CircuitState.CLOSED:
            return True
        elif state == CircuitState.OPEN:
            return False
        else:  # HALF_OPEN
            with self._lock:
                if self._half_open_calls < self.config.half_open_max_calls:
                    self._half_open_calls += 1
                    return True
                return False
    
    def __enter__(self) -> "CircuitBreaker":
        """Context manager entry."""
        if not self._can_execute():
            if self.fallback:
                raise CircuitBreakerOpenError(
                    f"Circuit '{self.name}' is open, using fallback",
                    circuit_name=self.name,
                    has_fallback=True
                )
            raise CircuitBreakerOpenError(
                f"Circuit '{self.name}' is open",
                circuit_name=self.name
            )
        return self
    
    def __exit__(self, exc_type, exc_val, exc_tb):
        """Context manager exit."""
        if exc_type is None:
            self._record_success()
        elif exc_val is not None:
            self._record_failure(exc_val)
        return False  # Don't suppress exceptions
    
    def protect(self, func: Callable[..., T]) -> Callable[..., T]:
        """Decorator to protect a function with circuit breaker."""
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            if not self._can_execute():
                if self.fallback:
                    logger.warning(
                        f"Circuit '{self.name}' open, using fallback",
                        extra={"extra": {"circuit": self.name, "function": func.__name__}}
                    )
                    return self.fallback()
                raise CircuitBreakerOpenError(
                    f"Circuit '{self.name}' is open",
                    circuit_name=self.name
                )
            
            try:
                result = func(*args, **kwargs)
                self._record_success()
                return result
            except Exception as e:
                self._record_failure(e)
                if self.fallback and self._state == CircuitState.OPEN:
                    return self.fallback()
                raise
        
        return wrapper
    
    def reset(self) -> None:
        """Manually reset the circuit breaker."""
        with self._lock:
            self._transition_to(CircuitState.CLOSED)
            self._stats = CircuitStats()
            logger.info(f"Circuit '{self.name}' manually reset")


# Global circuit breakers registry
_circuit_breakers: dict[str, CircuitBreaker] = {}


def get_circuit_breaker(
    name: str,
    config: Optional[CircuitBreakerConfig] = None,
    fallback: Optional[Callable] = None
) -> CircuitBreaker:
    """Get or create a circuit breaker by name."""
    if name not in _circuit_breakers:
        _circuit_breakers[name] = CircuitBreaker(name, config, fallback)
    return _circuit_breakers[name]
