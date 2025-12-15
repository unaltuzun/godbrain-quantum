# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN Metrics Collection
Prometheus-compatible metrics for observability.
═══════════════════════════════════════════════════════════════════════════════
"""

import time
import threading
from dataclasses import dataclass, field
from typing import Any, Callable, Dict, List, Optional
from functools import wraps
from contextlib import contextmanager

from .logging_config import get_logger

logger = get_logger(__name__)


@dataclass
class MetricValue:
    """Single metric value with labels."""
    value: float
    labels: Dict[str, str] = field(default_factory=dict)
    timestamp: float = field(default_factory=time.time)


class Counter:
    """
    Counter metric - monotonically increasing value.
    
    Usage:
        errors = Counter("errors_total", "Total errors", ["type"])
        errors.inc(labels={"type": "exchange"})
    """
    
    def __init__(self, name: str, description: str, label_names: List[str] = None):
        self.name = name
        self.description = description
        self.label_names = label_names or []
        self._values: Dict[tuple, float] = {}
        self._lock = threading.Lock()
    
    def _label_key(self, labels: Dict[str, str]) -> tuple:
        """Create hashable key from labels."""
        return tuple(sorted(labels.items()))
    
    def inc(self, value: float = 1.0, labels: Dict[str, str] = None) -> None:
        """Increment counter."""
        labels = labels or {}
        key = self._label_key(labels)
        with self._lock:
            self._values[key] = self._values.get(key, 0) + value
    
    def get(self, labels: Dict[str, str] = None) -> float:
        """Get current counter value."""
        labels = labels or {}
        key = self._label_key(labels)
        with self._lock:
            return self._values.get(key, 0)
    
    def collect(self) -> List[MetricValue]:
        """Collect all values for export."""
        values = []
        with self._lock:
            for key, value in self._values.items():
                labels = dict(key) if key else {}
                values.append(MetricValue(value=value, labels=labels))
        return values


class Gauge:
    """
    Gauge metric - value that can go up and down.
    
    Usage:
        equity = Gauge("equity_usd", "Current equity in USD")
        equity.set(1500.0)
    """
    
    def __init__(self, name: str, description: str, label_names: List[str] = None):
        self.name = name
        self.description = description
        self.label_names = label_names or []
        self._values: Dict[tuple, float] = {}
        self._lock = threading.Lock()
    
    def _label_key(self, labels: Dict[str, str]) -> tuple:
        return tuple(sorted(labels.items())) if labels else ()
    
    def set(self, value: float, labels: Dict[str, str] = None) -> None:
        """Set gauge value."""
        key = self._label_key(labels)
        with self._lock:
            self._values[key] = value
    
    def inc(self, value: float = 1.0, labels: Dict[str, str] = None) -> None:
        """Increment gauge."""
        key = self._label_key(labels)
        with self._lock:
            self._values[key] = self._values.get(key, 0) + value
    
    def dec(self, value: float = 1.0, labels: Dict[str, str] = None) -> None:
        """Decrement gauge."""
        self.inc(-value, labels)
    
    def get(self, labels: Dict[str, str] = None) -> float:
        """Get current gauge value."""
        key = self._label_key(labels)
        with self._lock:
            return self._values.get(key, 0)
    
    def collect(self) -> List[MetricValue]:
        """Collect all values for export."""
        values = []
        with self._lock:
            for key, value in self._values.items():
                labels = dict(key) if key else {}
                values.append(MetricValue(value=value, labels=labels))
        return values


class Histogram:
    """
    Histogram metric - distribution of values.
    
    Usage:
        latency = Histogram("api_latency_seconds", "API latency")
        with latency.time():
            call_api()
    """
    
    DEFAULT_BUCKETS = (0.005, 0.01, 0.025, 0.05, 0.1, 0.25, 0.5, 1, 2.5, 5, 10, float("inf"))
    
    def __init__(
        self,
        name: str,
        description: str,
        label_names: List[str] = None,
        buckets: tuple = None
    ):
        self.name = name
        self.description = description
        self.label_names = label_names or []
        self.buckets = buckets or self.DEFAULT_BUCKETS
        self._counts: Dict[tuple, Dict[float, int]] = {}
        self._sums: Dict[tuple, float] = {}
        self._totals: Dict[tuple, int] = {}
        self._lock = threading.Lock()
    
    def _label_key(self, labels: Dict[str, str]) -> tuple:
        return tuple(sorted(labels.items())) if labels else ()
    
    def _init_buckets(self, key: tuple) -> None:
        """Initialize bucket counters for a label set."""
        if key not in self._counts:
            self._counts[key] = {b: 0 for b in self.buckets}
            self._sums[key] = 0
            self._totals[key] = 0
    
    def observe(self, value: float, labels: Dict[str, str] = None) -> None:
        """Observe a value."""
        key = self._label_key(labels)
        with self._lock:
            self._init_buckets(key)
            self._sums[key] += value
            self._totals[key] += 1
            for bucket in self.buckets:
                if value <= bucket:
                    self._counts[key][bucket] += 1
    
    @contextmanager
    def time(self, labels: Dict[str, str] = None):
        """Context manager to measure execution time."""
        start = time.perf_counter()
        try:
            yield
        finally:
            elapsed = time.perf_counter() - start
            self.observe(elapsed, labels)
    
    def time_decorator(self, labels: Dict[str, str] = None):
        """Decorator to measure function execution time."""
        def decorator(func: Callable) -> Callable:
            @wraps(func)
            def wrapper(*args, **kwargs):
                with self.time(labels):
                    return func(*args, **kwargs)
            return wrapper
        return decorator
    
    def collect(self) -> Dict[str, Any]:
        """Collect histogram data for export."""
        result = {}
        with self._lock:
            for key, buckets in self._counts.items():
                labels = dict(key) if key else {}
                result[str(labels)] = {
                    "buckets": dict(buckets),
                    "sum": self._sums.get(key, 0),
                    "count": self._totals.get(key, 0),
                }
        return result


class MetricsCollector:
    """
    Central metrics registry and collector.
    
    Usage:
        metrics = MetricsCollector()
        metrics.trades_total.inc(labels={"symbol": "BTC/USDT", "side": "BUY"})
        metrics.equity_usd.set(1500.0)
    """
    
    def __init__(self):
        # Counters
        self.trades_total = Counter(
            "godbrain_trades_total",
            "Total number of trades executed",
            ["symbol", "side"]
        )
        self.errors_total = Counter(
            "godbrain_errors_total",
            "Total number of errors",
            ["type", "component"]
        )
        self.signals_total = Counter(
            "godbrain_signals_total",
            "Total signals generated",
            ["symbol", "action"]
        )
        self.signals_filtered = Counter(
            "godbrain_signals_filtered_total",
            "Total signals filtered/blocked",
            ["reason"]
        )
        self.circuit_breaker_trips = Counter(
            "godbrain_circuit_breaker_trips_total",
            "Circuit breaker trip count",
            ["circuit"]
        )
        
        # Gauges
        self.equity_usd = Gauge(
            "godbrain_equity_usd",
            "Current equity in USD"
        )
        self.open_positions = Gauge(
            "godbrain_open_positions",
            "Number of open positions",
            ["symbol"]
        )
        self.dna_multiplier = Gauge(
            "godbrain_dna_multiplier",
            "Current DNA multiplier"
        )
        self.voltran_factor = Gauge(
            "godbrain_voltran_factor",
            "Current VOLTRAN factor"
        )
        self.quantum_score = Gauge(
            "godbrain_quantum_score",
            "Current quantum resonance score",
            ["symbol"]
        )
        self.regime = Gauge(
            "godbrain_regime",
            "Current market regime (encoded)",
            ["symbol"]
        )
        
        # Histograms
        self.decision_latency = Histogram(
            "godbrain_decision_latency_seconds",
            "Decision engine latency in seconds",
            ["symbol"]
        )
        self.api_latency = Histogram(
            "godbrain_api_latency_seconds",
            "Exchange API latency in seconds",
            ["endpoint"]
        )
        self.loop_duration = Histogram(
            "godbrain_loop_duration_seconds",
            "Main loop iteration duration"
        )
    
    def export_prometheus(self) -> str:
        """Export metrics in Prometheus text format."""
        lines = []
        
        # Counters
        for counter in [
            self.trades_total, self.errors_total, self.signals_total,
            self.signals_filtered, self.circuit_breaker_trips
        ]:
            lines.append(f"# HELP {counter.name} {counter.description}")
            lines.append(f"# TYPE {counter.name} counter")
            for mv in counter.collect():
                labels_str = ",".join(f'{k}="{v}"' for k, v in mv.labels.items())
                if labels_str:
                    lines.append(f"{counter.name}{{{labels_str}}} {mv.value}")
                else:
                    lines.append(f"{counter.name} {mv.value}")
        
        # Gauges
        for gauge in [
            self.equity_usd, self.open_positions, self.dna_multiplier,
            self.voltran_factor, self.quantum_score, self.regime
        ]:
            lines.append(f"# HELP {gauge.name} {gauge.description}")
            lines.append(f"# TYPE {gauge.name} gauge")
            for mv in gauge.collect():
                labels_str = ",".join(f'{k}="{v}"' for k, v in mv.labels.items())
                if labels_str:
                    lines.append(f"{gauge.name}{{{labels_str}}} {mv.value}")
                else:
                    lines.append(f"{gauge.name} {mv.value}")
        
        return "\n".join(lines)
    
    def to_dict(self) -> Dict[str, Any]:
        """Export all metrics as dictionary."""
        return {
            "counters": {
                "trades_total": {str(k): v for mv in self.trades_total.collect() for k, v in [(mv.labels, mv.value)]},
                "errors_total": {str(k): v for mv in self.errors_total.collect() for k, v in [(mv.labels, mv.value)]},
                "signals_total": {str(k): v for mv in self.signals_total.collect() for k, v in [(mv.labels, mv.value)]},
            },
            "gauges": {
                "equity_usd": self.equity_usd.get(),
                "dna_multiplier": self.dna_multiplier.get(),
                "voltran_factor": self.voltran_factor.get(),
            },
            "histograms": {
                "decision_latency": self.decision_latency.collect(),
                "api_latency": self.api_latency.collect(),
            },
        }


# Global metrics instance
metrics = MetricsCollector()
