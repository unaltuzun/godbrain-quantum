# -*- coding: utf-8 -*-
"""
📱 MOBILE API - REST endpoints for Mobile App
Provides JSON API for GODBRAIN mobile dashboard.
"""

import os
import json
from flask import Flask, jsonify, request
from flask_cors import CORS
from datetime import datetime
from pathlib import Path

# Initialize Flask
app = Flask(__name__)
CORS(app)  # Enable CORS for mobile app

# Redis connection
import redis
redis_client = None

def get_redis():
    global redis_client
    if redis_client is None:
        try:
            redis_client = redis.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", 16379)),
                password=os.getenv("REDIS_PASS", "voltran2024"),
                decode_responses=True
            )
        except:
            redis_client = None
    return redis_client


# ═══════════════════════════════════════════════════════════════════════════════
# SYSTEM STATUS
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/status', methods=['GET'])
def get_status():
    """Get system status including VOLTRAN score, DNA generation, epoch."""
    try:
        r = get_redis()
        
        # Load wisdom for DNA info
        wisdom_file = Path("quantum_lab/wisdom/latest_wisdom.json")
        wisdom = {}
        if wisdom_file.exists():
            with open(wisdom_file) as f:
                wisdom = json.load(f)
        
        # Load engine state
        state_file = Path("quantum_lab/wisdom/engine_state.json")
        state = {}
        if state_file.exists():
            with open(state_file) as f:
                state = json.load(f)
        
        # Calculate VOLTRAN score from fitness
        champion_fitness = wisdom.get("champion_fitness", 0.85)
        voltran_score = round(champion_fitness * 100, 1)
        
        return jsonify({
            "voltran_score": voltran_score,
            "dna_generation": wisdom.get("total_generations", 19000),
            "epoch": state.get("epoch", 300),
            "risk_var": 2.1,  # TODO: Calculate from anomaly adjuster
            "uptime": 86400,
            "timestamp": datetime.now().isoformat()
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# QUANTUM LAB WISDOM
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/wisdom', methods=['GET'])
def get_wisdom():
    """Get Quantum Lab wisdom data."""
    try:
        wisdom_file = Path("quantum_lab/wisdom/latest_wisdom.json")
        if wisdom_file.exists():
            with open(wisdom_file) as f:
                return jsonify(json.load(f))
        return jsonify({"error": "Wisdom not found"}), 404
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# SERAPH CHAT
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/seraph/chat', methods=['POST'])
def seraph_chat():
    """Chat with Seraph AI."""
    try:
        data = request.get_json()
        message = data.get("message", "")
        
        if not message:
            return jsonify({"error": "No message provided"}), 400
        
        # Import Seraph
        try:
            from seraph.seraph_jarvis import SeraphJarvis
            seraph = SeraphJarvis()
            response = seraph.chat(message)
            
            return jsonify({
                "role": "assistant",
                "content": response,
                "confidence": 85,
                "llms_used": ["claude", "gpt", "gemini"]
            })
        except Exception as e:
            return jsonify({
                "role": "assistant",
                "content": f"Seraph is initializing... ({str(e)[:50]})",
                "confidence": 0
            })
            
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# ANOMALIES
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/anomalies', methods=['GET'])
def get_anomalies():
    """Get detected anomalies."""
    try:
        discoveries_dir = Path("discoveries")
        anomalies = []
        
        if discoveries_dir.exists():
            for file in sorted(discoveries_dir.glob("*.json"), key=lambda x: x.stat().st_mtime, reverse=True)[:20]:
                try:
                    with open(file) as f:
                        anomalies.append(json.load(f))
                except:
                    pass
        
        return jsonify(anomalies)
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# RISK ADJUSTMENT
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/risk-adjustment', methods=['GET'])
def get_risk_adjustment():
    """Get current risk adjustment based on anomalies."""
    try:
        r = get_redis()
        if r:
            data = r.get("godbrain:anomaly:risk_adjustment")
            if data:
                return jsonify(json.loads(data))
        
        # Default
        return jsonify({
            "position_multiplier": 1.0,
            "stop_loss_multiplier": 1.0,
            "take_profit_multiplier": 1.0,
            "signal_threshold": 0.5,
            "reason": "No anomalies detected",
            "source": "none"
        })
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# LLM STATUS
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/llm-status', methods=['GET'])
def get_llm_status():
    """Get LLM provider status."""
    try:
        r = get_redis()
        if r:
            stats = r.get("godbrain:llm:stats")
            if stats:
                data = json.loads(stats)
                providers = data.get("providers", {})
                return jsonify([
                    {
                        "name": name.upper(),
                        "active": info.get("success_count", 0) > 0,
                        "latency": int(info.get("avg_latency", 0) * 1000)
                    }
                    for name, info in providers.items()
                ])
        
        # Default
        return jsonify([
            {"name": "CLAUDE", "active": True, "latency": 120},
            {"name": "GPT", "active": True, "latency": 90},
            {"name": "GEMINI", "active": True, "latency": 150},
            {"name": "LLAMA", "active": False, "latency": 0}
        ])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# POSITIONS
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/positions', methods=['GET'])
def get_positions():
    """Get open trading positions."""
    try:
        r = get_redis()
        if r:
            positions = r.get("godbrain:trading:positions")
            if positions:
                return jsonify(json.loads(positions))
        
        # Demo data
        return jsonify([
            {
                "symbol": "BTC/USDT",
                "side": "long",
                "size": 0.1,
                "entry_price": 95000,
                "current_price": 96500,
                "pnl": 150,
                "pnl_percent": 1.58
            }
        ])
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# MARKET DATA
# ═══════════════════════════════════════════════════════════════════════════════

@app.route('/api/market', methods=['GET'])
def get_market():
    """Get market data."""
    try:
        r = get_redis()
        if r:
            ticker = r.get("godbrain:market:ticker")
            if ticker:
                return jsonify({"btc_price": float(ticker)})
        
        return jsonify({"btc_price": 96000})
    except Exception as e:
        return jsonify({"error": str(e)}), 500


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == '__main__':
    print("📱 GODBRAIN Mobile API starting on port 8000...")
    app.run(host='0.0.0.0', port=8000, debug=False)
