#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN ENTERPRISE COMMAND CENTER
Unified operations dashboard for C-level visibility.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import json
import time
import asyncio
from pathlib import Path
from datetime import datetime
from typing import Dict, Any, Optional, List

from flask import Flask, render_template_string, jsonify, request
import redis

# Imports for our modules
try:
    from infrastructure.chaos_monkey import get_chaos_monkey, ChaosScenarios
    from infrastructure.prometheus_exporter import get_metrics
    from lab.visualization.dna_evolution_3d import DNAEvolutionVisualizer, EvolutionHistory
    HAS_MODULES = True
except ImportError:
    HAS_MODULES = False


ROOT = Path(__file__).parent
app = Flask(__name__)


# =============================================================================
# REDIS CONNECTION
# =============================================================================

def get_redis() -> Optional[redis.Redis]:
    """Get Redis connection."""
    try:
        r = redis.Redis(
            host=os.getenv("REDIS_HOST", "localhost"),
            port=int(os.getenv("REDIS_PORT", 6379)),
            password=os.getenv("REDIS_PASS", ""),
            decode_responses=True
        )
        r.ping()
        return r
    except:
        return None


# =============================================================================
# API ENDPOINTS
# =============================================================================

@app.route("/api/system-status")
def api_system_status():
    """Get overall system status."""
    r = get_redis()
    
    status = {
        "timestamp": datetime.now().isoformat(),
        "redis": r is not None,
        "components": {
            "voltran": True,
            "genetics": True,
            "seraph": True,
            "market_feed": True,
            "prometheus": True,
            "grafana": True,
        }
    }
    
    # Try to get trading state from Redis
    if r:
        try:
            equity = r.get("account:equity")
            status["equity"] = float(equity) if equity else 0
            
            positions = r.get("account:positions")
            status["open_positions"] = int(positions) if positions else 0
            
            dna = r.get("genetics:current_dna")
            if dna:
                status["current_dna"] = json.loads(dna)
        except:
            pass
    
    return jsonify(status)


@app.route("/api/chaos-status")
def api_chaos_status():
    """Get Chaos Monkey status."""
    if not HAS_MODULES:
        return jsonify({"enabled": False, "error": "Modules not loaded"})
    
    chaos = get_chaos_monkey()
    return jsonify(chaos.get_stats())


@app.route("/api/metrics")
def api_metrics():
    """Get Prometheus metrics."""
    if not HAS_MODULES:
        return jsonify({})
    
    metrics = get_metrics()
    return jsonify({
        "trades_total": metrics.trades_total,
        "equity_usd": metrics.equity_usd,
        "dna_fitness": metrics.dna_fitness,
        "dna_generation": metrics.dna_generation,
        "open_positions": metrics.open_positions,
    })


@app.route("/api/dna-history")
def api_dna_history():
    """Get DNA evolution history."""
    history = EvolutionHistory.from_dna_tracker()
    
    if not history.snapshots:
        # Generate sample data for demo
        from lab.visualization.dna_evolution_3d import generate_sample_history
        history = generate_sample_history(30)
    
    return jsonify({
        "generations": history.generations,
        "fitness": history.fitness_values,
        "snapshots": [
            {
                "gen": s.generation,
                "fitness": s.fitness,
                "dna": s.dna[:5] if s.dna else []
            }
            for s in history.snapshots[-50:]
        ]
    })


@app.route("/api/chaos/enable/<scenario>", methods=["POST"])
def api_enable_chaos(scenario: str):
    """Enable a chaos scenario."""
    if not HAS_MODULES:
        return jsonify({"error": "Modules not loaded"}), 500
    
    chaos = get_chaos_monkey()
    chaos.enable()
    
    scenarios = {
        "latency": lambda: ChaosScenarios.exchange_latency(chaos, "medium"),
        "rate_limit": lambda: ChaosScenarios.rate_limit_storm(chaos),
        "network": lambda: ChaosScenarios.network_instability(chaos),
        "redis": lambda: ChaosScenarios.redis_failure(chaos),
        "crash": lambda: ChaosScenarios.market_crash(chaos),
        "full": lambda: ChaosScenarios.full_chaos(chaos),
    }
    
    if scenario in scenarios:
        scenarios[scenario]()
        return jsonify({"status": "enabled", "scenario": scenario})
    
    return jsonify({"error": f"Unknown scenario: {scenario}"}), 400


