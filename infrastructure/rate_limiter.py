# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN Rate Limiter
Token bucket implementation for exchange API rate limiting.
═══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
import threading
import time
from dataclasses import dataclass
from typing import Dict, Optional

from .logging_config import get_logger
from .exceptions import RateLimitError

logger = get_logger(__name__)


@dataclass
class RateLimitConfig:
    """Rate limit configuration."""
    requests_per_second: float = 10.0     # Max requests per second
    burst_size: int = 20                   # Max burst capacity
    wait_on_limit: bool = True             # Wait or raise exception
    max_wait_seconds: float = 5.0          # Max wait time


class TokenBucket:
    """
    Token bucket rate limiter implementation.
    
    Allows bursts up to burst_size, then throttles to requests_per_second.
    """
    
    def __init__(self, rate: float, capacity: int):
        """
        Initialize token bucket.
        
        Args:
            rate: Tokens added per second
            capacity: Maximum tokens in bucket
        """
        self.rate = rate
        self.capacity = capacity
        self.tokens = float(capacity)
        self.last_update = time.monotonic()
        self._lock = threading.Lock()
    
    def _refill(self) -> None:
        """Refill tokens based on elapsed time."""
        now = time.monotonic()
        elapsed = now - self.last_update
        self.tokens = min(self.capacity, self.tokens + elapsed * self.rate)
        self.last_update = now
    
    def acquire(self, tokens: int = 1, wait: bool = True, timeout: float = 5.0) -> bool:
        """
        Acquire tokens from the bucket.
        
        Args:
            tokens: Number of tokens to acquire
            wait: If True, wait for tokens; if False, return immediately
            timeout: Maximum wait time in seconds
        
        Returns:
            True if tokens acquired, False if not (when wait=False)
        
        Raises:
            RateLimitError: If wait=True and timeout exceeded
        """
        start_time = time.monotonic()
        
        while True:
            with self._lock:
                self._refill()
                
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
                
                if not wait:
                    return False
                
                # Calculate wait time
                tokens_needed = tokens - self.tokens
                wait_time = tokens_needed / self.rate
            
            # Check timeout
            elapsed = time.monotonic() - start_time
            if elapsed + wait_time > timeout:
                raise RateLimitError(
                    f"Rate limit timeout after {elapsed:.2f}s",
                    retry_after=wait_time
                )
            
            time.sleep(min(wait_time, 0.1))
    
    async def acquire_async(self, tokens: int = 1, wait: bool = True, timeout: float = 5.0) -> bool:
        """Async version of acquire."""
        start_time = time.monotonic()
        
        while True:
            with self._lock:
                self._refill()
                
                if self.tokens >= tokens:
                    self.tokens -= tokens
                    return True
                
                if not wait:
                    return False
                
                tokens_needed = tokens - self.tokens
                wait_time = tokens_needed / self.rate
            
            elapsed = time.monotonic() - start_time
            if elapsed + wait_time > timeout:
                raise RateLimitError(
                    f"Rate limit timeout after {elapsed:.2f}s",
                    retry_after=wait_time
                )
            
            await asyncio.sleep(min(wait_time, 0.1))
    
    @property
    def available_tokens(self) -> float:
        """Get current available tokens."""
        with self._lock:
            self._refill()
            return self.tokens


class RateLimiter:
    """
    Multi-endpoint rate limiter.
    
    Manages separate rate limits for different API endpoints.
    """
    
    # OKX Rate Limits (from docs)
    OKX_LIMITS = {
        "trade": RateLimitConfig(requests_per_second=10, burst_size=20),
        "order": RateLimitConfig(requests_per_second=20, burst_size=60),
        "account": RateLimitConfig(requests_per_second=5, burst_size=10),
        "market": RateLimitConfig(requests_per_second=20, burst_size=40),
        "default": RateLimitConfig(requests_per_second=10, burst_size=20),
    }
    
    def __init__(self, limits: Optional[Dict[str, RateLimitConfig]] = None):
        """
        Initialize rate limiter.
        
        Args:
            limits: Endpoint-specific rate limit configurations
        """
        self.limits = limits or self.OKX_LIMITS
        self._buckets: Dict[str, TokenBucket] = {}
        self._lock = threading.Lock()
        
        # Pre-create buckets
        for endpoint, config in self.limits.items():
            self._buckets[endpoint] = TokenBucket(
                rate=config.requests_per_second,
                capacity=config.burst_size
            )
    
    def _get_bucket(self, endpoint: str) -> TokenBucket:
        """Get or create bucket for endpoint."""
        if endpoint not in self._buckets:
            with self._lock:
                if endpoint not in self._buckets:
                    config = self.limits.get(endpoint, self.limits["default"])
                    self._buckets[endpoint] = TokenBucket(
                        rate=config.requests_per_second,
                        capacity=config.burst_size
                    )
        return self._buckets[endpoint]
    
    def acquire(self, endpoint: str = "default", tokens: int = 1) -> bool:
        """
        Acquire rate limit tokens for an endpoint.
        
        Args:
            endpoint: API endpoint category
            tokens: Number of tokens to acquire
        
        Returns:
            True when tokens acquired (may wait)
        """
        config = self.limits.get(endpoint, self.limits["default"])
        bucket = self._get_bucket(endpoint)
        
        try:
            return bucket.acquire(
                tokens=tokens,
                wait=config.wait_on_limit,
                timeout=config.max_wait_seconds
            )
        except RateLimitError:
            logger.warning(f"Rate limit exceeded for {endpoint}")
            raise
    
    async def acquire_async(self, endpoint: str = "default", tokens: int = 1) -> bool:
        """Async version of acquire."""
        config = self.limits.get(endpoint, self.limits["default"])
        bucket = self._get_bucket(endpoint)
        
        try:
            return await bucket.acquire_async(
                tokens=tokens,
                wait=config.wait_on_limit,
                timeout=config.max_wait_seconds
            )
        except RateLimitError:
            logger.warning(f"Rate limit exceeded for {endpoint}")
            raise
    
    def get_status(self) -> Dict[str, Dict]:
        """Get rate limiter status for all endpoints."""
        status = {}
        for endpoint, bucket in self._buckets.items():
            status[endpoint] = {
                "available_tokens": bucket.available_tokens,
                "capacity": bucket.capacity,
                "rate": bucket.rate,
            }
        return status


# Global rate limiter instance
_rate_limiter: Optional[RateLimiter] = None


def get_rate_limiter() -> RateLimiter:
    """Get or create global rate limiter."""
    global _rate_limiter
    if _rate_limiter is None:
        _rate_limiter = RateLimiter()
    return _rate_limiter
