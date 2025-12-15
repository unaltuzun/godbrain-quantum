# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN Prometheus Metrics Exporter
Exports trading metrics for Prometheus scraping.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import time
import threading
from typing import Dict, Any
from http.server import HTTPServer, BaseHTTPRequestHandler
from dataclasses import dataclass, field
from collections import defaultdict


@dataclass
class TradingMetrics:
    """Trading metrics for Prometheus export."""
    
    # Counters
    trades_total: int = 0
    trades_buy: int = 0
    trades_sell: int = 0
    signals_generated: int = 0
    errors_total: int = 0
    
    # Gauges
    equity_usd: float = 0.0
    open_positions: int = 0
    unrealized_pnl: float = 0.0
    realized_pnl: float = 0.0
    dna_fitness: float = 0.0
    dna_generation: int = 0
    
    # Histograms (simplified as recent values)
    trade_latency_ms: float = 0.0
    signal_processing_ms: float = 0.0
    
    # Per-symbol metrics
    symbol_equity: Dict[str, float] = field(default_factory=dict)
    symbol_trades: Dict[str, int] = field(default_factory=dict)
    
    def to_prometheus_format(self) -> str:
        """Convert metrics to Prometheus text format."""
        lines = [
            "# HELP godbrain_trades_total Total number of trades executed",
            "# TYPE godbrain_trades_total counter",
            f"godbrain_trades_total {self.trades_total}",
            "",
            "# HELP godbrain_trades_buy Total buy trades",
            "# TYPE godbrain_trades_buy counter",
            f"godbrain_trades_buy {self.trades_buy}",
            "",
            "# HELP godbrain_trades_sell Total sell trades",
            "# TYPE godbrain_trades_sell counter",
            f"godbrain_trades_sell {self.trades_sell}",
            "",
            "# HELP godbrain_signals_total Total signals generated",
            "# TYPE godbrain_signals_total counter",
            f"godbrain_signals_total {self.signals_generated}",
            "",
            "# HELP godbrain_errors_total Total errors",
            "# TYPE godbrain_errors_total counter",
            f"godbrain_errors_total {self.errors_total}",
            "",
            "# HELP godbrain_equity_usd Current equity in USD",
            "# TYPE godbrain_equity_usd gauge",
            f"godbrain_equity_usd {self.equity_usd}",
            "",
            "# HELP godbrain_open_positions Number of open positions",
            "# TYPE godbrain_open_positions gauge",
            f"godbrain_open_positions {self.open_positions}",
            "",
            "# HELP godbrain_unrealized_pnl Unrealized PnL in USD",
            "# TYPE godbrain_unrealized_pnl gauge",
            f"godbrain_unrealized_pnl {self.unrealized_pnl}",
            "",
            "# HELP godbrain_realized_pnl Realized PnL in USD",
            "# TYPE godbrain_realized_pnl gauge",
            f"godbrain_realized_pnl {self.realized_pnl}",
            "",
            "# HELP godbrain_dna_fitness Current DNA fitness score",
            "# TYPE godbrain_dna_fitness gauge",
            f"godbrain_dna_fitness {self.dna_fitness}",
            "",
            "# HELP godbrain_dna_generation Current DNA generation",
            "# TYPE godbrain_dna_generation gauge",
            f"godbrain_dna_generation {self.dna_generation}",
            "",
            "# HELP godbrain_trade_latency_ms Trade execution latency in ms",
            "# TYPE godbrain_trade_latency_ms gauge",
            f"godbrain_trade_latency_ms {self.trade_latency_ms}",
            "",
            "# HELP godbrain_signal_processing_ms Signal processing time in ms",
            "# TYPE godbrain_signal_processing_ms gauge",
            f"godbrain_signal_processing_ms {self.signal_processing_ms}",
            "",
        ]
        
        # Per-symbol metrics
        if self.symbol_equity:
            lines.append("# HELP godbrain_symbol_equity Equity per symbol")
            lines.append("# TYPE godbrain_symbol_equity gauge")
            for symbol, equity in self.symbol_equity.items():
                safe_symbol = symbol.replace("/", "_").replace(":", "_")
                lines.append(f'godbrain_symbol_equity{{symbol="{safe_symbol}"}} {equity}')
            lines.append("")
        
        if self.symbol_trades:
            lines.append("# HELP godbrain_symbol_trades Trades per symbol")
            lines.append("# TYPE godbrain_symbol_trades counter")
            for symbol, count in self.symbol_trades.items():
                safe_symbol = symbol.replace("/", "_").replace(":", "_")
                lines.append(f'godbrain_symbol_trades{{symbol="{safe_symbol}"}} {count}')
            lines.append("")
        
        # System info
        lines.extend([
            "# HELP godbrain_info System information",
            "# TYPE godbrain_info gauge",
            'godbrain_info{version="4.6",component="voltran"} 1',
            "",
            "# HELP godbrain_up Service health",
            "# TYPE godbrain_up gauge",
            "godbrain_up 1",
        ])
        
        return "\n".join(lines)


