# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN DATA FEEDS BRIDGE v1.0
═══════════════════════════════════════════════════════════════════════════════

Agg.py ↔ Apex arasındaki tick stream köprüsü.

Problem: "No tick found yet" - Apex tick bekliyor ama agg.py göndermiyor.
Çözüm: publish_tick() / get_last_tick() API

Kullanım:
  - agg.py: EXECUTE sonrası publish_tick() çağır
  - apex.py: Loop içinde get_last_tick() ile tick al

Transport seçenekleri:
  1. Redis (önerilen, production)
  2. File-based (fallback, Redis yoksa)
  
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import json
import time
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass, asdict
import threading

# =============================================================================
# PATHS
# =============================================================================

QUANTUM_ROOT = Path("/mnt/c/godbrain-quantum")
TICK_FILE = QUANTUM_ROOT / "logs" / "tick_stream.jsonl"
TICK_LATEST = QUANTUM_ROOT / "logs" / "tick_latest.json"

# =============================================================================
# REDIS SETUP (Optional)
# =============================================================================

_redis_client = None
_REDIS_AVAILABLE = False
REDIS_TICK_KEY = "godbrain:tick_stream"
REDIS_TICK_LATEST = "godbrain:tick_latest"

try:
    import redis
    redis_dsn = os.getenv("GODBRAIN_REDIS_DSN", "redis://localhost:6379/0")
    _redis_client = redis.from_url(redis_dsn, decode_responses=True)
    _redis_client.ping()
    _REDIS_AVAILABLE = True
except:
    _REDIS_AVAILABLE = False


# =============================================================================
# TICK DATA CLASS
# =============================================================================

@dataclass
class TickData:
    """Tick sent from agg.py to Apex."""
    timestamp: float
    symbol: str
    side: str                    # BUY / SELL
    size_usd: float
    equity: float
    regime: str                  # TRENDING_UP / TRENDING_DOWN / etc
    conviction: float            # 0.0 - 1.0
    price: float = 0.0
    source: str = "GODQUANTUM"
    
    # Anti-whipsaw metadata
    filter_reason: str = ""
    regime_age_seconds: int = 0
    
    # Optional extras
    meta: Dict[str, Any] = None
    
    def __post_init__(self):
        if self.meta is None:
            self.meta = {}
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> 'TickData':
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})
    
    def to_json(self) -> str:
        return json.dumps(self.to_dict())
    
    @classmethod
    def from_json(cls, json_str: str) -> 'TickData':
        return cls.from_dict(json.loads(json_str))


# =============================================================================
# PUBLISH / GET API
# =============================================================================

def publish_tick(
    symbol: str,
    side: str,
    size_usd: float,
    equity: float,
    regime: str,
    conviction: float,
    price: float = 0.0,
    filter_reason: str = "",
    regime_age_seconds: int = 0,
    meta: Optional[Dict[str, Any]] = None
) -> bool:
    """
    Publish a tick from agg.py to Apex.
    
    Called after EXECUTE decision is made.
    
    Returns True if published successfully.
    """
    tick = TickData(
        timestamp=time.time(),
        symbol=symbol,
        side=side,
        size_usd=size_usd,
        equity=equity,
        regime=regime,
        conviction=conviction,
        price=price,
        source="GODQUANTUM",
        filter_reason=filter_reason,
        regime_age_seconds=regime_age_seconds,
        meta=meta or {}
    )
    
    success = False
    
    # 1. Try Redis first
    if _REDIS_AVAILABLE and _redis_client:
        try:
            # Push to list (stream)
            _redis_client.lpush(REDIS_TICK_KEY, tick.to_json())
            # Trim to last 1000 ticks
            _redis_client.ltrim(REDIS_TICK_KEY, 0, 999)
            # Also set latest for quick access
            _redis_client.set(REDIS_TICK_LATEST, tick.to_json())
            success = True
        except Exception as e:
            print(f"[DATA_FEEDS] Redis publish failed: {e}")
    
    # 2. Always write to file as backup
    try:
        TICK_FILE.parent.mkdir(parents=True, exist_ok=True)
        
        # Append to stream file
        with open(TICK_FILE, "a", encoding="utf-8") as f:
            f.write(tick.to_json() + "\n")
        
        # Write latest
        with open(TICK_LATEST, "w", encoding="utf-8") as f:
            f.write(tick.to_json())
        
        success = True
    except Exception as e:
        print(f"[DATA_FEEDS] File publish failed: {e}")
    
    if success:
        ts = datetime.now().strftime("%H:%M:%S")
        print(f"[DATA_FEEDS] [{ts}] TICK PUBLISHED: {side} {symbol} ${size_usd:.0f} | Regime: {regime}")
    
    return success


