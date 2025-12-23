# -*- coding: utf-8 -*-
"""
GODBRAIN CONFIG CENTER
The single source of truth for all system parameters.
Unifies .env, environment variables, and defaults.
"""

import os
import sys
from pathlib import Path
from dotenv import load_dotenv

# Base Paths
THIS_FILE = Path(__file__).resolve()
ROOT = Path(os.getenv("GODBRAIN_ROOT", str(THIS_FILE.parent))).resolve()

# Load environment variables from .env
load_dotenv(ROOT / ".env")

class GodbrainConfig:
    """Central configuration class."""
    
    # --- INFRASTRUCTURE ---
    ROOT_DIR = ROOT
    LOG_DIR = ROOT / "logs"
    APEX_LIVE = os.getenv("APEX_LIVE", "false").lower() in ("true", "1", "yes")
    
    # Redis
    REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
    REDIS_PORT = int(os.getenv("REDIS_PORT", "16379"))
    REDIS_PASS = os.getenv("REDIS_PASS", "voltran2024")
    
    # Specific Redis Namespaces (Goal for Phase 2)
    REDIS_GENETICS_HOST = os.getenv("GENETICS_REDIS_HOST", REDIS_HOST)
    REDIS_GENETICS_PORT = int(os.getenv("GENETICS_REDIS_PORT", REDIS_PORT))
    REDIS_GENETICS_PASS = os.getenv("GENETICS_REDIS_PASSWORD", REDIS_PASS)
    
    # --- EXCHANGE ---
    OKX_KEY = os.getenv("OKX_API_KEY")
    OKX_SECRET = os.getenv("OKX_API_SECRET")
    OKX_PASS = os.getenv("OKX_API_PASSPHRASE")
    
    # Symbols - PEPE, TIA, PI (User's choice for high volatility)
    SYMBOLS_RAW = os.getenv("SYMBOLS", "1000PEPE/USDT:USDT,TIA/USDT:USDT,PI/USDT:USDT")
    TRADING_PAIRS = [s.strip() for s in SYMBOLS_RAW.split(",") if s.strip()]
    
    # --- REDIS NAMESPACES (Phase 2) ---
    NS_GENETICS = "genetics"
    NS_CACHE = "cache"
    NS_STATE = "state"
    NS_PULSE = "pulse"

    # Genetics Keys
    DNA_KEY = f"{NS_GENETICS}:blackjack:dna"
    META_KEY = f"{NS_GENETICS}:blackjack:meta"
    
    # Legacy support / Voltran Bridge keys
    BJ_DNA_KEY = f"{NS_GENETICS}:blackjack:dna"
    RL_DNA_KEY = f"{NS_GENETICS}:roulette:dna"
    CH_DNA_KEY = f"{NS_GENETICS}:chaos:dna"
    
    BJ_META_KEY = f"{NS_GENETICS}:blackjack:meta"
    RL_META_KEY = f"{NS_GENETICS}:roulette:meta"
    CH_META_KEY = f"{NS_GENETICS}:chaos:meta"
    DNA_REFRESH_INTERVAL = 60
    
    VOLTRAN_REFRESH_INTERVAL = 30
    
    # --- EDGE AI ---
    EDGE_AI_ENABLED = os.getenv("EDGE_AI_ENABLED", "true").lower() in ("1", "true", "yes", "on")
    EDGE_AI_CONFIG = ROOT / "config" / "edge_ai_config.json"

    # --- LOGGING ---
    LOG_DECISIONS = LOG_DIR / "agg_decisions.log"
    SIGNAL_FILE = LOG_DIR / "apex_signal.json"

    @classmethod
    def ensure_paths(cls):
        """Create necessary directories."""
        cls.LOG_DIR.mkdir(parents=True, exist_ok=True)

# Initialize paths
GodbrainConfig.ensure_paths()

# Singleton-like access
config = GodbrainConfig()

if __name__ == "__main__":
    print(f"🚀 GODBRAIN CONFIG CENTER LOADED")
    print(f"📍 ROOT: {config.ROOT_DIR}")
    print(f"📈 LIVE MODE: {config.APEX_LIVE}")
    print(f"🪙 SYMBOLS: {config.TRADING_PAIRS}")
    print(f"🔗 REDIS: {config.REDIS_HOST}:{config.REDIS_PORT}")
