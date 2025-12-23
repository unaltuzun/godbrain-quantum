# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN RISK MANAGER - Enterprise-Grade Hard Limits & Circuit Breakers
═══════════════════════════════════════════════════════════════════════════════

Features:
- Daily loss limits (USD and percentage)
- Per-trade position limits
- Maximum leverage enforcement
- Circuit breakers (loss streak, drawdown halt)
- Redis-backed persistent state
- Real-time limit checking before every trade

Usage:
    from core.risk_manager import RiskManager, get_risk_manager
    
    rm = get_risk_manager()
    if rm.can_open_position(size_usd=100, leverage=5):
        # Safe to open position
    else:
        # Limit breached, do not trade
"""

import os
import json
import time
from dataclasses import dataclass, asdict
from datetime import datetime, timedelta
from typing import Dict, Any, Optional, Tuple
import redis


# =============================================================================
# RISK LIMITS CONFIGURATION
# =============================================================================

@dataclass
class RiskLimits:
    """
    Hard risk limits for the trading system.
    All values are enforced before any trade is executed.
    """
    # Daily Limits
    max_daily_loss_usd: float = 100.0      # Günde max $100 kayıp
    max_daily_loss_pct: float = 5.0        # Günde max %5 kayıp
    
    # Per-Trade Limits
    max_position_size_usd: float = 500.0   # Tek pozisyon max $500
    max_position_size_pct: float = 25.0    # Equity'nin max %25'i
    
    # Global Limits
    max_open_positions: int = 3            # Max 3 eşzamanlı pozisyon
    max_leverage: float = 10.0             # Max 10x kaldıraç (USER SPECIFIED)
    max_total_exposure_pct: float = 75.0   # Toplam max %75 exposure
    
    # Circuit Breakers
    loss_streak_limit: int = 5             # 5 ardışık kayıptan sonra dur
    drawdown_halt_pct: float = 10.0        # %10 drawdown'da dur
    
    # Cooldown Settings
    cooldown_after_halt_minutes: int = 60  # Halt sonrası 1 saat bekleme
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiskLimits":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


@dataclass
class RiskState:
    """
    Current risk state tracked in Redis.
    """
    # Daily tracking (resets at midnight UTC)
    daily_pnl_usd: float = 0.0
    daily_trades: int = 0
    daily_wins: int = 0
    daily_losses: int = 0
    
    # Streak tracking
    current_loss_streak: int = 0
    
    # Drawdown tracking
    peak_equity_usd: float = 0.0
    current_equity_usd: float = 0.0
    
    # Position tracking
    open_positions_count: int = 0
    total_exposure_usd: float = 0.0
    
    # Halt status
    is_halted: bool = False
    halt_reason: str = ""
    halt_timestamp: float = 0.0
    
    # Metadata
    last_update: float = 0.0
    last_reset_date: str = ""
    
    def to_dict(self) -> Dict[str, Any]:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict[str, Any]) -> "RiskState":
        return cls(**{k: v for k, v in data.items() if k in cls.__dataclass_fields__})


# =============================================================================
# RISK MANAGER
# =============================================================================

class RiskManager:
    """
    Centralized risk management for GODBRAIN trading system.
    
    Enforces hard limits and circuit breakers before every trade.
    State is persisted in Redis to survive restarts.
    """
    
    REDIS_KEY_LIMITS = "godbrain:risk:limits"
    REDIS_KEY_STATE = "godbrain:risk:state"
    
    def __init__(self, redis_client: Optional[redis.Redis] = None):
        self._redis = redis_client
        self._limits = RiskLimits()
        self._state = RiskState()
        self._load_from_redis()
    
    # -------------------------------------------------------------------------
    # PUBLIC API
    # -------------------------------------------------------------------------
    
    def can_open_position(
        self,
        size_usd: float,
        leverage: float,
        equity_usd: float,
    ) -> Tuple[bool, str]:
        """
        Check if a new position can be opened.
        
        Returns:
            (can_trade, reason)
        """
        # Reload state
        self._load_state()
        
        # Check halt status
        if self._state.is_halted:
            if not self._check_cooldown_expired():
                return False, f"HALTED: {self._state.halt_reason}"
            else:
                self._resume_trading("Cooldown expired")
        
        # Check daily loss limit
        if abs(self._state.daily_pnl_usd) >= self._limits.max_daily_loss_usd:
            if self._state.daily_pnl_usd < 0:
                self._halt_trading("Daily loss limit reached")
                return False, f"DAILY_LOSS_LIMIT: ${abs(self._state.daily_pnl_usd):.2f} >= ${self._limits.max_daily_loss_usd}"
        
        # Check daily loss percentage
        if equity_usd > 0:
            daily_loss_pct = abs(self._state.daily_pnl_usd) / equity_usd * 100
            if daily_loss_pct >= self._limits.max_daily_loss_pct and self._state.daily_pnl_usd < 0:
                self._halt_trading("Daily loss percentage limit reached")
                return False, f"DAILY_LOSS_PCT: {daily_loss_pct:.2f}% >= {self._limits.max_daily_loss_pct}%"
        
        # Check loss streak
        if self._state.current_loss_streak >= self._limits.loss_streak_limit:
            self._halt_trading(f"Loss streak: {self._state.current_loss_streak}")
            return False, f"LOSS_STREAK: {self._state.current_loss_streak} >= {self._limits.loss_streak_limit}"
        
        # Check drawdown
        if self._state.peak_equity_usd > 0:
            drawdown_pct = (self._state.peak_equity_usd - self._state.current_equity_usd) / self._state.peak_equity_usd * 100
            if drawdown_pct >= self._limits.drawdown_halt_pct:
                self._halt_trading(f"Drawdown: {drawdown_pct:.2f}%")
                return False, f"DRAWDOWN_HALT: {drawdown_pct:.2f}% >= {self._limits.drawdown_halt_pct}%"
        
        # Check max open positions
        if self._state.open_positions_count >= self._limits.max_open_positions:
            return False, f"MAX_POSITIONS: {self._state.open_positions_count} >= {self._limits.max_open_positions}"
        
        # Check leverage limit
        if leverage > self._limits.max_leverage:
            return False, f"MAX_LEVERAGE: {leverage}x > {self._limits.max_leverage}x"
        
        # Check position size (USD)
        if size_usd > self._limits.max_position_size_usd:
            return False, f"MAX_SIZE_USD: ${size_usd:.2f} > ${self._limits.max_position_size_usd}"
        
        # Check position size (percentage)
        if equity_usd > 0:
            size_pct = size_usd / equity_usd * 100
            if size_pct > self._limits.max_position_size_pct:
                return False, f"MAX_SIZE_PCT: {size_pct:.2f}% > {self._limits.max_position_size_pct}%"
        
        # Check total exposure
        new_exposure = self._state.total_exposure_usd + size_usd
        if equity_usd > 0:
            exposure_pct = new_exposure / equity_usd * 100
            if exposure_pct > self._limits.max_total_exposure_pct:
                return False, f"MAX_EXPOSURE: {exposure_pct:.2f}% > {self._limits.max_total_exposure_pct}%"
        
        return True, "OK"
    
    def record_trade_result(
        self,
        pnl_usd: float,
        is_win: bool,
        position_size_usd: float = 0.0,
    ) -> None:
        """
        Record the result of a completed trade.
        Updates daily PnL, streaks, and drawdown tracking.
        """
        self._load_state()
        self._check_daily_reset()
        
        # Update daily PnL
        self._state.daily_pnl_usd += pnl_usd
        self._state.daily_trades += 1
        
        if is_win:
            self._state.daily_wins += 1
            self._state.current_loss_streak = 0
        else:
            self._state.daily_losses += 1
            self._state.current_loss_streak += 1
        
        # Update equity and drawdown
        self._state.current_equity_usd += pnl_usd
        if self._state.current_equity_usd > self._state.peak_equity_usd:
            self._state.peak_equity_usd = self._state.current_equity_usd
        
        # Update position count
        if position_size_usd > 0:
            self._state.total_exposure_usd -= position_size_usd
            self._state.open_positions_count = max(0, self._state.open_positions_count - 1)
        
        self._state.last_update = time.time()
        self._save_state()
    
    def record_position_open(self, size_usd: float) -> None:
        """Record a new position being opened."""
        self._load_state()
        self._state.open_positions_count += 1
        self._state.total_exposure_usd += size_usd
        self._state.last_update = time.time()
        self._save_state()
    
    def record_position_close(self, size_usd: float) -> None:
        """Record a position being closed (without PnL update)."""
        self._load_state()
        self._state.open_positions_count = max(0, self._state.open_positions_count - 1)
        self._state.total_exposure_usd = max(0, self._state.total_exposure_usd - size_usd)
        self._state.last_update = time.time()
        self._save_state()
    
    def update_equity(self, equity_usd: float) -> None:
        """Update current equity (call periodically from dashboard)."""
        self._load_state()
        self._state.current_equity_usd = equity_usd
        if equity_usd > self._state.peak_equity_usd:
            self._state.peak_equity_usd = equity_usd
        self._state.last_update = time.time()
        self._save_state()
    
    def get_status(self) -> Dict[str, Any]:
        """Get current risk status for dashboard display."""
        self._load_state()
        self._check_daily_reset()
        
        # Calculate metrics
        drawdown_pct = 0.0
        if self._state.peak_equity_usd > 0:
            drawdown_pct = (self._state.peak_equity_usd - self._state.current_equity_usd) / self._state.peak_equity_usd * 100
        
        return {
            "is_halted": self._state.is_halted,
            "halt_reason": self._state.halt_reason,
            "daily_pnl_usd": self._state.daily_pnl_usd,
            "daily_trades": self._state.daily_trades,
            "daily_wins": self._state.daily_wins,
            "daily_losses": self._state.daily_losses,
            "loss_streak": self._state.current_loss_streak,
            "drawdown_pct": drawdown_pct,
            "open_positions": self._state.open_positions_count,
            "total_exposure_usd": self._state.total_exposure_usd,
            "current_equity_usd": self._state.current_equity_usd,
            "peak_equity_usd": self._state.peak_equity_usd,
            "limits": self._limits.to_dict(),
            "last_update": datetime.fromtimestamp(self._state.last_update).isoformat() if self._state.last_update else None,
        }
    
    def get_limits(self) -> RiskLimits:
        """Get current risk limits."""
        self._load_limits()
        return self._limits
    
    def set_limits(self, limits: RiskLimits) -> None:
        """Update risk limits."""
        self._limits = limits
        self._save_limits()
    
    def halt_trading(self, reason: str = "Manual halt") -> None:
        """Manually halt all trading."""
        self._halt_trading(reason)
    
    def resume_trading(self, reason: str = "Manual resume") -> None:
        """Manually resume trading after halt."""
        self._resume_trading(reason)
    
    def reset_daily_stats(self) -> None:
        """Manually reset daily stats."""
        self._load_state()
        self._state.daily_pnl_usd = 0.0
        self._state.daily_trades = 0
        self._state.daily_wins = 0
        self._state.daily_losses = 0
        self._state.last_reset_date = datetime.utcnow().strftime("%Y-%m-%d")
        self._save_state()
    
    # -------------------------------------------------------------------------
    # INTERNAL METHODS
    # -------------------------------------------------------------------------
    
    def _halt_trading(self, reason: str) -> None:
        """Internal: Halt trading with reason."""
        self._state.is_halted = True
        self._state.halt_reason = reason
        self._state.halt_timestamp = time.time()
        self._save_state()
        print(f"[RISK MANAGER] 🚨 TRADING HALTED: {reason}")
    
    def _resume_trading(self, reason: str) -> None:
        """Internal: Resume trading."""
        self._state.is_halted = False
        self._state.halt_reason = ""
        self._state.halt_timestamp = 0.0
        self._state.current_loss_streak = 0  # Reset streak on resume
        self._save_state()
        print(f"[RISK MANAGER] ✅ TRADING RESUMED: {reason}")
    
    def _check_cooldown_expired(self) -> bool:
        """Check if cooldown period has expired after a halt."""
        if self._state.halt_timestamp == 0:
            return True
        cooldown_seconds = self._limits.cooldown_after_halt_minutes * 60
        return time.time() - self._state.halt_timestamp >= cooldown_seconds
    
    def _check_daily_reset(self) -> None:
        """Reset daily stats if it's a new day (UTC)."""
        today = datetime.utcnow().strftime("%Y-%m-%d")
        if self._state.last_reset_date != today:
            self._state.daily_pnl_usd = 0.0
            self._state.daily_trades = 0
            self._state.daily_wins = 0
            self._state.daily_losses = 0
            self._state.last_reset_date = today
            self._save_state()
    
    def _load_from_redis(self) -> None:
        """Load both limits and state from Redis."""
        self._load_limits()
        self._load_state()
    
    def _load_limits(self) -> None:
        """Load limits from Redis."""
        if not self._redis:
            return
        try:
            data = self._redis.get(self.REDIS_KEY_LIMITS)
            if data:
                self._limits = RiskLimits.from_dict(json.loads(data))
        except Exception as e:
            print(f"[RISK MANAGER] Error loading limits: {e}")
    
    def _save_limits(self) -> None:
        """Save limits to Redis."""
        if not self._redis:
            return
        try:
            self._redis.set(self.REDIS_KEY_LIMITS, json.dumps(self._limits.to_dict()))
        except Exception as e:
            print(f"[RISK MANAGER] Error saving limits: {e}")
    
    def _load_state(self) -> None:
        """Load state from Redis."""
        if not self._redis:
            return
        try:
            data = self._redis.get(self.REDIS_KEY_STATE)
            if data:
                self._state = RiskState.from_dict(json.loads(data))
        except Exception as e:
            print(f"[RISK MANAGER] Error loading state: {e}")
    
    def _save_state(self) -> None:
        """Save state to Redis."""
        if not self._redis:
            return
        try:
            self._redis.set(self.REDIS_KEY_STATE, json.dumps(self._state.to_dict()))
        except Exception as e:
            print(f"[RISK MANAGER] Error saving state: {e}")


