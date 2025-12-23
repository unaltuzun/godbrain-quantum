from dataclasses import dataclass
from datetime import datetime, timedelta
from typing import Optional
from collections import deque
import logging

logger = logging.getLogger("SIGNAL_FILTER")

@dataclass
class FilteredSignal:
    should_execute: bool
    filtered_action: str
    filter_reason: str

class SignalFilter:
    MIN_SECONDS_BETWEEN_TRADES = 120  # 2 mins
    MIN_SECONDS_FOR_REVERSAL = 300    # 5 mins
    MIN_CONVICTION = 0.5
    
    def __init__(self):
        self.last_trade_time = None
        self.last_direction = None

    def filter(self, action: str, conviction: float) -> FilteredSignal:
        action = action.upper()
        if action == "HOLD":
            return FilteredSignal(False, "HOLD", "HOLD_SIGNAL")
            
        now = datetime.now()
        
        # 1. Conviction Check
        if conviction < self.MIN_CONVICTION:
            return FilteredSignal(False, "HOLD", f"LOW_CONVICTION ({conviction:.2f} < {self.MIN_CONVICTION})")

        # 2. Cooldown Check
        if self.last_trade_time:
            diff = (now - self.last_trade_time).total_seconds()
            if diff < self.MIN_SECONDS_BETWEEN_TRADES:
                return FilteredSignal(False, "HOLD", f"COOLDOWN ({int(diff)}s < {self.MIN_SECONDS_BETWEEN_TRADES}s)")
                
        # 3. Reversal Check
        if self.last_direction and action != self.last_direction:
            if self.last_trade_time:
                diff = (now - self.last_trade_time).total_seconds()
                if diff < self.MIN_SECONDS_FOR_REVERSAL:
                    return FilteredSignal(False, "HOLD", f"REVERSAL_PROTECT ({int(diff)}s < {self.MIN_SECONDS_FOR_REVERSAL}s)")

        return FilteredSignal(True, action, "PASS")

    def record_trade(self, direction: str):
        self.last_trade_time = datetime.now()
        self.last_direction = direction.upper()