@app.route("/api/chaos/disable", methods=["POST"])
def api_disable_chaos():
    """Disable all chaos."""
    if not HAS_MODULES:
        return jsonify({"error": "Modules not loaded"}), 500
    
    chaos = get_chaos_monkey()
    chaos.disable()
    chaos.clear_all_faults()
    return jsonify({"status": "disabled"})


# =============================================================================
# MAIN DASHBOARD HTML
# =============================================================================

COMMAND_CENTER_HTML = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🧠 GODBRAIN Command Center</title>
    <script src="https://cdn.plot.ly/plotly-2.26.0.min.js"></script>
    <style>
        * { margin: 0; padding: 0; box-sizing: border-box; }
        
        body {
            font-family: 'Segoe UI', system-ui, sans-serif;
            background: linear-gradient(135deg, #0a0a0f 0%, #1a1a2e 100%);
            color: #e0e0e0;
            min-height: 100vh;
        }
        
        /* Header */
        .header {
            background: rgba(0, 255, 136, 0.1);
            border-bottom: 1px solid #00ff88;
            padding: 15px 30px;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h1 {
            font-size: 24px;
            color: #00ff88;
            text-shadow: 0 0 20px rgba(0, 255, 136, 0.5);
        }
        
        .header-status {
            display: flex;
            gap: 20px;
            align-items: center;
        }
        
        .status-badge {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
            font-weight: bold;
        }
        
        .status-online { background: #00ff88; color: #000; animation: pulse 2s infinite; }
        .status-warning { background: #ffaa00; color: #000; }
        .status-danger { background: #ff4444; color: #fff; }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.7; }
        }
        
        /* Main Grid */
        .dashboard {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            grid-template-rows: auto auto;
            gap: 20px;
            padding: 20px;
        }
        
        /* Panels */
        .panel {
            background: rgba(26, 26, 46, 0.8);
            border: 1px solid #333;
            border-radius: 12px;
            overflow: hidden;
            backdrop-filter: blur(10px);
        }
        
        .panel-header {
            background: rgba(0, 0, 0, 0.3);
            padding: 15px 20px;
            border-bottom: 1px solid #333;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .panel-header h3 {
            font-size: 14px;
            color: #00ff88;
            text-transform: uppercase;
            letter-spacing: 1px;
        }
        
        .panel-body {
            padding: 20px;
        }
        
        .panel-full { grid-column: span 2; }
        .panel-tall { grid-row: span 2; }
        
        /* Metrics Grid */
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 15px;
        }
        
        .metric-card {
            background: rgba(0, 0, 0, 0.3);
            padding: 15px;
            border-radius: 8px;
            text-align: center;
        }
        
        .metric-value {
            font-size: 28px;
            font-weight: bold;
            color: #00ff88;
        }
        
        .metric-label {
            font-size: 11px;
            color: #888;
            text-transform: uppercase;
            margin-top: 5px;
        }
        
        .metric-positive { color: #00ff88; }
        .metric-negative { color: #ff4444; }
        
        /* Chaos Control */
        .chaos-controls {
            display: flex;
            gap: 10px;
            flex-wrap: wrap;
        }
        
        .btn {
            padding: 10px 20px;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            font-size: 12px;
            font-weight: bold;
            transition: all 0.2s;
        }
        
        .btn-primary {
            background: #00ff88;
            color: #000;
        }
        
        .btn-danger {
            background: #ff4444;
            color: #fff;
        }
        
        .btn-warning {
            background: #ffaa00;
            color: #000;
        }
        
        .btn:hover {
            transform: translateY(-2px);
            box-shadow: 0 5px 20px rgba(0, 255, 136, 0.3);
        }
        
        .btn:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        
        /* Status List */
        .status-list {
            list-style: none;
        }
        
        .status-list li {
            padding: 10px 0;
            border-bottom: 1px solid #222;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .status-dot {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 10px;
        }
        
        .dot-green { background: #00ff88; box-shadow: 0 0 10px #00ff88; }
        .dot-red { background: #ff4444; box-shadow: 0 0 10px #ff4444; }
        .dot-yellow { background: #ffaa00; }
        
        /* Chart Container */
        .chart-container {
            height: 300px;
            background: rgba(0, 0, 0, 0.2);
            border-radius: 8px;
        }
        
        /* Iframe */
        .grafana-frame {
            width: 100%;
            height: 300px;
            border: none;
            border-radius: 8px;
        }
        
        /* Log Console */
        .console {
            background: #000;
            padding: 15px;
            border-radius: 8px;
            font-family: 'Courier New', monospace;
            font-size: 11px;
            max-height: 200px;
            overflow-y: auto;
        }
        
        .console-line {
            padding: 3px 0;
            border-bottom: 1px solid #111;
        }
        
        .console-time { color: #666; }
        .console-info { color: #00ff88; }
        .console-warn { color: #ffaa00; }
        .console-error { color: #ff4444; }
    </style>
</head>
<body>
    <!-- Header -->
    <div class="header">
        <h1>🧠 GODBRAIN COMMAND CENTER</h1>
        <div class="header-status">
            <span id="time" style="color: #888;">--:--:--</span>
            <span id="systemStatus" class="status-badge status-online">● LIVE</span>
        </div>
    </div>
    
    <!-- Dashboard -->
    <div class="dashboard">
        <!-- Key Metrics -->
        <div class="panel panel-full">
            <div class="panel-header">
                <h3>📊 Key Metrics</h3>
                <span id="lastUpdate" style="color: #666; font-size: 11px;">Updated: --</span>
            </div>
            <div class="panel-body">
                <div class="metrics-grid">
                    <div class="metric-card">
                        <div id="metricEquity" class="metric-value">$0.00</div>
                        <div class="metric-label">Equity</div>
                    </div>
                    <div class="metric-card">
                        <div id="metricTrades" class="metric-value">0</div>
                        <div class="metric-label">Total Trades</div>
                    </div>
                    <div class="metric-card">
                        <div id="metricPositions" class="metric-value">0</div>
                        <div class="metric-label">Open Positions</div>
                    </div>
                    <div class="metric-card">
                        <div id="metricFitness" class="metric-value">0.00</div>
                        <div class="metric-label">DNA Fitness</div>
                    </div>
                    <div class="metric-card">
                        <div id="metricGeneration" class="metric-value">0</div>
                        <div class="metric-label">DNA Generation</div>
                    </div>
                    <div class="metric-card">
                        <div id="metricChaos" class="metric-value">OFF</div>
                        <div class="metric-label">Chaos Monkey</div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- System Status -->
        <div class="panel">
            <div class="panel-header">
                <h3>⚡ System Status</h3>
            </div>
            <div class="panel-body">
                <ul id="statusList" class="status-list">
                    <li><span class="status-dot dot-green"></span>Voltran <span>Running</span></li>
                    <li><span class="status-dot dot-green"></span>Genetics <span>Running</span></li>
                    <li><span class="status-dot dot-green"></span>Seraph <span>Running</span></li>
                    <li><span class="status-dot dot-green"></span>Redis <span>Connected</span></li>
                    <li><span class="status-dot dot-green"></span>Prometheus <span>Scraping</span></li>
                </ul>
            </div>
        </div>
        
        <!-- DNA Evolution Chart -->
        <div class="panel panel-full">
            <div class="panel-header">
                <h3>🧬 DNA Evolution</h3>
                <button class="btn btn-primary" onclick="refresh3D()">Refresh</button>
            </div>
            <div class="panel-body">
                <div id="dnaChart" class="chart-container"></div>
            </div>
        </div>
        
        <!-- Chaos Monkey Control -->
        <div class="panel">
            <div class="panel-header">
                <h3>🐒 Chaos Monkey</h3>
            </div>
            <div class="panel-body">
                <div class="chaos-controls">
                    <button class="btn btn-warning" onclick="enableChaos('latency')">⏱️ Latency</button>
                    <button class="btn btn-warning" onclick="enableChaos('rate_limit')">🚫 Rate Limit</button>
                    <button class="btn btn-warning" onclick="enableChaos('network')">📡 Network</button>
                    <button class="btn btn-danger" onclick="enableChaos('crash')">💥 Crash</button>
                    <button class="btn btn-primary" onclick="disableChaos()">✅ Disable All</button>
                </div>
                <div id="chaosLog" class="console" style="margin-top: 15px;">
                    <div class="console-line"><span class="console-info">Chaos Monkey ready</span></div>
                </div>
            </div>
        </div>
        
        <!-- Grafana Embed -->
        <div class="panel panel-full">
            <div class="panel-header">
                <h3>📈 Grafana Metrics</h3>
                <a href="http://34.45.186.133" target="_blank" class="btn btn-primary">Open Grafana</a>
            </div>
            <div class="panel-body">
                <iframe class="grafana-frame" src="http://34.45.186.133/d/godbrain-main?orgId=1&theme=dark&kiosk=tv"></iframe>
            </div>
        </div>
    </div>
    
    <script>
        // Update time
        function updateTime() {
            document.getElementById('time').textContent = new Date().toLocaleTimeString();
        }
        setInterval(updateTime, 1000);
        updateTime();
        
        // Fetch metrics
        async function fetchMetrics() {
            try {
                const resp = await fetch('/api/metrics');
                const data = await resp.json();
                
                document.getElementById('metricEquity').textContent = '$' + (data.equity_usd || 0).toFixed(2);
                document.getElementById('metricTrades').textContent = data.trades_total || 0;
                document.getElementById('metricPositions').textContent = data.open_positions || 0;
                document.getElementById('metricFitness').textContent = (data.dna_fitness || 0).toFixed(4);
                document.getElementById('metricGeneration').textContent = data.dna_generation || 0;
                document.getElementById('lastUpdate').textContent = 'Updated: ' + new Date().toLocaleTimeString();
            } catch (e) {
                console.error('Metrics error:', e);
            }
        }
        
        // Fetch chaos status
        async function fetchChaosStatus() {
            try {
                const resp = await fetch('/api/chaos-status');
                const data = await resp.json();
                
                const status = data.enabled ? 'ON' : 'OFF';
                document.getElementById('metricChaos').textContent = status;
                document.getElementById('metricChaos').className = 'metric-value ' + (data.enabled ? 'metric-negative' : 'metric-positive');
            } catch (e) {
                console.error('Chaos status error:', e);
            }
        }
        
        // DNA Evolution Chart
        async function loadDNAChart() {
            try {
                const resp = await fetch('/api/dna-history');
                const data = await resp.json();
                
                const trace = {
                    x: data.generations,
                    y: data.fitness,
                    type: 'scatter',
                    mode: 'lines+markers',
                    name: 'Fitness',
                    line: { color: '#00ff88', width: 2 },
                    marker: { size: 6, color: '#00ff88' }
                };
                
                const layout = {
                    paper_bgcolor: 'rgba(0,0,0,0)',
                    plot_bgcolor: 'rgba(0,0,0,0.3)',
                    font: { color: '#888' },
                    xaxis: { title: 'Generation', gridcolor: '#333' },
                    yaxis: { title: 'Fitness', gridcolor: '#333' },
                    margin: { t: 20, r: 20, b: 50, l: 50 }
                };
                
                Plotly.newPlot('dnaChart', [trace], layout, { responsive: true });
            } catch (e) {
                console.error('DNA chart error:', e);
            }
        }
        
        function refresh3D() {
            loadDNAChart();
        }
        
        // Chaos controls
        async function enableChaos(scenario) {
            try {
                const resp = await fetch('/api/chaos/enable/' + scenario, { method: 'POST' });
                const data = await resp.json();
                
                logChaos('Enabled: ' + scenario, 'warn');
                fetchChaosStatus();
            } catch (e) {
                logChaos('Error: ' + e.message, 'error');
            }
        }
        
        async function disableChaos() {
            try {
                await fetch('/api/chaos/disable', { method: 'POST' });
                logChaos('All chaos disabled', 'info');
                fetchChaosStatus();
            } catch (e) {
                logChaos('Error: ' + e.message, 'error');
            }
        }
        
        function logChaos(msg, level = 'info') {
            const log = document.getElementById('chaosLog');
            const time = new Date().toLocaleTimeString();
            log.innerHTML += `<div class="console-line"><span class="console-time">[${time}]</span> <span class="console-${level}">${msg}</span></div>`;
            log.scrollTop = log.scrollHeight;
        }
        
        // Initialize
        fetchMetrics();
        fetchChaosStatus();
        loadDNAChart();
        
        // Refresh every 10 seconds
        setInterval(fetchMetrics, 10000);
        setInterval(fetchChaosStatus, 5000);
    </script>
</body>
</html>
'''


@app.route("/")
def command_center():
    """Render main command center."""
    return render_template_string(COMMAND_CENTER_HTML)


@app.route("/health")
def health():
    """Health check endpoint."""
    return jsonify({"status": "healthy", "timestamp": datetime.now().isoformat()})


# =============================================================================
# MAIN
# =============================================================================

def main():
    """Run the command center server."""
    port = int(os.getenv("PORT", 8000))
    print(f"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    GODBRAIN ENTERPRISE COMMAND CENTER                         ║
╠═══════════════════════════════════════════════════════════════════════════════╣
║  URL: http://localhost:{port}                                                  ║
║  Grafana: http://34.45.186.133                                                ║
║  Status: READY                                                                ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    app.run(host="0.0.0.0", port=port, debug=False)


if __name__ == "__main__":
    main()
