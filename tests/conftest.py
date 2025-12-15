# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN Test Configuration
Pytest fixtures for unit and integration tests.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import asyncio
from pathlib import Path
from typing import Any, Dict, Generator, List
from unittest.mock import AsyncMock, MagicMock, patch
from dataclasses import dataclass

import pytest
import pandas as pd
import numpy as np

# Add project root to path
ROOT = Path(__file__).parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


# =============================================================================
# Pytest Configuration
# =============================================================================

def pytest_configure(config):
    """Configure pytest markers."""
    config.addinivalue_line("markers", "slow: marks tests as slow")
    config.addinivalue_line("markers", "integration: marks tests as integration tests")
    config.addinivalue_line("markers", "unit: marks tests as unit tests")


# =============================================================================
# Event Loop Fixture
# =============================================================================

@pytest.fixture(scope="session")
def event_loop():
    """Create event loop for async tests."""
    loop = asyncio.new_event_loop()
    yield loop
    loop.close()


# =============================================================================
# Sample Data Fixtures
# =============================================================================

@pytest.fixture
def sample_ohlcv() -> pd.DataFrame:
    """Create sample OHLCV data for testing."""
    np.random.seed(42)
    n = 200
    
    # Generate realistic price data
    base_price = 100.0
    returns = np.random.normal(0, 0.02, n)
    prices = base_price * np.cumprod(1 + returns)
    
    data = {
        "timestamp": pd.date_range(end=pd.Timestamp.now(), periods=n, freq="1h"),
        "open": prices * (1 + np.random.uniform(-0.01, 0.01, n)),
        "high": prices * (1 + np.random.uniform(0.005, 0.02, n)),
        "low": prices * (1 - np.random.uniform(0.005, 0.02, n)),
        "close": prices,
        "vol": np.random.uniform(1000, 10000, n),
    }
    
    df = pd.DataFrame(data)
    # Ensure high/low relationship is correct
    df["high"] = df[["open", "high", "close"]].max(axis=1)
    df["low"] = df[["open", "low", "close"]].min(axis=1)
    
    return df


@pytest.fixture
def sample_ohlcv_bullish() -> pd.DataFrame:
    """Create bullish OHLCV data."""
    np.random.seed(42)
    n = 200
    
    # Upward trending prices
    trend = np.linspace(0, 0.5, n)
    noise = np.random.normal(0, 0.01, n)
    prices = 100.0 * (1 + trend + noise)
    
    return pd.DataFrame({
        "timestamp": pd.date_range(end=pd.Timestamp.now(), periods=n, freq="1h"),
        "open": prices * 0.99,
        "high": prices * 1.01,
        "low": prices * 0.98,
        "close": prices,
        "vol": np.random.uniform(1000, 10000, n),
    })


@pytest.fixture
def sample_ohlcv_bearish() -> pd.DataFrame:
    """Create bearish OHLCV data."""
    np.random.seed(42)
    n = 200
    
    # Downward trending prices
    trend = np.linspace(0, -0.3, n)
    noise = np.random.normal(0, 0.01, n)
    prices = 100.0 * (1 + trend + noise)
    
    return pd.DataFrame({
        "timestamp": pd.date_range(end=pd.Timestamp.now(), periods=n, freq="1h"),
        "open": prices * 1.01,
        "high": prices * 1.02,
        "low": prices * 0.99,
        "close": prices,
        "vol": np.random.uniform(1000, 10000, n),
    })


# =============================================================================
# Mock Exchange Fixtures
# =============================================================================

@dataclass
class MockBalance:
    """Mock exchange balance."""
    total: Dict[str, float]
    free: Dict[str, float]
    used: Dict[str, float]


@pytest.fixture
def mock_exchange() -> MagicMock:
    """Create mock exchange client."""
    exchange = MagicMock()
    
    # Mock balance
    exchange.fetch_balance.return_value = {
        "total": {"USDT": 1000.0, "BTC": 0.0},
        "free": {"USDT": 1000.0, "BTC": 0.0},
        "used": {"USDT": 0.0, "BTC": 0.0},
    }
    
    # Mock OHLCV
    exchange.fetch_ohlcv = MagicMock(return_value=[
        [1700000000000, 100.0, 101.0, 99.0, 100.5, 1000.0],
        [1700003600000, 100.5, 102.0, 100.0, 101.5, 1200.0],
    ])
    
    # Mock ticker
    exchange.fetch_ticker.return_value = {
        "symbol": "BTC/USDT",
        "last": 100.5,
        "bid": 100.4,
        "ask": 100.6,
        "volume": 10000.0,
    }
    
    # Mock order creation
    exchange.create_order.return_value = {
        "id": "test-order-123",
        "symbol": "BTC/USDT",
        "side": "buy",
        "amount": 0.01,
        "price": 100.5,
        "status": "closed",
    }
    
    exchange.load_markets.return_value = True
    
    return exchange


