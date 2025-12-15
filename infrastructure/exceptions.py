# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN Exception Hierarchy
Structured exception classes for proper error handling.
═══════════════════════════════════════════════════════════════════════════════
"""

from typing import Any, Dict, Optional


class GodbrainError(Exception):
    """Base exception for all GODBRAIN errors."""
    
    def __init__(
        self,
        message: str,
        code: Optional[str] = None,
        details: Optional[Dict[str, Any]] = None
    ):
        super().__init__(message)
        self.message = message
        self.code = code or self.__class__.__name__
        self.details = details or {}
    
    def to_dict(self) -> Dict[str, Any]:
        """Convert exception to dictionary for logging/serialization."""
        return {
            "error": self.code,
            "message": self.message,
            "details": self.details,
        }
    
    def __str__(self) -> str:
        if self.details:
            return f"[{self.code}] {self.message} | {self.details}"
        return f"[{self.code}] {self.message}"


# =============================================================================
# Infrastructure Errors
# =============================================================================

class ConfigurationError(GodbrainError):
    """Raised when configuration is invalid or missing."""
    pass


class ValidationError(GodbrainError):
    """Raised when data validation fails."""
    
    def __init__(self, message: str, field: Optional[str] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.field = field
        if field:
            self.details["field"] = field


class CircuitBreakerOpenError(GodbrainError):
    """Raised when circuit breaker is open and blocking calls."""
    
    def __init__(
        self,
        message: str,
        circuit_name: str,
        has_fallback: bool = False,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.circuit_name = circuit_name
        self.has_fallback = has_fallback
        self.details["circuit_name"] = circuit_name
        self.details["has_fallback"] = has_fallback


class RateLimitError(GodbrainError):
    """Raised when rate limit is exceeded."""
    
    def __init__(self, message: str, retry_after: Optional[float] = None, **kwargs):
        super().__init__(message, **kwargs)
        self.retry_after = retry_after
        if retry_after:
            self.details["retry_after_seconds"] = retry_after


# =============================================================================
# Exchange Errors
# =============================================================================

class ExchangeError(GodbrainError):
    """Base exception for exchange-related errors."""
    pass


class ExchangeConnectionError(ExchangeError):
    """Raised when connection to exchange fails."""
    pass


class ExchangeAPIError(ExchangeError):
    """Raised when exchange API returns an error."""
    
    def __init__(
        self,
        message: str,
        status_code: Optional[int] = None,
        exchange_code: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.status_code = status_code
        self.exchange_code = exchange_code
        if status_code:
            self.details["status_code"] = status_code
        if exchange_code:
            self.details["exchange_code"] = exchange_code


class InsufficientBalanceError(ExchangeError):
    """Raised when balance is insufficient for trade."""
    
    def __init__(
        self,
        message: str,
        required: float,
        available: float,
        asset: str = "USDT",
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.required = required
        self.available = available
        self.asset = asset
        self.details.update({
            "required": required,
            "available": available,
            "asset": asset,
        })


class OrderError(ExchangeError):
    """Raised when order placement fails."""
    
    def __init__(
        self,
        message: str,
        symbol: Optional[str] = None,
        side: Optional[str] = None,
        order_type: Optional[str] = None,
        **kwargs
    ):
        super().__init__(message, **kwargs)
        self.symbol = symbol
        self.side = side
        self.order_type = order_type
        if symbol:
            self.details["symbol"] = symbol
        if side:
            self.details["side"] = side
        if order_type:
            self.details["order_type"] = order_type


# =============================================================================
# Trading Errors
# =============================================================================

class TradingError(GodbrainError):
    """Base exception for trading logic errors."""
    pass


class SignalFilteredError(TradingError):
    """Raised when a signal is filtered/blocked."""
    
    def __init__(self, message: str, filter_reason: str, **kwargs):
        super().__init__(message, **kwargs)
        self.filter_reason = filter_reason
        self.details["filter_reason"] = filter_reason


class RegimeError(TradingError):
    """Raised when regime detection fails or is invalid."""
    pass


class DNAError(TradingError):
    """Raised when DNA/genetics system encounters an error."""
    pass


# =============================================================================
# Data Errors
# =============================================================================

class DataError(GodbrainError):
    """Base exception for data-related errors."""
    pass


class DataFeedError(DataError):
    """Raised when data feed is unavailable or returns invalid data."""
    
    def __init__(self, message: str, feed_name: str, **kwargs):
        super().__init__(message, **kwargs)
        self.feed_name = feed_name
        self.details["feed_name"] = feed_name


class RedisError(DataError):
    """Raised when Redis operations fail."""
    pass


class StaleDataError(DataError):
    """Raised when data is too old to be reliable."""
    
    def __init__(self, message: str, data_age_seconds: float, max_age_seconds: float, **kwargs):
        super().__init__(message, **kwargs)
        self.data_age_seconds = data_age_seconds
        self.max_age_seconds = max_age_seconds
        self.details["data_age_seconds"] = data_age_seconds
        self.details["max_age_seconds"] = max_age_seconds
