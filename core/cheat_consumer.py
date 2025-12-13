"""
Cheat Signal Consumer for AGG
"""
import json
from pathlib import Path
from datetime import datetime, timedelta

SIGNAL_FILE = Path("/mnt/c/godbrain-quantum/logs/cheat_signals.json")

def get_cheat_signal(symbol: str) -> dict:
    """Get latest cheat signal for a symbol"""
    try:
        if not SIGNAL_FILE.exists():
            return None
        
        with open(SIGNAL_FILE, 'r') as f:
            data = json.load(f)
        
        # Check if signal is fresh (< 10 minutes)
        ts = datetime.fromisoformat(data['timestamp'])
        if datetime.now() - ts > timedelta(minutes=10):
            return None
        
        # Find signal for this symbol
        for sig in data.get('signals', []):
            if sig['symbol'] == symbol:
                return sig
        
        return None
    except:
        return None

def get_cheat_override(symbol: str) -> tuple:
    """
    Returns (action_override, confidence_boost, size_multiplier)
    AGG bunu kullanarak cheat sinyallerini trade'e dönüştürür
    """
    sig = get_cheat_signal(symbol)
    if not sig:
        return None, 0, 1.0
    
    conf = sig.get('confidence', 0)
    action = sig.get('action')
    
    if conf >= 0.7:
        return action, 0.25, 1.5  # Strong signal - boost
    elif conf >= 0.5:
        return action, 0.15, 1.2  # Medium signal
    else:
        return None, 0, 1.0  # Weak - ignore
