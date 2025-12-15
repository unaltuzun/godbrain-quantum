# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN Retry Logic
Exponential backoff with jitter for resilient external service calls.
═══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
import random
import time
from dataclasses import dataclass
from functools import wraps
from typing import Any, Callable, Optional, Tuple, Type, TypeVar, Union

from .logging_config import get_logger

logger = get_logger(__name__)

T = TypeVar("T")


@dataclass
class RetryConfig:
    """Retry configuration."""
    max_attempts: int = 3
    base_delay: float = 1.0           # Base delay in seconds
    max_delay: float = 60.0           # Maximum delay cap
    exponential_base: float = 2.0     # Exponential backoff base
    jitter: bool = True               # Add randomness to prevent thundering herd
    jitter_range: Tuple[float, float] = (0.8, 1.2)  # Jitter multiplier range
    retryable_exceptions: Tuple[Type[Exception], ...] = (Exception,)
    non_retryable_exceptions: Tuple[Type[Exception], ...] = ()


def calculate_delay(
    attempt: int,
    config: RetryConfig
) -> float:
    """Calculate delay for the given attempt number."""
    delay = config.base_delay * (config.exponential_base ** attempt)
    delay = min(delay, config.max_delay)
    
    if config.jitter:
        jitter_mult = random.uniform(*config.jitter_range)
        delay *= jitter_mult
    
    return delay


def should_retry(
    exception: Exception,
    config: RetryConfig
) -> bool:
    """Determine if the exception should trigger a retry."""
    # Non-retryable exceptions always fail fast
    if isinstance(exception, config.non_retryable_exceptions):
        return False
    
    # Check if it's in retryable list
    return isinstance(exception, config.retryable_exceptions)


def with_retry(
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for synchronous functions with retry logic.
    
    Usage:
        @with_retry(RetryConfig(max_attempts=3))
        def call_api():
            ...
    """
    cfg = config or RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        def wrapper(*args, **kwargs) -> T:
            last_exception: Optional[Exception] = None
            
            for attempt in range(cfg.max_attempts):
                try:
                    return func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if not should_retry(e, cfg):
                        logger.warning(
                            f"Non-retryable error in {func.__name__}: {e}",
                            extra={"extra": {"function": func.__name__, "attempt": attempt + 1}}
                        )
                        raise
                    
                    if attempt < cfg.max_attempts - 1:
                        delay = calculate_delay(attempt, cfg)
                        logger.warning(
                            f"Retry {attempt + 1}/{cfg.max_attempts} for {func.__name__} after {delay:.2f}s: {e}",
                            extra={"extra": {"function": func.__name__, "attempt": attempt + 1, "delay": delay}}
                        )
                        
                        if on_retry:
                            on_retry(e, attempt + 1)
                        
                        time.sleep(delay)
            
            logger.error(
                f"All {cfg.max_attempts} retries exhausted for {func.__name__}",
                extra={"extra": {"function": func.__name__}}
            )
            raise last_exception
        
        return wrapper
    return decorator


def with_async_retry(
    config: Optional[RetryConfig] = None,
    on_retry: Optional[Callable[[Exception, int], None]] = None
) -> Callable[[Callable[..., T]], Callable[..., T]]:
    """
    Decorator for async functions with retry logic.
    
    Usage:
        @with_async_retry(RetryConfig(max_attempts=3))
        async def call_api():
            ...
    """
    cfg = config or RetryConfig()
    
    def decorator(func: Callable[..., T]) -> Callable[..., T]:
        @wraps(func)
        async def wrapper(*args, **kwargs) -> T:
            last_exception: Optional[Exception] = None
            
            for attempt in range(cfg.max_attempts):
                try:
                    return await func(*args, **kwargs)
                except Exception as e:
                    last_exception = e
                    
                    if not should_retry(e, cfg):
                        logger.warning(f"Non-retryable error in {func.__name__}: {e}")
                        raise
                    
                    if attempt < cfg.max_attempts - 1:
                        delay = calculate_delay(attempt, cfg)
                        logger.warning(
                            f"Retry {attempt + 1}/{cfg.max_attempts} for {func.__name__} after {delay:.2f}s: {e}"
                        )
                        
                        if on_retry:
                            on_retry(e, attempt + 1)
                        
                        await asyncio.sleep(delay)
            
            logger.error(f"All {cfg.max_attempts} retries exhausted for {func.__name__}")
            raise last_exception
        
        return wrapper
    return decorator


class RetryContext:
    """
    Context manager for retry logic with manual control.
    
    Usage:
        async with RetryContext(config) as ctx:
            while ctx.should_continue:
                try:
                    result = await call_api()
                    break
                except Exception as e:
                    await ctx.handle_error(e)
    """
    
    def __init__(self, config: Optional[RetryConfig] = None):
        self.config = config or RetryConfig()
        self.attempt = 0
        self.last_exception: Optional[Exception] = None
        self._exhausted = False
    
    @property
    def should_continue(self) -> bool:
        """Check if more attempts are available."""
        return self.attempt < self.config.max_attempts and not self._exhausted
    
    async def handle_error(self, exception: Exception) -> None:
        """Handle an error, potentially sleeping before next attempt."""
        self.last_exception = exception
        self.attempt += 1
        
        if not should_retry(exception, self.config):
            self._exhausted = True
            raise exception
        
        if self.attempt >= self.config.max_attempts:
            self._exhausted = True
            raise exception
        
        delay = calculate_delay(self.attempt - 1, self.config)
        logger.warning(f"Retry attempt {self.attempt}/{self.config.max_attempts} after {delay:.2f}s")
        await asyncio.sleep(delay)
    
    def handle_error_sync(self, exception: Exception) -> None:
        """Synchronous version of handle_error."""
        self.last_exception = exception
        self.attempt += 1
        
        if not should_retry(exception, self.config):
            self._exhausted = True
            raise exception
        
        if self.attempt >= self.config.max_attempts:
            self._exhausted = True
            raise exception
        
        delay = calculate_delay(self.attempt - 1, self.config)
        logger.warning(f"Retry attempt {self.attempt}/{self.config.max_attempts} after {delay:.2f}s")
        time.sleep(delay)
    
    async def __aenter__(self) -> "RetryContext":
        return self
    
    async def __aexit__(self, *args):
        pass
    
    def __enter__(self) -> "RetryContext":
        return self
    
    def __exit__(self, *args):
        pass
