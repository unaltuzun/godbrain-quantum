# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN Config Settings
Centralized configuration for OKX and system settings
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import json
from pathlib import Path
from typing import Dict, Any, Optional

# Config directory
CONFIG_DIR = Path(__file__).parent
ROOT_DIR = CONFIG_DIR.parent

# Load .env file if exists (for API keys)
ENV_FILE = ROOT_DIR / ".env"
if ENV_FILE.exists():
    for line in ENV_FILE.read_text(encoding='utf-8').splitlines():
        line = line.strip()
        if line and not line.startswith('#') and '=' in line:
            key, value = line.split('=', 1)
            os.environ.setdefault(key.strip(), value.strip())


def _load_json_config(filename: str) -> Dict[str, Any]:
    """Load a JSON config file from config directory."""
    config_path = CONFIG_DIR / filename
    if config_path.exists():
        with open(config_path, 'r', encoding='utf-8') as f:
            return json.load(f)
    return {}


# =============================================================================
# OKX CONFIGURATION
# =============================================================================

def get_okx_config() -> Dict[str, Any]:
    """
    Get OKX API configuration.
    Priority: Environment variables > config/okx_config.json
    """
    # Load from JSON first (fallback values)
    json_config = _load_json_config("okx_config.json")
    
    # Environment variables take priority
    config = {
        "api_key": os.getenv("OKX_API_KEY") or os.getenv("OKX_KEY") or json_config.get("apiKey", ""),
        "secret": os.getenv("OKX_API_SECRET") or os.getenv("OKX_SECRET") or json_config.get("secret", ""),
        "password": os.getenv("OKX_PASSWORD") or os.getenv("OKX_PASSPHRASE") or json_config.get("password", ""),
        "use_demo": _parse_bool(os.getenv("OKX_USE_DEMO", str(json_config.get("use_demo", True)))),
        "symbol": os.getenv("OKX_SYMBOL", json_config.get("symbol", "BTC/USDT")),
        "default_type": json_config.get("defaultType", "swap"),
        "poll_interval_sec": float(json_config.get("poll_interval_sec", 1.0)),
    }
    
    return config


def _parse_bool(value: Any) -> bool:
    """Parse boolean from various formats."""
    if isinstance(value, bool):
        return value
    return str(value).lower() in ("true", "1", "yes", "on")


# Pre-loaded OKX config for direct import
OKX_CONFIG = get_okx_config()


# =============================================================================
# BINANCE CONFIGURATION
# =============================================================================

def get_binance_config() -> Dict[str, Any]:
    """
    Get Binance API configuration.
    Priority: Environment variables > config/binance_config.json
    """
    # Load from JSON first (fallback values)
    json_config = _load_json_config("binance_config.json")
    
    # Environment variables take priority
    config = {
        "api_key": os.getenv("BINANCE_API_KEY") or json_config.get("apiKey", ""),
        "secret": os.getenv("BINANCE_API_SECRET") or json_config.get("secret", ""),
        "testnet": _parse_bool(os.getenv("BINANCE_TESTNET", str(json_config.get("testnet", False)))),
        "default_type": json_config.get("defaultType", "spot"),
    }
    
    return config


# Pre-loaded Binance config
BINANCE_CONFIG = get_binance_config()


def validate_binance_config() -> tuple:
    """Check if Binance configuration is valid."""
    config = BINANCE_CONFIG
    
    if not config["api_key"]:
        return False, "BINANCE_API_KEY eksik"
    if not config["secret"]:
        return False, "BINANCE_API_SECRET eksik"
    
    return True, "Binance config OK"


# =============================================================================
# TRADING CONFIGURATION  
# =============================================================================

def get_trade_config() -> Dict[str, Any]:
    """Get trading configuration."""
    json_config = _load_json_config("okx_trade_config.json")
    
    return {
        "leverage": int(os.getenv("TRADE_LEVERAGE", json_config.get("leverage", 20))),
        "position_mode": json_config.get("position_mode", "net_mode"),
        "margin_mode": json_config.get("margin_mode", "cross"),
        "order_type": json_config.get("order_type", "market"),
    }


TRADE_CONFIG = get_trade_config()


# =============================================================================
# SYSTEM CONFIGURATION
# =============================================================================

# Redis
REDIS_CONFIG = {
    "host": os.getenv("REDIS_HOST", os.getenv("GENETICS_REDIS_HOST", "127.0.0.1")),
    "port": int(os.getenv("REDIS_PORT", os.getenv("GENETICS_REDIS_PORT", 6379))),
    "db": int(os.getenv("REDIS_DB", 0)),
    "password": os.getenv("REDIS_PASS") or os.getenv("GENETICS_REDIS_PASSWORD"),
}

# Feature Flags
FEATURES = {
    "edge_ai": _parse_bool(os.getenv("EDGE_AI_ENABLED", "true")),
    "voltran": _parse_bool(os.getenv("VOLTRAN_ENABLED", "true")),
    "pulse": _parse_bool(os.getenv("PULSE_ENABLED", "true")),
    "cheat": _parse_bool(os.getenv("CHEAT_ENABLED", "true")),
}


# =============================================================================
# VALIDATION
# =============================================================================

def validate_okx_config() -> tuple[bool, str]:
    """
    Check if OKX configuration is valid.
    Returns (is_valid, message)
    """
    config = OKX_CONFIG
    
    if not config["api_key"]:
        return False, "OKX_API_KEY eksik"
    if not config["secret"]:
        return False, "OKX_API_SECRET eksik"
    if not config["password"]:
        return False, "OKX_PASSWORD eksik"
    
    return True, "OKX config OK"


def get_config_status() -> Dict[str, Any]:
    """Get overall configuration status for SERAPH awareness."""
    okx_valid, okx_msg = validate_okx_config()
    binance_valid, binance_msg = validate_binance_config()
    
    return {
        "okx_configured": okx_valid,
        "okx_status": okx_msg,
        "okx_demo_mode": OKX_CONFIG["use_demo"],
        "binance_configured": binance_valid,
        "binance_status": binance_msg,
        "redis_host": REDIS_CONFIG["host"],
        "features": FEATURES,
    }


if __name__ == "__main__":
    # Quick test
    print("=== GODBRAIN Config Status ===")
    status = get_config_status()
    for k, v in status.items():
        print(f"  {k}: {v}")
