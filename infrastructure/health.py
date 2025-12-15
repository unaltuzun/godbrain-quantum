# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN Health Check System
Liveness and readiness probes for Kubernetes/Docker orchestration.
═══════════════════════════════════════════════════════════════════════════════
"""

import time
import asyncio
from dataclasses import dataclass, field
from enum import Enum
from typing import Any, Callable, Dict, List, Optional
from datetime import datetime

from .logging_config import get_logger

logger = get_logger(__name__)


class HealthStatus(Enum):
    """Health check status."""
    HEALTHY = "healthy"
    DEGRADED = "degraded"
    UNHEALTHY = "unhealthy"
    UNKNOWN = "unknown"


@dataclass
class ComponentHealth:
    """Health status for a single component."""
    name: str
    status: HealthStatus
    message: str = ""
    latency_ms: float = 0.0
    last_check: float = field(default_factory=time.time)
    details: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "name": self.name,
            "status": self.status.value,
            "message": self.message,
            "latency_ms": round(self.latency_ms, 2),
            "last_check": datetime.fromtimestamp(self.last_check).isoformat(),
            "details": self.details,
        }


@dataclass 
class HealthCheckResult:
    """Aggregate health check result."""
    status: HealthStatus
    components: List[ComponentHealth]
    timestamp: float = field(default_factory=time.time)
    
    @property
    def is_healthy(self) -> bool:
        return self.status == HealthStatus.HEALTHY
    
    @property
    def is_ready(self) -> bool:
        return self.status in (HealthStatus.HEALTHY, HealthStatus.DEGRADED)
    
    def to_dict(self) -> Dict[str, Any]:
        return {
            "status": self.status.value,
            "is_healthy": self.is_healthy,
            "is_ready": self.is_ready,
            "timestamp": datetime.fromtimestamp(self.timestamp).isoformat(),
            "components": [c.to_dict() for c in self.components],
        }


class HealthCheck:
    """
    Health check manager for system components.
    
    Usage:
        health = HealthCheck()
        
        # Register component checks
        health.register("redis", check_redis_health)
        health.register("exchange", check_exchange_health)
        
        # Run checks
        result = await health.check_all()
    """
    
    def __init__(self):
        self._checks: Dict[str, Callable] = {}
        self._last_results: Dict[str, ComponentHealth] = {}
        self._cache_ttl = 5.0  # Cache results for 5 seconds
    
    def register(
        self,
        name: str,
        check_fn: Callable[[], ComponentHealth],
        critical: bool = True
    ) -> None:
        """
        Register a health check.
        
        Args:
            name: Component name
            check_fn: Function that returns ComponentHealth (sync or async)
            critical: If True, failure makes system unhealthy; if False, only degraded
        """
        self._checks[name] = {"fn": check_fn, "critical": critical}
        logger.debug(f"Registered health check: {name} (critical={critical})")
    
    def unregister(self, name: str) -> None:
        """Remove a health check."""
        self._checks.pop(name, None)
        self._last_results.pop(name, None)
    
    async def _run_check(self, name: str, check_info: dict) -> ComponentHealth:
        """Run a single health check."""
        check_fn = check_info["fn"]
        start = time.perf_counter()
        
        try:
            # Handle both sync and async check functions
            if asyncio.iscoroutinefunction(check_fn):
                result = await check_fn()
            else:
                result = check_fn()
            
            result.latency_ms = (time.perf_counter() - start) * 1000
            result.last_check = time.time()
            return result
            
        except Exception as e:
            latency = (time.perf_counter() - start) * 1000
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNHEALTHY,
                message=f"Check failed: {str(e)}",
                latency_ms=latency,
            )
    
    async def check(self, name: str) -> ComponentHealth:
        """Run a specific health check."""
        if name not in self._checks:
            return ComponentHealth(
                name=name,
                status=HealthStatus.UNKNOWN,
                message=f"Unknown component: {name}"
            )
        
        # Check cache
        cached = self._last_results.get(name)
        if cached and (time.time() - cached.last_check) < self._cache_ttl:
            return cached
        
        result = await self._run_check(name, self._checks[name])
        self._last_results[name] = result
        return result
    
    async def check_all(self) -> HealthCheckResult:
        """Run all health checks."""
        components = []
        
        # Run all checks concurrently
        tasks = [
            self._run_check(name, info)
            for name, info in self._checks.items()
        ]
        
        if tasks:
            results = await asyncio.gather(*tasks, return_exceptions=True)
            
            for result in results:
                if isinstance(result, Exception):
                    components.append(ComponentHealth(
                        name="unknown",
                        status=HealthStatus.UNHEALTHY,
                        message=str(result)
                    ))
                else:
                    components.append(result)
                    self._last_results[result.name] = result
        
        # Determine overall status
        overall = self._calculate_overall_status(components)
        
        return HealthCheckResult(
            status=overall,
            components=components,
        )
    
    def _calculate_overall_status(self, components: List[ComponentHealth]) -> HealthStatus:
        """Calculate overall health status from components."""
        if not components:
            return HealthStatus.HEALTHY
        
        has_unhealthy_critical = False
        has_degraded = False
        
        for comp in components:
            check_info = self._checks.get(comp.name, {"critical": True})
            
            if comp.status == HealthStatus.UNHEALTHY:
                if check_info.get("critical", True):
                    has_unhealthy_critical = True
                else:
                    has_degraded = True
            elif comp.status == HealthStatus.DEGRADED:
                has_degraded = True
        
        if has_unhealthy_critical:
            return HealthStatus.UNHEALTHY
        if has_degraded:
            return HealthStatus.DEGRADED
        return HealthStatus.HEALTHY
    
    def liveness(self) -> bool:
        """
        Liveness probe - is the process alive and not deadlocked?
        This is a quick, synchronous check.
        """
        return True  # If we can execute this, we're alive
    
    async def readiness(self) -> bool:
        """
        Readiness probe - is the system ready to accept traffic?
        Checks all components.
        """
        result = await self.check_all()
        return result.is_ready


# =============================================================================
# Pre-built health checks for common components
# =============================================================================

def check_redis_health(
    host: str = "localhost",
    port: int = 6379,
    password: Optional[str] = None,
    timeout: float = 2.0
) -> Callable[[], ComponentHealth]:
    """Create a Redis health check function."""
    def check() -> ComponentHealth:
        try:
            import redis
            r = redis.Redis(
                host=host,
                port=port,
                password=password,
                socket_timeout=timeout,
                socket_connect_timeout=timeout,
            )
            start = time.perf_counter()
            r.ping()
            latency = (time.perf_counter() - start) * 1000
            
            info = r.info("server")
            return ComponentHealth(
                name="redis",
                status=HealthStatus.HEALTHY,
                message=f"Redis {info.get('redis_version', 'unknown')}",
                latency_ms=latency,
                details={"version": info.get("redis_version")},
            )
        except ImportError:
            return ComponentHealth(
                name="redis",
                status=HealthStatus.UNKNOWN,
                message="Redis client not installed",
            )
        except Exception as e:
            return ComponentHealth(
                name="redis",
                status=HealthStatus.UNHEALTHY,
                message=str(e),
            )
    
    return check


def check_exchange_health(exchange_client: Any) -> Callable[[], ComponentHealth]:
    """Create an exchange health check function."""
    async def check() -> ComponentHealth:
        try:
            start = time.perf_counter()
            # Try to fetch server time as a simple health check
            if hasattr(exchange_client, "fetch_time"):
                await exchange_client.fetch_time()
            elif hasattr(exchange_client, "fetch_status"):
                await exchange_client.fetch_status()
            latency = (time.perf_counter() - start) * 1000
            
            return ComponentHealth(
                name="exchange",
                status=HealthStatus.HEALTHY,
                message="Exchange API responding",
                latency_ms=latency,
            )
        except Exception as e:
            return ComponentHealth(
                name="exchange",
                status=HealthStatus.UNHEALTHY,
                message=str(e),
            )
    
    return check


# Global health check instance
_health_check: Optional[HealthCheck] = None


def get_health_check() -> HealthCheck:
    """Get or create global health check instance."""
    global _health_check
    if _health_check is None:
        _health_check = HealthCheck()
    return _health_check
