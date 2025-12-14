# ==============================================================================
# SYSTEM TOOLS - GodBrain system state access
# ==============================================================================
"""
System tools for Seraph.
Provides access to internal system state, DNA parameters, and signals.
"""

import json
import logging
from typing import Dict, Any, Optional
from pathlib import Path

logger = logging.getLogger("seraph.tools.system")

# Project root
ROOT = Path(__file__).parent.parent.parent


def get_system_state() -> Dict[str, Any]:
    """
    Get current GodBrain system state.
    
    Returns:
        Dict with system status, health, active strategies, etc.
    """
    state = {
        "status": "ONLINE",
        "health": {},
        "active_strategies": [],
        "uptime": None
    }
    
    # Check service health
    services = ["redis", "voltran", "market_feed", "genetics", "seraph"]
    for service in services:
        state["health"][service] = "unknown"
    
    # Try to get actual state from Redis
    try:
        import os
        import redis
        
        redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
        redis_port = int(os.getenv("REDIS_PORT", "16379"))
        redis_pass = os.getenv("REDIS_PASS", "voltran2024")
        
        r = redis.Redis(host=redis_host, port=redis_port, password=redis_pass, decode_responses=True)
        r.ping()
        state["health"]["redis"] = "healthy"
        
        # Get active strategy
        strategy = r.get("godbrain:active_strategy")
        if strategy:
            state["active_strategies"].append(strategy)
            
    except Exception as e:
        state["health"]["redis"] = f"error: {str(e)[:50]}"
    
    return state


def get_dna_params() -> Dict[str, Any]:
    """
    Get current active DNA parameters from genetic evolution.
    
    Returns:
        Dict with stop_loss, take_profit, RSI levels, etc.
    """
    try:
        genome_file = ROOT / "logs" / "active_genome.json"
        if genome_file.exists():
            with open(genome_file, 'r') as f:
                data = json.load(f)
                return {
                    "params": data.get("params", {}),
                    "generation": data.get("generation", 0),
                    "champion_id": data.get("champion_id", ""),
                    "fitness": data.get("champion_fitness", 0),
                    "source": data.get("source", "unknown"),
                    "timestamp": data.get("timestamp", "")
                }
    except Exception as e:
        logger.warning(f"Error reading DNA params: {e}")
    
    return {
        "params": {},
        "error": "DNA parameters unavailable"
    }


def get_voltran_signals() -> Dict[str, Any]:
    """
    Get latest Voltran trading signals.
    
    Returns:
        Dict with current signals, regime, and recommendations
    """
    try:
        signal_file = ROOT / "logs" / "apex_signal.json"
        if signal_file.exists():
            with open(signal_file, 'r') as f:
                data = json.load(f)
                return {
                    "symbol": data.get("symbol", ""),
                    "action": data.get("action", ""),
                    "size_usd": data.get("size_usd", 0),
                    "regime": data.get("regime", ""),
                    "conviction": data.get("extras", {}).get("conviction", 0),
                    "quantum_score": data.get("extras", {}).get("quantum_score", 0),
                    "voltran_factor": data.get("extras", {}).get("voltran_factor", 1.0),
                    "timestamp": data.get("timestamp", "")
                }
    except Exception as e:
        logger.warning(f"Error reading Voltran signals: {e}")
    
    return {
        "signal": None,
        "error": "Voltran signals unavailable"
    }


def get_wisdom() -> Dict[str, Any]:
    """
    Get quantum wisdom from multiverse evolution.
    
    Returns:
        Dict with ensemble parameters and regime champions
    """
    try:
        wisdom_file = ROOT / "quantum_lab" / "wisdom" / "latest_wisdom.json"
        if wisdom_file.exists():
            with open(wisdom_file, 'r') as f:
                data = json.load(f)
                return {
                    "total_generations": data.get("total_generations", 0),
                    "ensemble_params": data.get("ensemble_params", {}),
                    "global_champion": data.get("global_champion", {}),
                    "regime_champions": list(data.get("regime_champions", {}).keys()),
                    "timestamp": data.get("timestamp", "")
                }
    except Exception as e:
        logger.warning(f"Error reading wisdom: {e}")
    
    return {
        "wisdom": None,
        "error": "Wisdom unavailable"
    }

