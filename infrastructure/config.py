# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN Configuration Management
Type-safe configuration with Pydantic validation.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from functools import lru_cache


@dataclass(frozen=True)
class ExchangeConfig:
    """Exchange configuration."""
    api_key: str = ""
    secret: str = ""
    password: str = ""
    use_demo: bool = True
    rate_limit_requests_per_second: float = 10.0
    timeout_seconds: float = 30.0


@dataclass(frozen=True)
class RedisConfig:
    """Redis configuration."""
    host: str = "127.0.0.1"
    port: int = 6379
    db: int = 0
    password: Optional[str] = None
    socket_timeout: float = 5.0
    
    @property
    def url(self) -> str:
        """Get Redis URL."""
        auth = f":{self.password}@" if self.password else ""
        return f"redis://{auth}{self.host}:{self.port}/{self.db}"


@dataclass(frozen=True)
class TradingConfig:
    """Trading parameters."""
    pairs: Tuple[str, ...] = ("DOGE/USDT:USDT", "XRP/USDT:USDT", "SOL/USDT:USDT")
    min_trade_usd: float = 5.0
    max_equity_fraction: float = 0.5
    base_equity_fraction: float = 0.9
    initial_equity_usd: float = 23.0


@dataclass(frozen=True)
class DNAConfig:
    """Genetics/DNA configuration."""
    refresh_interval_seconds: int = 60
    fallback_dna: Tuple[int, ...] = (10, 10, 234, 326, 354, 500)
    redis_key: str = "godbrain:genetics:best_dna"
    meta_key: str = "godbrain:genetics:best_meta"


@dataclass(frozen=True)
class LoggingConfig:
    """Logging configuration."""
    level: str = "INFO"
    json_output: bool = False
    log_file: Optional[str] = None
    log_dir: str = "logs"


@dataclass(frozen=True)
class CircuitBreakerConfig:
    """Circuit breaker configuration."""
    failure_threshold: int = 5
    success_threshold: int = 2
    timeout_seconds: float = 60.0