def get_last_tick(
    block: bool = True,
    timeout: float = 1.0,
    consume: bool = True
) -> Optional[TickData]:
    """
    Get the last tick for Apex consumption.
    
    Args:
        block: If True, wait for tick (up to timeout)
        timeout: Max seconds to wait
        consume: If True, remove tick after reading (prevents double-exec)
    
    Returns:
        TickData if available, None otherwise
    """
    start_time = time.time()
    
    while True:
        tick_data = None
        
        # 1. Try Redis first
        if _REDIS_AVAILABLE and _redis_client:
            try:
                if consume:
                    # Pop from list (consume)
                    raw = _redis_client.rpop(REDIS_TICK_KEY)
                else:
                    # Just peek at latest
                    raw = _redis_client.get(REDIS_TICK_LATEST)
                
                if raw:
                    tick_data = TickData.from_json(raw)
            except Exception as e:
                pass
        
        # 2. Fall back to file
        if tick_data is None and TICK_LATEST.exists():
            try:
                with open(TICK_LATEST, "r", encoding="utf-8") as f:
                    raw = f.read().strip()
                    if raw:
                        tick_data = TickData.from_json(raw)
                        
                        # Check if it's fresh (within last 30 seconds)
                        if tick_data and (time.time() - tick_data.timestamp) > 30:
                            tick_data = None  # Stale tick
                        
                        # Consume by clearing file
                        if tick_data and consume:
                            with open(TICK_LATEST, "w", encoding="utf-8") as f:
                                f.write("")
            except Exception as e:
                pass
        
        if tick_data:
            return tick_data
        
        # Check timeout
        if not block or (time.time() - start_time) >= timeout:
            return None
        
        time.sleep(0.1)


def get_tick_stream(count: int = 10) -> list:
    """
    Get recent tick history.
    
    Args:
        count: Number of ticks to retrieve
    
    Returns:
        List of TickData (newest first)
    """
    ticks = []
    
    # Try Redis
    if _REDIS_AVAILABLE and _redis_client:
        try:
            raw_list = _redis_client.lrange(REDIS_TICK_KEY, 0, count - 1)
            ticks = [TickData.from_json(r) for r in raw_list]
            return ticks
        except:
            pass
    
    # Fall back to file
    if TICK_FILE.exists():
        try:
            with open(TICK_FILE, "r", encoding="utf-8") as f:
                lines = f.readlines()
            
            # Get last N lines
            recent = lines[-count:] if len(lines) >= count else lines
            recent.reverse()  # Newest first
            
            for line in recent:
                try:
                    ticks.append(TickData.from_json(line.strip()))
                except:
                    pass
        except:
            pass
    
    return ticks


def clear_tick_stream():
    """Clear all pending ticks (for reset/cleanup)."""
    
    if _REDIS_AVAILABLE and _redis_client:
        try:
            _redis_client.delete(REDIS_TICK_KEY)
            _redis_client.delete(REDIS_TICK_LATEST)
        except:
            pass
    
    try:
        if TICK_LATEST.exists():
            TICK_LATEST.unlink()
    except:
        pass


# =============================================================================
# HEALTH CHECK
# =============================================================================

def get_feed_status() -> dict:
    """Get data feed status."""
    return {
        "redis_available": _REDIS_AVAILABLE,
        "tick_file": str(TICK_FILE),
        "tick_latest": str(TICK_LATEST),
        "tick_file_exists": TICK_FILE.exists(),
        "latest_exists": TICK_LATEST.exists(),
        "pending_ticks": len(get_tick_stream(100)) if TICK_FILE.exists() else 0
    }


# =============================================================================
# TEST
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("DATA FEEDS BRIDGE TEST")
    print("=" * 60)
    
    # Status
    status = get_feed_status()
    print(f"\nStatus:")
    for k, v in status.items():
        print(f"  {k}: {v}")
    
    # Test publish
    print("\n--- Testing publish_tick ---")
    publish_tick(
        symbol="BTC/USDT:USDT",
        side="BUY",
        size_usd=500.0,
        equity=4000.0,
        regime="TRENDING_UP",
        conviction=0.75,
        price=98000.0,
        filter_reason="PASS",
        meta={"test": True}
    )
    
    # Test get
    print("\n--- Testing get_last_tick ---")
    tick = get_last_tick(block=False, consume=False)
    if tick:
        print(f"Got tick: {tick.side} {tick.symbol} ${tick.size_usd}")
    else:
        print("No tick found")
    
    # Test stream
    print("\n--- Testing get_tick_stream ---")
    stream = get_tick_stream(5)
    print(f"Stream has {len(stream)} ticks")
    for t in stream[:3]:
        print(f"  {t.side} {t.symbol} @ {t.timestamp}")