@pytest.fixture
def mock_async_exchange() -> AsyncMock:
    """Create async mock exchange client."""
    exchange = AsyncMock()
    
    exchange.fetch_balance.return_value = {
        "total": {"USDT": 1000.0},
        "free": {"USDT": 1000.0},
        "used": {"USDT": 0.0},
    }
    
    exchange.fetch_ohlcv.return_value = [
        [1700000000000, 100.0, 101.0, 99.0, 100.5, 1000.0],
    ]
    
    return exchange


# =============================================================================
# Mock Redis Fixtures
# =============================================================================

@pytest.fixture
def mock_redis() -> MagicMock:
    """Create mock Redis client."""
    redis = MagicMock()
    
    # In-memory storage for tests
    storage: Dict[str, Any] = {}
    
    def mock_get(key):
        return storage.get(key)
    
    def mock_set(key, value, **kwargs):
        storage[key] = value
        return True
    
    def mock_delete(*keys):
        for key in keys:
            storage.pop(key, None)
        return len(keys)
    
    redis.get = MagicMock(side_effect=mock_get)
    redis.set = MagicMock(side_effect=mock_set)
    redis.delete = MagicMock(side_effect=mock_delete)
    redis.ping.return_value = True
    redis.info.return_value = {"redis_version": "7.0.0"}
    
    # List operations
    lists: Dict[str, List] = {}
    
    def mock_lpush(key, *values):
        if key not in lists:
            lists[key] = []
        for v in values:
            lists[key].insert(0, v)
        return len(lists[key])
    
    def mock_rpop(key):
        if key in lists and lists[key]:
            return lists[key].pop()
        return None
    
    redis.lpush = MagicMock(side_effect=mock_lpush)
    redis.rpop = MagicMock(side_effect=mock_rpop)
    redis.lrange = MagicMock(return_value=[])
    redis.ltrim = MagicMock(return_value=True)
    
    return redis


# =============================================================================
# Configuration Fixtures
# =============================================================================

@pytest.fixture
def test_settings():
    """Create test settings."""
    from infrastructure.config import Settings, ExchangeConfig, RedisConfig, TradingConfig
    
    return Settings(
        app_name="godbrain-test",
        version="test",
        environment="test",
        exchange=ExchangeConfig(use_demo=True),
        redis=RedisConfig(host="localhost", port=6379),
        trading=TradingConfig(
            pairs=("BTC/USDT:USDT",),
            min_trade_usd=1.0,
        ),
    )


@pytest.fixture
def test_env(monkeypatch):
    """Set test environment variables."""
    monkeypatch.setenv("ENVIRONMENT", "test")
    monkeypatch.setenv("LOG_LEVEL", "DEBUG")
    monkeypatch.setenv("OKX_USE_DEMO", "true")
    monkeypatch.setenv("REDIS_HOST", "localhost")


# =============================================================================
# Decision Engine Fixtures
# =============================================================================

@pytest.fixture
def mock_ultimate_brain() -> AsyncMock:
    """Create mock UltimateConnector."""
    brain = AsyncMock()
    
    @dataclass
    class MockDecision:
        action: str = "HOLD"
        conviction: float = 0.5
        regime: str = "NEUTRAL"
        position_size_usd: float = 100.0
    
    brain.get_signal.return_value = MockDecision()
    brain.initialized = True
    
    return brain


@pytest.fixture
def mock_signal_filter() -> MagicMock:
    """Create mock signal filter."""
    from dataclasses import dataclass
    
    @dataclass
    class FilteredSignal:
        should_execute: bool = True
        filtered_action: str = "BUY"
        filter_reason: str = "PASS"
        conviction_boost: float = 0.0
    
    filter_mock = MagicMock()
    filter_mock.filter.return_value = FilteredSignal()
    filter_mock.record_trade = MagicMock()
    
    return filter_mock


# =============================================================================
# Cleanup Fixtures
# =============================================================================

@pytest.fixture(autouse=True)
def reset_singletons():
    """Reset singleton instances between tests."""
    yield
    
    # Reset infrastructure singletons
    try:
        from infrastructure.config import reset_settings
        reset_settings()
    except ImportError:
        pass
    
    try:
        from infrastructure.metrics import metrics
        # Reset counters
        metrics.trades_total._values.clear()
        metrics.errors_total._values.clear()
    except ImportError:
        pass


@pytest.fixture
def temp_log_dir(tmp_path) -> Path:
    """Create temporary log directory."""
    log_dir = tmp_path / "logs"
    log_dir.mkdir()
    return log_dir