@dataclass(frozen=True)
class Settings:
    """
    Main application settings.
    
    All settings are immutable after creation for thread safety.
    """
    # Core
    app_name: str = "godbrain-quantum"
    version: str = "4.6"
    environment: str = "development"
    root_path: Path = field(default_factory=lambda: Path(__file__).parent.parent)
    
    # Sub-configs
    exchange: ExchangeConfig = field(default_factory=ExchangeConfig)
    redis: RedisConfig = field(default_factory=RedisConfig)
    trading: TradingConfig = field(default_factory=TradingConfig)
    dna: DNAConfig = field(default_factory=DNAConfig)
    logging: LoggingConfig = field(default_factory=LoggingConfig)
    circuit_breaker: CircuitBreakerConfig = field(default_factory=CircuitBreakerConfig)
    
    # Feature flags
    edge_ai_enabled: bool = True
    voltran_enabled: bool = True
    pulse_enabled: bool = True
    cheat_enabled: bool = True
    
    def __post_init__(self):
        """Validate settings after initialization."""
        if self.trading.min_trade_usd <= 0:
            raise ValueError("min_trade_usd must be positive")
        if not 0 < self.trading.max_equity_fraction <= 1:
            raise ValueError("max_equity_fraction must be between 0 and 1")
    
    @property
    def log_dir(self) -> Path:
        """Get log directory path."""
        return self.root_path / self.logging.log_dir
    
    @property
    def config_dir(self) -> Path:
        """Get config directory path."""
        return self.root_path / "config"
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert settings to dictionary (for logging/debugging)."""
        return {
            "app_name": self.app_name,
            "version": self.version,
            "environment": self.environment,
            "root_path": str(self.root_path),
            "trading_pairs": list(self.trading.pairs),
            "redis_host": self.redis.host,
            "edge_ai_enabled": self.edge_ai_enabled,
            "voltran_enabled": self.voltran_enabled,
        }


def _get_env(key: str, default: Any = None, cast: type = str) -> Any:
    """Get environment variable with type casting."""
    value = os.getenv(key, default)
    if value is None:
        return None
    if cast == bool:
        return str(value).lower() in ("true", "1", "yes", "on")
    return cast(value)


def load_settings_from_env() -> Settings:
    """
    Load settings from environment variables.
    
    Environment variable naming convention:
    - GODBRAIN_<SECTION>_<KEY> for nested config
    - GODBRAIN_<KEY> for top-level config
    """
    root_path = Path(_get_env("GODBRAIN_ROOT", Path(__file__).parent.parent))
    
    exchange = ExchangeConfig(
        api_key=_get_env("OKX_API_KEY", ""),
        secret=_get_env("OKX_SECRET", ""),
        password=_get_env("OKX_PASSWORD", "") or _get_env("OKX_PASSPHRASE", ""),
        use_demo=_get_env("OKX_USE_DEMO", True, bool),
        rate_limit_requests_per_second=_get_env("OKX_RATE_LIMIT", 10.0, float),
        timeout_seconds=_get_env("OKX_TIMEOUT", 30.0, float),
    )
    
    redis = RedisConfig(
        host=_get_env("GENETICS_REDIS_HOST", _get_env("REDIS_HOST", "127.0.0.1")),
        port=_get_env("GENETICS_REDIS_PORT", _get_env("REDIS_PORT", 6379), int),
        db=_get_env("GENETICS_REDIS_DB", 0, int),
        password=_get_env("GENETICS_REDIS_PASSWORD", _get_env("REDIS_PASS", None)),
    )
    
    # Parse trading pairs
    pairs_str = _get_env("TRADING_PAIRS", "DOGE/USDT:USDT,XRP/USDT:USDT,SOL/USDT:USDT")
    pairs = tuple(p.strip() for p in pairs_str.split(",") if p.strip())
    
    trading = TradingConfig(
        pairs=pairs,
        min_trade_usd=_get_env("MIN_TRADE_USD", 5.0, float),
        max_equity_fraction=_get_env("MAX_EQUITY_FRACTION", 0.5, float),
        base_equity_fraction=_get_env("BASE_EQUITY_FRACTION", 0.9, float),
        initial_equity_usd=_get_env("INITIAL_EQUITY_USD", 23.0, float),
    )
    
    dna = DNAConfig(
        refresh_interval_seconds=_get_env("DNA_REFRESH_INTERVAL", 60, int),
    )
    
    logging_config = LoggingConfig(
        level=_get_env("LOG_LEVEL", "INFO"),
        json_output=_get_env("LOG_JSON", False, bool),
        log_file=_get_env("LOG_FILE", None),
    )
    
    circuit_breaker = CircuitBreakerConfig(
        failure_threshold=_get_env("CB_FAILURE_THRESHOLD", 5, int),
        success_threshold=_get_env("CB_SUCCESS_THRESHOLD", 2, int),
        timeout_seconds=_get_env("CB_TIMEOUT", 60.0, float),
    )
    
    return Settings(
        app_name=_get_env("APP_NAME", "godbrain-quantum"),
        version=_get_env("APP_VERSION", "4.6"),
        environment=_get_env("ENVIRONMENT", "development"),
        root_path=root_path,
        exchange=exchange,
        redis=redis,
        trading=trading,
        dna=dna,
        logging=logging_config,
        circuit_breaker=circuit_breaker,
        edge_ai_enabled=_get_env("EDGE_AI_ENABLED", True, bool),
        voltran_enabled=_get_env("VOLTRAN_ENABLED", True, bool),
        pulse_enabled=_get_env("PULSE_ENABLED", True, bool),
        cheat_enabled=_get_env("CHEAT_ENABLED", True, bool),
    )


# Cached settings instance
_settings: Optional[Settings] = None


def get_settings(reload: bool = False) -> Settings:
    """
    Get application settings (cached).
    
    Args:
        reload: Force reload from environment
    
    Returns:
        Settings instance
    """
    global _settings
    if _settings is None or reload:
        _settings = load_settings_from_env()
    return _settings


def reset_settings() -> None:
    """Reset cached settings (for testing)."""
    global _settings
    _settings = None
