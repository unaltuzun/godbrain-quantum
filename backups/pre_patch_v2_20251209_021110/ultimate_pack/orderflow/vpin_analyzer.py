import numpy as np
import pandas as pd
from dataclasses import dataclass
from datetime import datetime
from typing import List, Optional

@dataclass
class VPINSignal:
    timestamp: datetime
    vpin_value: float
    vpin_zscore: float
    toxicity_level: str
    informed_direction: str
    confidence: float
    recommended_action: str

class VPINAnalyzer:
    """
    Volume-Synchronized Probability of Informed Trading (VPIN) Analyzer.
    Detects toxic order flow (Smart Money).
    """
    def __init__(self, bucket_volume_size: float = 1000000.0, window_size: int = 50):
        self.bucket_vol = bucket_volume_size
        self.window = window_size
        self.current_bucket_buy = 0.0
        self.current_bucket_sell = 0.0
        self.buckets = [] # List of (buy_vol, sell_vol) tuples
        self.historical_vpin = []
        
    def process_trade(self, price: float, amount: float, side: str):
        """
        Process a single trade tick. Accumulate into volume buckets.
        """
        vol_usd = price * amount
        
        if side == 'buy':
            self.current_bucket_buy += vol_usd
        else:
            self.current_bucket_sell += vol_usd
            
        total_bucket_vol = self.current_bucket_buy + self.current_bucket_sell
        
        if total_bucket_vol >= self.bucket_vol:
            # Bucket filled
            self.buckets.append((self.current_bucket_buy, self.current_bucket_sell))
            if len(self.buckets) > self.window:
                self.buckets.pop(0)
            
            # Reset bucket (carry over excess logic omitted for simplicity)
            self.current_bucket_buy = 0.0
            self.current_bucket_sell = 0.0
            
            return self._calculate_vpin()
            
        return None # Bucket not full yet

    def _calculate_vpin(self) -> VPINSignal:
        if len(self.buckets) < self.window:
            return None
            
        # VPIN Formula: sum(|V_buy - V_sell|) / (n * V_bucket)
        total_imbalance = sum(abs(b[0] - b[1]) for b in self.buckets)
        total_volume = len(self.buckets) * self.bucket_vol
        
        vpin = total_imbalance / total_volume
        self.historical_vpin.append(vpin)
        
        # Calculate Z-Score
        if len(self.historical_vpin) > 20:
            hist_series = pd.Series(self.historical_vpin[-100:])
            mean = hist_series.mean()
            std = hist_series.std()
            zscore = (vpin - mean) / std if std > 0 else 0
        else:
            zscore = 0
            
        # Classification
        toxicity = "LOW"
        action = "NORMAL"
        
        if vpin > 0.5: toxicity = "EXTREME"
        elif vpin > 0.3: toxicity = "HIGH"
        elif vpin > 0.2: toxicity = "MEDIUM"
        
        # Determine direction of informed trading (last 5 buckets)
        recent_buy = sum(b[0] for b in self.buckets[-5:])
        recent_sell = sum(b[1] for b in self.buckets[-5:])
        direction = "BUYING" if recent_buy > recent_sell else "SELLING"
        
        if toxicity in ["HIGH", "EXTREME"]:
            action = "FOLLOW_SMART_MONEY" if abs(zscore) > 2 else "CAUTION"
            
        return VPINSignal(
            timestamp=datetime.now(),
            vpin_value=vpin,
            vpin_zscore=zscore,
            toxicity_level=toxicity,
            informed_direction=direction,
            confidence=min(1.0, abs(zscore)/3.0),
            recommended_action=action
        )
