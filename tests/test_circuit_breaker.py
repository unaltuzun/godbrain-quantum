# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN Circuit Breaker Tests
Unit tests for circuit breaker pattern implementation.
═══════════════════════════════════════════════════════════════════════════════
"""

import pytest
import time
from unittest.mock import MagicMock, patch

import sys
from pathlib import Path
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from infrastructure.circuit_breaker import (
    CircuitBreaker,
    CircuitBreakerConfig,
    CircuitState,
    get_circuit_breaker,
)
from infrastructure.exceptions import CircuitBreakerOpenError


class TestCircuitBreakerStates:
    """Test circuit breaker state transitions."""
    
    def test_initial_state_is_closed(self):
        """Circuit should start in CLOSED state."""
        cb = CircuitBreaker("test")
        assert cb.state == CircuitState.CLOSED
    
    def test_stays_closed_on_success(self):
        """Circuit should stay closed after successful calls."""
        cb = CircuitBreaker("test")
        
        @cb.protect
        def success_fn():
            return "ok"
        
        for _ in range(10):
            result = success_fn()
            assert result == "ok"
        
        assert cb.state == CircuitState.CLOSED
        assert cb.stats.consecutive_successes == 10
        assert cb.stats.consecutive_failures == 0
    
    def test_opens_after_failure_threshold(self):
        """Circuit should open after reaching failure threshold."""
        config = CircuitBreakerConfig(failure_threshold=3)
        cb = CircuitBreaker("test", config)
        
        @cb.protect
        def failing_fn():
            raise ValueError("Expected error")
        
        for i in range(3):
            with pytest.raises(ValueError):
                failing_fn()
        
        assert cb.state == CircuitState.OPEN
        assert cb.stats.consecutive_failures == 3
    
    def test_open_circuit_blocks_calls(self):
        """Open circuit should block calls immediately."""
        config = CircuitBreakerConfig(failure_threshold=1, timeout_seconds=60)
        cb = CircuitBreaker("test", config)
        
        @cb.protect
        def failing_fn():
            raise ValueError("Error")
        
        # Trip the circuit
        with pytest.raises(ValueError):
            failing_fn()
        
        assert cb.state == CircuitState.OPEN
        
        # Next call should be blocked
        with pytest.raises(CircuitBreakerOpenError):
            failing_fn()
    
    def test_half_open_after_timeout(self):
        """Circuit should transition to HALF_OPEN after timeout."""
        config = CircuitBreakerConfig(failure_threshold=1, timeout_seconds=0.1)
        cb = CircuitBreaker("test", config)
        
        @cb.protect
        def failing_fn():
            raise ValueError("Error")
        
        # Trip the circuit
        with pytest.raises(ValueError):
            failing_fn()
        
        assert cb.state == CircuitState.OPEN
        
        # Wait for timeout
        time.sleep(0.15)
        
        assert cb.state == CircuitState.HALF_OPEN
    
    def test_closes_after_success_in_half_open(self):
        """Circuit should close after successes in HALF_OPEN state."""
        config = CircuitBreakerConfig(
            failure_threshold=1,
            success_threshold=2,
            timeout_seconds=0.1
        )
        cb = CircuitBreaker("test", config)
        
        call_count = 0
        
        @cb.protect
        def sometimes_fails():
            nonlocal call_count
            call_count += 1
            if call_count == 1:
                raise ValueError("First call fails")
            return "ok"
        
        # Trip the circuit
        with pytest.raises(ValueError):
            sometimes_fails()
        
        assert cb.state == CircuitState.OPEN
        
        # Wait for timeout
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        
        # Successful calls should close the circuit
        sometimes_fails()
        sometimes_fails()
        
        assert cb.state == CircuitState.CLOSED
    
    def test_reopens_on_failure_in_half_open(self):
        """Circuit should reopen on failure in HALF_OPEN state."""
        config = CircuitBreakerConfig(failure_threshold=1, timeout_seconds=0.1)
        cb = CircuitBreaker("test", config)
        
        @cb.protect
        def always_fails():
            raise ValueError("Always fails")
        
        # Trip the circuit
        with pytest.raises(ValueError):
            always_fails()
        
        # Wait for half-open
        time.sleep(0.15)
        assert cb.state == CircuitState.HALF_OPEN
        
        # Failure in half-open should reopen
        with pytest.raises(ValueError):
            always_fails()
        
        assert cb.state == CircuitState.OPEN


class TestCircuitBreakerFallback:
    """Test circuit breaker fallback functionality."""
    
    def test_fallback_used_when_open(self):
        """Fallback should be called when circuit is open."""
        fallback_called = False
        
        def fallback():
            nonlocal fallback_called
            fallback_called = True
            return "fallback_value"
        
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker("test", config, fallback=fallback)
        
        call_count = 0
        
        @cb.protect
        def failing_fn():
            nonlocal call_count
            call_count += 1
            raise ValueError("Error")
        
        # Trip the circuit - first failure trips it, but exception still raises
        try:
            failing_fn()
        except ValueError:
            pass  # Expected - circuit trips but error propagates
        
        assert cb.state == CircuitState.OPEN
        
        # Next call should use fallback since circuit is now open
        result = failing_fn()
        
        assert fallback_called
        assert result == "fallback_value"
        assert call_count == 1  # Second call didn't reach the function
    
    def test_no_fallback_raises_error(self):
        """Without fallback, open circuit should raise error."""
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker("test", config, fallback=None)
        
        @cb.protect
        def failing_fn():
            raise ValueError("Error")
        
        # Trip the circuit
        with pytest.raises(ValueError):
            failing_fn()
        
        # Next call should raise CircuitBreakerOpenError
        with pytest.raises(CircuitBreakerOpenError) as exc_info:
            failing_fn()
        
        assert exc_info.value.circuit_name == "test"


class TestCircuitBreakerContextManager:
    """Test circuit breaker as context manager."""
    
    def test_context_manager_success(self):
        """Context manager should work for successful operations."""
        cb = CircuitBreaker("test")
        
        with cb:
            result = 1 + 1
        
        assert result == 2
        assert cb.stats.total_successes == 1
    
    def test_context_manager_failure(self):
        """Context manager should record failures."""
        config = CircuitBreakerConfig(failure_threshold=5)
        cb = CircuitBreaker("test", config)
        
        with pytest.raises(ValueError):
            with cb:
                raise ValueError("Error")
        
        assert cb.stats.consecutive_failures == 1
    
    def test_context_manager_blocks_when_open(self):
        """Context manager should raise when circuit is open."""
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker("test", config)
        
        # Trip the circuit
        with pytest.raises(ValueError):
            with cb:
                raise ValueError("Error")
        
        # Should block on entry
        with pytest.raises(CircuitBreakerOpenError):
            with cb:
                pass


class TestCircuitBreakerStats:
    """Test circuit breaker statistics."""
    
    def test_stats_tracked_correctly(self):
        """Statistics should be tracked accurately."""
        config = CircuitBreakerConfig(failure_threshold=10)
        cb = CircuitBreaker("test", config)
        
        @cb.protect
        def mixed_fn(should_fail: bool):
            if should_fail:
                raise ValueError("Error")
            return "ok"
        
        # 3 successes
        for _ in range(3):
            mixed_fn(False)
        
        # 2 failures
        for _ in range(2):
            with pytest.raises(ValueError):
                mixed_fn(True)
        
        # 1 more success
        mixed_fn(False)
        
        assert cb.stats.total_calls == 6
        assert cb.stats.total_successes == 4
        assert cb.stats.total_failures == 2
        assert cb.stats.consecutive_successes == 1
        assert cb.stats.consecutive_failures == 0
    
    def test_manual_reset(self):
        """Manual reset should clear statistics and close circuit."""
        config = CircuitBreakerConfig(failure_threshold=1)
        cb = CircuitBreaker("test", config)
        
        @cb.protect
        def failing_fn():
            raise ValueError("Error")
        
        # Trip the circuit
        with pytest.raises(ValueError):
            failing_fn()
        
        assert cb.state == CircuitState.OPEN
        
        # Reset
        cb.reset()
        
        assert cb.state == CircuitState.CLOSED
        assert cb.stats.total_calls == 0
        assert cb.stats.total_failures == 0


class TestCircuitBreakerRegistry:
    """Test circuit breaker registry functions."""
    
    def test_get_circuit_breaker_creates_new(self):
        """get_circuit_breaker should create new instance."""
        cb = get_circuit_breaker("unique_test_cb")
        assert cb.name == "unique_test_cb"
        assert cb.state == CircuitState.CLOSED
    
    def test_get_circuit_breaker_returns_same(self):
        """get_circuit_breaker should return same instance for same name."""
        cb1 = get_circuit_breaker("shared_test_cb")
        cb2 = get_circuit_breaker("shared_test_cb")
        assert cb1 is cb2


class TestExcludedExceptions:
    """Test excluded exceptions handling."""
    
    def test_excluded_exceptions_not_counted(self):
        """Excluded exceptions should not count as failures."""
        config = CircuitBreakerConfig(
            failure_threshold=2,
            excluded_exceptions=(KeyError,)
        )
        cb = CircuitBreaker("test", config)
        
        @cb.protect
        def fn(error_type):
            if error_type == "key":
                raise KeyError("excluded")
            elif error_type == "value":
                raise ValueError("counted")
        
        # KeyError should not count
        for _ in range(5):
            with pytest.raises(KeyError):
                fn("key")
        
        assert cb.state == CircuitState.CLOSED
        assert cb.stats.consecutive_failures == 0
        
        # ValueError should count
        for _ in range(2):
            with pytest.raises(ValueError):
                fn("value")
        
        assert cb.state == CircuitState.OPEN