# Global metrics instance
_metrics = TradingMetrics()
_lock = threading.Lock()


def get_metrics() -> TradingMetrics:
    """Get global metrics instance."""
    return _metrics


def update_metric(name: str, value: Any) -> None:
    """Thread-safe metric update."""
    with _lock:
        if hasattr(_metrics, name):
            setattr(_metrics, name, value)


def increment_counter(name: str, amount: int = 1) -> None:
    """Thread-safe counter increment."""
    with _lock:
        if hasattr(_metrics, name):
            current = getattr(_metrics, name)
            setattr(_metrics, name, current + amount)


def record_trade(action: str, symbol: str, latency_ms: float = 0) -> None:
    """Record a trade execution."""
    with _lock:
        _metrics.trades_total += 1
        if action.upper() == "BUY":
            _metrics.trades_buy += 1
        else:
            _metrics.trades_sell += 1
        
        _metrics.symbol_trades[symbol] = _metrics.symbol_trades.get(symbol, 0) + 1
        _metrics.trade_latency_ms = latency_ms


class MetricsHandler(BaseHTTPRequestHandler):
    """HTTP handler for Prometheus metrics endpoint."""
    
    def do_GET(self):
        if self.path == "/metrics":
            with _lock:
                content = _metrics.to_prometheus_format()
            
            self.send_response(200)
            self.send_header("Content-Type", "text/plain; version=0.0.4")
            self.end_headers()
            self.wfile.write(content.encode("utf-8"))
        elif self.path == "/health":
            self.send_response(200)
            self.send_header("Content-Type", "application/json")
            self.end_headers()
            self.wfile.write(b'{"status":"healthy"}')
        else:
            self.send_response(404)
            self.end_headers()
    
    def log_message(self, format, *args):
        pass  # Suppress logging


def start_metrics_server(port: int = 8080) -> threading.Thread:
    """Start metrics HTTP server in background thread."""
    def run_server():
        server = HTTPServer(("0.0.0.0", port), MetricsHandler)
        print(f"📊 Prometheus metrics server running on :{port}/metrics")
        server.serve_forever()
    
    thread = threading.Thread(target=run_server, daemon=True)
    thread.start()
    return thread


if __name__ == "__main__":
    # Demo
    print("Starting Prometheus metrics exporter...")
    
    # Simulate some metrics
    update_metric("equity_usd", 10500.0)
    update_metric("dna_fitness", 0.85)
    update_metric("dna_generation", 42)
    record_trade("BUY", "DOGE/USDT:USDT", 150)
    record_trade("SELL", "XRP/USDT:USDT", 120)
    
    # Start server
    start_metrics_server(8080)
    
    print("Visit http://localhost:8080/metrics to see metrics")
    
    # Keep running
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("Shutting down...")