# =============================================================================
# SINGLETON ACCESSOR
# =============================================================================

_risk_manager_instance: Optional[RiskManager] = None


def get_risk_manager(redis_client: Optional[redis.Redis] = None) -> RiskManager:
    """
    Get or create the singleton Risk Manager instance.
    
    Usage:
        rm = get_risk_manager()
        can_trade, reason = rm.can_open_position(size_usd=100, leverage=5, equity_usd=1000)
    """
    global _risk_manager_instance
    
    if _risk_manager_instance is None:
        # Try to create Redis client if not provided
        if redis_client is None:
            try:
                redis_host = os.getenv("REDIS_HOST", "127.0.0.1")
                redis_port = int(os.getenv("REDIS_PORT", "6379"))
                redis_pass = os.getenv("REDIS_PASS", None)
                redis_client = redis.Redis(
                    host=redis_host,
                    port=redis_port,
                    password=redis_pass,
                    decode_responses=True,
                )
                redis_client.ping()  # Test connection
            except Exception as e:
                print(f"[RISK MANAGER] Redis not available, using in-memory state: {e}")
                redis_client = None
        
        _risk_manager_instance = RiskManager(redis_client)
    
    return _risk_manager_instance


# =============================================================================
# CLI TESTING
# =============================================================================

if __name__ == "__main__":
    print("=" * 60)
    print("GODBRAIN RISK MANAGER TEST")
    print("=" * 60)
    
    rm = get_risk_manager()
    
    # Show current status
    status = rm.get_status()
    print(f"\nCurrent Status:")
    print(f"  Is Halted: {status['is_halted']}")
    print(f"  Daily PnL: ${status['daily_pnl_usd']:.2f}")
    print(f"  Drawdown: {status['drawdown_pct']:.2f}%")
    print(f"  Loss Streak: {status['loss_streak']}")
    print(f"  Open Positions: {status['open_positions']}")
    
    # Test position check
    can_trade, reason = rm.can_open_position(
        size_usd=100,
        leverage=5,
        equity_usd=1000,
    )
    print(f"\nCan Open $100 @ 5x: {can_trade} - {reason}")
    
    # Test leverage limit
    can_trade, reason = rm.can_open_position(
        size_usd=100,
        leverage=15,  # Over limit
        equity_usd=1000,
    )
    print(f"Can Open $100 @ 15x: {can_trade} - {reason}")
    
    print("\n" + "=" * 60)
    print("✅ Risk Manager Test Complete")
