# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN Integration Tests
End-to-end tests for trading flow.
═══════════════════════════════════════════════════════════════════════════════
"""

import pytest
import asyncio
import sys
from pathlib import Path
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class TestInfrastructureImports:
    """Test that all infrastructure modules can be imported."""
    
    def test_import_logging(self):
        """Test logging module import."""
        from infrastructure.logging_config import get_logger, configure_logging
        logger = get_logger("test")
        assert logger is not None
    
    def test_import_circuit_breaker(self):
        """Test circuit breaker module import."""
        from infrastructure.circuit_breaker import CircuitBreaker, CircuitState
        cb = CircuitBreaker("test_import")
        assert cb.state == CircuitState.CLOSED
    
    def test_import_retry(self):
        """Test retry module import."""
        from infrastructure.retry import with_retry, RetryConfig
        config = RetryConfig(max_attempts=3)
        assert config.max_attempts == 3
    
    def test_import_rate_limiter(self):
        """Test rate limiter module import."""
        from infrastructure.rate_limiter import RateLimiter, TokenBucket
        bucket = TokenBucket(rate=10, capacity=20)
        assert bucket.available_tokens == 20
    
    def test_import_metrics(self):
        """Test metrics module import."""
        from infrastructure.metrics import metrics, Counter, Gauge
        assert metrics is not None
        assert hasattr(metrics, "trades_total")
    
    def test_import_health(self):
        """Test health module import."""
        from infrastructure.health import HealthCheck, HealthStatus
        health = HealthCheck()
        assert health.liveness() is True
    
    def test_import_config(self):
        """Test config module import."""
        from infrastructure.config import get_settings
        settings = get_settings()
        assert settings.app_name == "godbrain-quantum"
    
    def test_import_exceptions(self):
        """Test exceptions module import."""
        from infrastructure.exceptions import (
            GodbrainError,
            ExchangeError,
            CircuitBreakerOpenError,
        )
        err = GodbrainError("test", code="TEST", details={"key": "value"})
        assert err.code == "TEST"


class TestMetricsIntegration:
    """Test metrics collection integration."""
    
    def test_counter_increment(self):
        """Test counter incrementing with labels."""
        from infrastructure.metrics import Counter
        
        counter = Counter("test_trades", "Test trades", ["symbol", "side"])
        counter.inc(labels={"symbol": "BTC/USDT", "side": "BUY"})
        counter.inc(labels={"symbol": "BTC/USDT", "side": "BUY"})
        counter.inc(labels={"symbol": "ETH/USDT", "side": "SELL"})
        
        assert counter.get({"symbol": "BTC/USDT", "side": "BUY"}) == 2
        assert counter.get({"symbol": "ETH/USDT", "side": "SELL"}) == 1
    
    def test_gauge_operations(self):
        """Test gauge set/inc/dec."""
        from infrastructure.metrics import Gauge
        
        gauge = Gauge("test_equity", "Test equity")
        gauge.set(1000.0)
        assert gauge.get() == 1000.0
        
        gauge.inc(100.0)
        assert gauge.get() == 1100.0
        
        gauge.dec(50.0)
        assert gauge.get() == 1050.0
    
    def test_histogram_observation(self):
        """Test histogram observation and timing."""
        from infrastructure.metrics import Histogram
        import time
        
        hist = Histogram("test_latency", "Test latency")
        
        # Manual observation
        hist.observe(0.1)
        hist.observe(0.5)
        hist.observe(1.5)
        
        data = hist.collect()
        assert len(data) > 0
    
    def test_histogram_time_context(self):
        """Test histogram time context manager."""
        from infrastructure.metrics import Histogram
        import time
        
        hist = Histogram("test_duration", "Test duration")
        
        with hist.time():
            time.sleep(0.01)
        
        data = hist.collect()
        assert len(data) > 0


class TestLoggingIntegration:
    """Test logging integration."""
    
    def test_correlation_id_propagation(self):
        """Test correlation ID context manager."""
        from infrastructure.logging_config import correlation_context, get_correlation_id
        
        with correlation_context("test-123") as cid:
            assert cid == "test-123"
            assert get_correlation_id() == "test-123"
        
        # Outside context, should be empty or default
        assert get_correlation_id() in ("", "-")
    
    def test_logger_creation(self):
        """Test logger creation and usage."""
        from infrastructure.logging_config import get_logger
        
        logger = get_logger("test.module")
        logger.info("Test message")
        logger.warning("Warning message")
        
        # Should not raise
        assert True


class TestRetryIntegration:
    """Test retry logic integration."""
    
    def test_retry_succeeds_eventually(self):
        """Test that retry succeeds after temporary failures."""
        from infrastructure.retry import with_retry, RetryConfig
        
        attempt_count = 0
        
        @with_retry(RetryConfig(max_attempts=3, base_delay=0.01))
        def flaky_fn():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 3:
                raise ValueError("Not ready")
            return "success"
        
        result = flaky_fn()
        assert result == "success"
        assert attempt_count == 3
    
    def test_retry_exhausts_attempts(self):
        """Test that retry raises after all attempts exhausted."""
        from infrastructure.retry import with_retry, RetryConfig
        
        @with_retry(RetryConfig(max_attempts=2, base_delay=0.01))
        def always_fails():
            raise ValueError("Always fails")
        
        with pytest.raises(ValueError):
            always_fails()
    
    @pytest.mark.asyncio
    async def test_async_retry(self):
        """Test async retry functionality."""
        from infrastructure.retry import with_async_retry, RetryConfig
        
        attempt_count = 0
        
        @with_async_retry(RetryConfig(max_attempts=3, base_delay=0.01))
        async def async_flaky():
            nonlocal attempt_count
            attempt_count += 1
            if attempt_count < 2:
                raise ValueError("Not ready")
            return "async_success"
        
        result = await async_flaky()
        assert result == "async_success"


class TestRateLimiterIntegration:
    """Test rate limiter integration."""
    
    def test_token_bucket_allows_burst(self):
        """Test that token bucket allows burst up to capacity."""
        from infrastructure.rate_limiter import TokenBucket
        
        bucket = TokenBucket(rate=10, capacity=5)
        
        # Should allow 5 immediate requests
        for _ in range(5):
            assert bucket.acquire(wait=False)
        
        # 6th should fail (no wait)
        assert not bucket.acquire(wait=False)
    
    def test_token_bucket_refills(self):
        """Test that token bucket refills over time."""
        import time
        from infrastructure.rate_limiter import TokenBucket
        
        bucket = TokenBucket(rate=100, capacity=5)  # 100/sec = 0.01 sec per token
        
        # Exhaust tokens
        for _ in range(5):
            bucket.acquire(wait=False)
        
        # Wait for refill
        time.sleep(0.05)  # Should get ~5 tokens
        
        # Should have some tokens now
        assert bucket.available_tokens > 0


class TestHealthCheckIntegration:
    """Test health check integration."""
    
    @pytest.mark.asyncio
    async def test_empty_health_check(self):
        """Test health check with no components."""
        from infrastructure.health import HealthCheck, HealthStatus
        
        health = HealthCheck()
        result = await health.check_all()
        
        assert result.status == HealthStatus.HEALTHY
        assert result.is_healthy
        assert result.is_ready
    
    @pytest.mark.asyncio
    async def test_health_check_with_component(self):
        """Test health check with registered component."""
        from infrastructure.health import HealthCheck, HealthStatus, ComponentHealth
        
        health = HealthCheck()
        
        def check_component():
            return ComponentHealth(
                name="test_component",
                status=HealthStatus.HEALTHY,
                message="OK"
            )
        
        health.register("test_component", check_component)
        result = await health.check_all()
        
        assert result.status == HealthStatus.HEALTHY
        assert len(result.components) == 1
        assert result.components[0].name == "test_component"
    
    @pytest.mark.asyncio
    async def test_health_check_degraded(self):
        """Test health check with degraded component."""
        from infrastructure.health import HealthCheck, HealthStatus, ComponentHealth
        
        health = HealthCheck()
        
        def check_degraded():
            return ComponentHealth(
                name="degraded_component",
                status=HealthStatus.DEGRADED,
                message="Slow response"
            )
        
        health.register("degraded", check_degraded, critical=False)
        result = await health.check_all()
        
        assert result.status == HealthStatus.DEGRADED
        assert result.is_ready  # Still ready, just degraded


class TestConfigIntegration:
    """Test configuration integration."""
    
    def test_settings_load(self, test_env):
        """Test settings load from environment."""
        from infrastructure.config import load_settings_from_env
        
        settings = load_settings_from_env()
        assert settings.environment == "test"
        assert settings.logging.level == "DEBUG"
    
    def test_settings_immutable(self, test_settings):
        """Test that settings are immutable."""
        with pytest.raises((AttributeError, TypeError)):
            test_settings.app_name = "changed"
    
    def test_settings_to_dict(self, test_settings):
        """Test settings serialization."""
        d = test_settings.to_dict()
        assert "app_name" in d
        assert "trading_pairs" in d


@pytest.mark.asyncio
class TestDecisionFlowIntegration:
    """Test decision engine flow (mocked)."""
    
    async def test_decision_engine_import(self):
        """Test decision engine can be imported."""
        try:
            from engines.decision_engine import DecisionEngine, DecisionEngineConfig
            config = DecisionEngineConfig()
            assert config.min_trade_usd == 5.0
        except ImportError as e:
            pytest.skip(f"DecisionEngine not available: {e}")
    
    async def test_mock_decision_flow(self, mock_ultimate_brain, mock_signal_filter):
        """Test decision flow with mocks."""
        # This tests that the mocks are properly configured
        decision = await mock_ultimate_brain.get_signal("BTC/USDT", 1000.0, None)
        assert decision.action == "HOLD"
        
        filtered = mock_signal_filter.filter("BUY", 0.8)
        assert filtered.should_execute is True


class TestExceptionsIntegration:
    """Test exception handling integration."""
    
    def test_exception_to_dict(self):
        """Test exception serialization."""
        from infrastructure.exceptions import ExchangeAPIError
        
        err = ExchangeAPIError(
            "API error",
            status_code=429,
            exchange_code="RATE_LIMIT",
            details={"endpoint": "/api/v5/trade"}
        )
        
        d = err.to_dict()
        assert d["error"] == "ExchangeAPIError"
        assert d["details"]["status_code"] == 429
        assert d["details"]["exchange_code"] == "RATE_LIMIT"
    
    def test_exception_inheritance(self):
        """Test exception hierarchy."""
        from infrastructure.exceptions import (
            GodbrainError,
            ExchangeError,
            ExchangeAPIError,
        )
        
        err = ExchangeAPIError("Test")
        assert isinstance(err, ExchangeError)
        assert isinstance(err, GodbrainError)
        assert isinstance(err, Exception)
