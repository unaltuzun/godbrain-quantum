#!/usr/bin/env python3
# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   ██████╗  ██████╗ ██████╗ ██████╗ ██████╗  █████╗ ██╗███╗   ██╗             ║
║  ██╔════╝ ██╔═══██╗██╔══██╗██╔══██╗██╔══██╗██╔══██╗██║████╗  ██║             ║
║  ██║  ███╗██║   ██║██║  ██║██████╔╝██████╔╝███████║██║██╔██╗ ██║             ║
║  ██║   ██║██║   ██║██║  ██║██╔══██╗██╔══██╗██╔══██║██║██║╚██╗██║             ║
║  ╚██████╔╝╚██████╔╝██████╔╝██████╔╝██║  ██║██║  ██║██║██║ ╚████║             ║
║   ╚═════╝  ╚═════╝ ╚═════╝ ╚═════╝ ╚═╝  ╚═╝╚═╝  ╚═╝╚═╝╚═╝  ╚═══╝             ║
║                                                                               ║
║                    LIVE DASHBOARD v1.0                                        ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝

Tarayıcıda aç: http://localhost:5000

Features:
- Real-time log streaming
- PM2 service status
- Config viewer/editor
- Trade history
- System metrics
"""

import os
import sys
import json
import time
import subprocess
import threading
from pathlib import Path
from datetime import datetime
from collections import deque
from flask import Flask, render_template_string, jsonify, request

# =============================================================================
# PATHS
# =============================================================================

QUANTUM_ROOT = Path("/mnt/c/godbrain-quantum")
LOG_DIR = QUANTUM_ROOT / "logs"
AGG_LOG = Path("/root/.pm2/logs/godbrain-quantum-out.log")
AGG_ERR = Path("/root/.pm2/logs/godbrain-quantum-error.log")
APEX_LOG = Path("/root/.pm2/logs/godmoney-apex-out.log")

HUMAN_BIAS = QUANTUM_ROOT / "human_bias.json"
HUMAN_CONTROL = QUANTUM_ROOT / "human_control.json"
TICK_STREAM = LOG_DIR / "tick_stream.jsonl"

# =============================================================================
# LOG BUFFER
# =============================================================================

log_buffer = deque(maxlen=200)
error_buffer = deque(maxlen=50)
apex_buffer = deque(maxlen=100)

def tail_file(filepath, buffer, lines=50):
    """Read last N lines from file."""
    try:
        if filepath.exists():
            with open(filepath, 'r', encoding='utf-8', errors='ignore') as f:
                all_lines = f.readlines()
                return all_lines[-lines:]
    except:
        pass
    return []

def update_logs():
    """Background thread to update log buffers."""
    global log_buffer, error_buffer, apex_buffer
    
    while True:
        try:
            # Main logs
            lines = tail_file(AGG_LOG, log_buffer, 100)
            log_buffer.clear()
            for line in lines:
                log_buffer.append(line.strip())
            
            # Error logs
            lines = tail_file(AGG_ERR, error_buffer, 30)
            error_buffer.clear()
            for line in lines:
                error_buffer.append(line.strip())
            
            # Apex logs
            lines = tail_file(APEX_LOG, apex_buffer, 50)
            apex_buffer.clear()
            for line in lines:
                apex_buffer.append(line.strip())
                
        except Exception as e:
            pass
        
        time.sleep(2)

# Start background thread
log_thread = threading.Thread(target=update_logs, daemon=True)
log_thread.start()

# =============================================================================
# FLASK APP
# =============================================================================

app = Flask(__name__)

HTML_TEMPLATE = '''
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0">
    <title>🧠 GODBRAIN Dashboard</title>
    <style>
        * {
            margin: 0;
            padding: 0;
            box-sizing: border-box;
        }
        
        body {
            font-family: 'Courier New', monospace;
            background: #0a0a0f;
            color: #00ff88;
            min-height: 100vh;
        }
        
        .header {
            background: linear-gradient(135deg, #1a1a2e 0%, #16213e 100%);
            padding: 15px 20px;
            border-bottom: 2px solid #00ff88;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .header h1 {
            font-size: 24px;
            text-shadow: 0 0 10px #00ff88;
        }
        
        .header .status {
            display: flex;
            gap: 20px;
        }
        
        .status-item {
            padding: 5px 15px;
            border-radius: 20px;
            font-size: 12px;
        }
        
        .status-online {
            background: rgba(0, 255, 136, 0.2);
            border: 1px solid #00ff88;
        }
        
        .status-offline {
            background: rgba(255, 68, 68, 0.2);
            border: 1px solid #ff4444;
            color: #ff4444;
        }
        
        .container {
            display: grid;
            grid-template-columns: 1fr 1fr;
            grid-template-rows: auto auto auto;
            gap: 15px;
            padding: 15px;
            max-height: calc(100vh - 80px);
        }
        
        .panel {
            background: #12121a;
            border: 1px solid #333;
            border-radius: 8px;
            overflow: hidden;
        }
        
        .panel-header {
            background: #1a1a2e;
            padding: 10px 15px;
            border-bottom: 1px solid #333;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }
        
        .panel-header h3 {
            font-size: 14px;
            color: #00ff88;
        }
        
        .panel-content {
            padding: 10px;
            max-height: 250px;
            overflow-y: auto;
            font-size: 11px;
            line-height: 1.6;
        }
        
        .log-line {
            padding: 2px 5px;
            border-radius: 3px;
            margin: 2px 0;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
        }
        
        .log-execute {
            background: rgba(0, 255, 136, 0.1);
            color: #00ff88;
        }
        
        .log-blocked {
            background: rgba(255, 170, 0, 0.1);
            color: #ffaa00;
        }
        
        .log-error {
            background: rgba(255, 68, 68, 0.1);
            color: #ff4444;
        }
        
        .log-info {
            color: #888;
        }
        
        .config-grid {
            display: grid;
            grid-template-columns: 1fr 1fr;
            gap: 10px;
        }
        
        .config-item {
            background: #1a1a2e;
            padding: 10px;
            border-radius: 5px;
        }
        
        .config-label {
            font-size: 10px;
            color: #666;
            margin-bottom: 5px;
        }
        
        .config-value {
            font-size: 18px;
            font-weight: bold;
        }
        
        .config-aggressive { color: #ff4444; }
        .config-neutral { color: #ffaa00; }
        .config-chill { color: #00ff88; }
        
        .metrics-grid {
            display: grid;
            grid-template-columns: repeat(4, 1fr);
            gap: 10px;
        }
        
        .metric {
            text-align: center;
            padding: 15px 10px;
            background: #1a1a2e;
            border-radius: 5px;
        }
        
        .metric-value {
            font-size: 24px;
            font-weight: bold;
            margin-bottom: 5px;
        }
        
        .metric-label {
            font-size: 10px;
            color: #666;
        }
        
        .trade-row {
            display: grid;
            grid-template-columns: 80px 60px 80px 60px auto;
            gap: 10px;
            padding: 8px;
            border-bottom: 1px solid #222;
            font-size: 11px;
        }
        
        .trade-buy { color: #00ff88; }
        .trade-sell { color: #ff4444; }
        
        .btn {
            padding: 8px 16px;
            border: none;
            border-radius: 5px;
            cursor: pointer;
            font-family: inherit;
            font-size: 12px;
        }
        
        .btn-danger {
            background: #ff4444;
            color: white;
        }
        
        .btn-success {
            background: #00ff88;
            color: black;
        }
        
        .btn-warning {
            background: #ffaa00;
            color: black;
        }
        
        .full-width {
            grid-column: 1 / -1;
        }
        
        .services-grid {
            display: grid;
            grid-template-columns: repeat(3, 1fr);
            gap: 10px;
        }
        
        .service {
            padding: 15px;
            background: #1a1a2e;
            border-radius: 5px;
            text-align: center;
        }
        
        .service-status {
            width: 10px;
            height: 10px;
            border-radius: 50%;
            display: inline-block;
            margin-right: 8px;
        }
        
        .service-online { background: #00ff88; box-shadow: 0 0 10px #00ff88; }
        .service-offline { background: #ff4444; }
        
        @keyframes pulse {
            0%, 100% { opacity: 1; }
            50% { opacity: 0.5; }
        }
        
        .live-indicator {
            animation: pulse 2s infinite;
            color: #00ff88;
        }
        
        ::-webkit-scrollbar {
            width: 6px;
        }
        
        ::-webkit-scrollbar-track {
            background: #1a1a2e;
        }
        
        ::-webkit-scrollbar-thumb {
            background: #333;
            border-radius: 3px;
        }
    </style>
</head>
<body>
    <div class="header">
        <h1>🧠 GODBRAIN LIVE DASHBOARD</h1>
        <div class="status">
            <span class="status-item status-online live-indicator">● LIVE</span>
            <span id="time" class="status-item">--:--:--</span>
        </div>
    </div>
    
    <div class="container">
        <!-- Services Status -->
        <div class="panel full-width">
            <div class="panel-header">
                <h3>⚡ PM2 SERVICES</h3>
                <div>
                    <button class="btn btn-warning" onclick="restartAll()">Restart All</button>
                    <button class="btn btn-danger" onclick="killSwitch()">🛑 KILL SWITCH</button>
                </div>
            </div>
            <div class="panel-content">
                <div class="services-grid" id="services">
                    <div class="service">
                        <span class="service-status service-online"></span>
                        <strong>godbrain-quantum</strong>
                        <div style="color: #666; font-size: 10px; margin-top: 5px;">Main Aggregator</div>
                    </div>
                    <div class="service">
                        <span class="service-status service-online"></span>
                        <strong>godmoney-apex</strong>
                        <div style="color: #666; font-size: 10px; margin-top: 5px;">Executor</div>
                    </div>
                    <div class="service">
                        <span class="service-status service-online"></span>
                        <strong>godbrain-chronos</strong>
                        <div style="color: #666; font-size: 10px; margin-top: 5px;">TRNG/Coherence</div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Config Panel -->
        <div class="panel">
            <div class="panel-header">
                <h3>⚙️ CONFIGURATION</h3>
                <button class="btn btn-success" onclick="refreshConfig()">Refresh</button>
            </div>
            <div class="panel-content">
                <div class="config-grid" id="config">
                    <div class="config-item">
                        <div class="config-label">BIAS MODE</div>
                        <div class="config-value config-aggressive" id="bias-mode">AGGRESSIVE</div>
                    </div>
                    <div class="config-item">
                        <div class="config-label">RISK ADJUSTMENT</div>
                        <div class="config-value" id="risk-adj">2.0x</div>
                    </div>
                    <div class="config-item">
                        <div class="config-label">KILL SWITCH</div>
                        <div class="config-value" id="kill-switch" style="color: #00ff88;">OFF</div>
                    </div>
                    <div class="config-item">
                        <div class="config-label">MAX DAILY LOSS</div>
                        <div class="config-value" id="max-loss">$200</div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Metrics Panel -->
        <div class="panel">
            <div class="panel-header">
                <h3>📊 LIVE METRICS</h3>
            </div>
            <div class="panel-content">
                <div class="metrics-grid" id="metrics">
                    <div class="metric">
                        <div class="metric-value" id="equity">$23</div>
                        <div class="metric-label">EQUITY</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value" id="regime" style="color: #ff4444;">DOWN</div>
                        <div class="metric-label">REGIME</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value" id="fg">22</div>
                        <div class="metric-label">F&G INDEX</div>
                    </div>
                    <div class="metric">
                        <div class="metric-value" id="ls">2.05</div>
                        <div class="metric-label">L/S RATIO</div>
                    </div>
                </div>
            </div>
        </div>
        
        <!-- Main Logs -->
        <div class="panel">
            <div class="panel-header">
                <h3>📜 QUANTUM LOGS</h3>
                <span class="live-indicator">● LIVE</span>
            </div>
            <div class="panel-content" id="main-logs">
                <div class="log-line log-info">Loading...</div>
            </div>
        </div>
        
        <!-- Trade History -->
        <div class="panel">
            <div class="panel-header">
                <h3>💹 RECENT TRADES</h3>
            </div>
            <div class="panel-content" id="trades">
                <div class="trade-row" style="color: #666; font-weight: bold;">
                    <span>TIME</span>
                    <span>SIDE</span>
                    <span>SIZE</span>
                    <span>CONV</span>
                    <span>REGIME</span>
                </div>
            </div>
        </div>
        
        <!-- Error Logs -->
        <div class="panel full-width">
            <div class="panel-header">
                <h3>⚠️ ERROR LOG</h3>
            </div>
            <div class="panel-content" id="error-logs" style="max-height: 150px;">
                <div class="log-line log-info">No errors</div>
            </div>
        </div>
    </div>
    
    <script>
        function updateTime() {
            const now = new Date();
            document.getElementById('time').textContent = now.toLocaleTimeString();
        }
        setInterval(updateTime, 1000);
        updateTime();
        
        function formatLogLine(line) {
            if (line.includes('EXECUTE')) {
                return `<div class="log-line log-execute">${escapeHtml(line)}</div>`;
            } else if (line.includes('BLOCKED')) {
                return `<div class="log-line log-blocked">${escapeHtml(line)}</div>`;
            } else if (line.includes('ERROR') || line.includes('Error')) {
                return `<div class="log-line log-error">${escapeHtml(line)}</div>`;
            }
            return `<div class="log-line log-info">${escapeHtml(line)}</div>`;
        }
        
        function escapeHtml(text) {
            const div = document.createElement('div');
            div.textContent = text;
            return div.innerHTML;
        }
        
        async function fetchLogs() {
            try {
                const resp = await fetch('/api/logs');
                const data = await resp.json();
                
                // Main logs
                const mainLogs = document.getElementById('main-logs');
                mainLogs.innerHTML = data.main.map(formatLogLine).join('');
                mainLogs.scrollTop = mainLogs.scrollHeight;
                
                // Error logs
                const errorLogs = document.getElementById('error-logs');
                if (data.errors.length > 0) {
                    errorLogs.innerHTML = data.errors.map(l => 
                        `<div class="log-line log-error">${escapeHtml(l)}</div>`
                    ).join('');
                }
                
                // Parse metrics from logs
                const lastExec = data.main.filter(l => l.includes('Eq:')).pop();
                if (lastExec) {
                    const eqMatch = lastExec.match(/Eq:\$(\d+)/);
                    if (eqMatch) document.getElementById('equity').textContent = '$' + eqMatch[1];
                    
                    const regMatch = lastExec.match(/TRENDING_(\w+)/);
                    if (regMatch) {
                        const regime = regMatch[1];
                        const regimeEl = document.getElementById('regime');
                        regimeEl.textContent = regime;
                        regimeEl.style.color = regime === 'UP' ? '#00ff88' : '#ff4444';
                    }
                    
                    const fgMatch = lastExec.match(/F&G:(\d+)/);
                    if (fgMatch) document.getElementById('fg').textContent = fgMatch[1];
                    
                    const lsMatch = lastExec.match(/L\/S:([\d.]+)/);
                    if (lsMatch) document.getElementById('ls').textContent = lsMatch[1];
                }
                
            } catch (e) {
                console.error('Fetch error:', e);
            }
        }
        
        async function fetchConfig() {
            try {
                const resp = await fetch('/api/config');
                const data = await resp.json();
                
                const biasEl = document.getElementById('bias-mode');
                biasEl.textContent = data.bias.bias_mode || 'NEUTRAL';
                biasEl.className = 'config-value config-' + (data.bias.bias_mode || 'neutral').toLowerCase();
                
                document.getElementById('risk-adj').textContent = (data.bias.risk_adjustment || 1.0) + 'x';
                
                const killEl = document.getElementById('kill-switch');
                killEl.textContent = data.control.kill_switch ? 'ON' : 'OFF';
                killEl.style.color = data.control.kill_switch ? '#ff4444' : '#00ff88';
                
                document.getElementById('max-loss').textContent = '$' + (data.control.max_daily_loss_usd || 200);
                
            } catch (e) {
                console.error('Config error:', e);
            }
        }
        
        async function fetchTrades() {
            try {
                const resp = await fetch('/api/trades');
                const data = await resp.json();
                
                const tradesEl = document.getElementById('trades');
                let html = `<div class="trade-row" style="color: #666; font-weight: bold;">
                    <span>TIME</span>
                    <span>SIDE</span>
                    <span>SIZE</span>
                    <span>CONV</span>
                    <span>REGIME</span>
                </div>`;
                
                data.trades.forEach(t => {
                    const sideClass = t.side === 'BUY' ? 'trade-buy' : 'trade-sell';
                    html += `<div class="trade-row">
                        <span>${t.time}</span>
                        <span class="${sideClass}">${t.side}</span>
                        <span>$${t.size}</span>
                        <span>${t.conv}</span>
                        <span>${t.regime}</span>
                    </div>`;
                });
                
                tradesEl.innerHTML = html;
                
            } catch (e) {
                console.error('Trades error:', e);
            }
        }
        
        async function fetchServices() {
            try {
                const resp = await fetch('/api/services');
                const data = await resp.json();
                
                const servicesEl = document.getElementById('services');
                servicesEl.innerHTML = data.services.map(s => `
                    <div class="service">
                        <span class="service-status ${s.status === 'online' ? 'service-online' : 'service-offline'}"></span>
                        <strong>${s.name}</strong>
                        <div style="color: #666; font-size: 10px; margin-top: 5px;">${s.memory || ''}</div>
                    </div>
                `).join('');
                
            } catch (e) {
                console.error('Services error:', e);
            }
        }
        
        function refreshConfig() {
            fetchConfig();
        }
        
        async function killSwitch() {
            if (confirm('🛑 KILL SWITCH aktif edilsin mi? Tüm tradeler durur!')) {
                await fetch('/api/kill', { method: 'POST' });
                fetchConfig();
            }
        }
        
        async function restartAll() {
            if (confirm('Tüm servisler restart edilsin mi?')) {
                await fetch('/api/restart', { method: 'POST' });
                setTimeout(fetchServices, 3000);
            }
        }
        
        // Initial load
        fetchLogs();
        fetchConfig();
        fetchTrades();
        fetchServices();
        
        // Auto refresh
        setInterval(fetchLogs, 2000);
        setInterval(fetchConfig, 10000);
        setInterval(fetchTrades, 5000);
        setInterval(fetchServices, 15000);
    </script>
</body>
</html>
'''

@app.route('/')
def index():
    return render_template_string(HTML_TEMPLATE)

@app.route('/api/logs')
def api_logs():
    return jsonify({
        'main': list(log_buffer)[-50:],
        'errors': list(error_buffer)[-20:],
        'apex': list(apex_buffer)[-30:]
    })

@app.route('/api/config')
def api_config():
    bias = {}
    control = {}
    
    try:
        if HUMAN_BIAS.exists():
            with open(HUMAN_BIAS, 'r') as f:
                bias = json.load(f)
    except:
        pass
    
    try:
        if HUMAN_CONTROL.exists():
            with open(HUMAN_CONTROL, 'r') as f:
                control = json.load(f)
    except:
        pass
    
    return jsonify({'bias': bias, 'control': control})

@app.route('/api/trades')
def api_trades():
    trades = []
    
    # Parse from logs
    for line in list(log_buffer):
        if 'EXECUTE' in line and 'BTC/USDT' in line:
            try:
                time_match = line.split(']')[0].replace('[', '')
                side = 'SELL' if 'SELL' in line else 'BUY'
                
                size_match = line.split('$')[1].split(' ')[0] if '$' in line else '0'
                
                regime = 'TRENDING_DOWN' if 'TRENDING_DOWN' in line else 'TRENDING_UP'
                regime = regime.replace('TRENDING_', '')
                
                trades.append({
                    'time': time_match,
                    'side': side,
                    'size': size_match,
                    'conv': '0.75',
                    'regime': regime
                })
            except:
                pass
    
    return jsonify({'trades': trades[-10:]})

@app.route('/api/services')
def api_services():
    services = []
    
    try:
        result = subprocess.run(['pm2', 'jlist'], capture_output=True, text=True, timeout=5)
        pm2_data = json.loads(result.stdout)
        
        for proc in pm2_data:
            services.append({
                'name': proc.get('name', 'unknown'),
                'status': proc.get('pm2_env', {}).get('status', 'offline'),
                'memory': f"{proc.get('monit', {}).get('memory', 0) // 1024 // 1024}MB"
            })
    except:
        services = [
            {'name': 'godbrain-quantum', 'status': 'unknown', 'memory': ''},
            {'name': 'godmoney-apex', 'status': 'unknown', 'memory': ''},
            {'name': 'godbrain-chronos', 'status': 'unknown', 'memory': ''}
        ]
    
    return jsonify({'services': services})

@app.route('/api/kill', methods=['POST'])
def api_kill():
    try:
        control = {'kill_switch': True, 'block_new_entries': True, 'max_daily_loss_usd': 200, 'max_open_positions': 0}
        with open(HUMAN_CONTROL, 'w') as f:
            json.dump(control, f, indent=2)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

@app.route('/api/restart', methods=['POST'])
def api_restart():
    try:
        subprocess.run(['pm2', 'restart', 'all'], timeout=10)
        return jsonify({'success': True})
    except Exception as e:
        return jsonify({'success': False, 'error': str(e)})

# =============================================================================
# MAIN
# =============================================================================

if __name__ == '__main__':
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   🧠 GODBRAIN LIVE DASHBOARD                                                  ║
║                                                                               ║
║   Tarayıcıda aç: http://localhost:5000                                       ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)
    
    app.run(host='0.0.0.0', port=5000, debug=False, threaded=True)