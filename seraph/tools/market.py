# ==============================================================================
# MARKET TOOLS - Real-time market data access
# ==============================================================================
"""
Market data tools for Seraph.
Provides access to real-time and historical market information.
"""

import json
import logging
from typing import Optional, Dict, Any
from pathlib import Path

logger = logging.getLogger("seraph.tools.market")

# Project root
ROOT = Path(__file__).parent.parent.parent


def get_market_data(symbol: str = "BTC/USDT") -> Dict[str, Any]:
    """
    Get latest market data for a symbol.
    
    Args:
        symbol: Trading pair (e.g., "BTC/USDT", "ETH/USDT")
    
    Returns:
        Dict with price, volume, change, etc.
    """
    try:
        # Try to read from tick file
        tick_file = ROOT / "logs" / "tick_latest.json"
        if tick_file.exists():
            with open(tick_file, 'r') as f:
                data = json.load(f)
                return {
                    "symbol": symbol,
                    "price": data.get("price", 0),
                    "timestamp": data.get("timestamp", ""),
                    "volume_24h": data.get("volume", 0),
                    "change_24h": data.get("change", 0),
                    "source": "tick_file"
                }
    except Exception as e:
        logger.warning(f"Error reading tick file: {e}")
    
    # Fallback: try Redis
    try:
        from ..memory.short_term import ShortTermMemory
        import os
        
        redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
        redis_port = int(os.getenv("REDIS_PORT", "16379"))
        redis_pass = os.getenv("REDIS_PASS", "voltran2024")
        
        import redis
        r = redis.Redis(host=redis_host, port=redis_port, password=redis_pass, decode_responses=True)
        
        price = r.get("godbrain:price") or r.get("price:btc")
        if price:
            return {
                "symbol": symbol,
                "price": float(price),
                "source": "redis"
            }
    except Exception as e:
        logger.warning(f"Redis market data error: {e}")
    
    return {
        "symbol": symbol,
        "price": None,
        "error": "Market data unavailable",
        "source": "none"
    }


def get_market_summary() -> Dict[str, Any]:
    """
    Get summary of all tracked markets.
    
    Returns:
        Dict with summary of all trading pairs
    """
    symbols = ["BTC/USDT", "ETH/USDT", "SOL/USDT", "DOGE/USDT", "XRP/USDT"]
    summary = {
        "timestamp": None,
        "markets": {}
    }
    
    for symbol in symbols:
        data = get_market_data(symbol)
        summary["markets"][symbol] = data
        if data.get("timestamp"):
            summary["timestamp"] = data["timestamp"]
    
    return summary

