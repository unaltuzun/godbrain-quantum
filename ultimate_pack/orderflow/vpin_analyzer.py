import numpy as np
import pandas as pd
from dataclasses import dataclass
from datetime import datetime
from collections import deque
import logging

logger = logging.getLogger("VPIN")

@dataclass
class VPINSignal:
    timestamp: datetime
    vpin_value: float
    vpin_zscore: float
    toxicity_level: str
    informed_direction: str
    confidence: float
    alert: bool
    recommended_action: str

class VPINAnalyzer:
    def __init__(self, bucket_volume_usd=500000, window_size=50):
        self.bucket_vol = bucket_volume_usd
        self.window = window_size
        self.current_buy = 0.0
        self.current_sell = 0.0
        self.buckets = deque(maxlen=window_size*2)
        self.vpin_history = deque(maxlen=500)
        self.last_signal = None
        self.callbacks = []

    def register_callback(self, cb):
        self.callbacks.append(cb)

    def process_tick(self, price, amount, side):
        vol = price * amount
        if side == 'buy': self.current_buy += vol
        else: self.current_sell += vol
        
        if (self.current_buy + self.current_sell) >= self.bucket_vol:
            return self._complete_bucket()
        return None

    def _complete_bucket(self):
        self.buckets.append({'buy': self.current_buy, 'sell': self.current_sell})
        self.current_buy = 0
        self.current_sell = 0
        
        if len(self.buckets) >= self.window:
            return self._calc_vpin()
        return None

    def _calc_vpin(self):
        recent = list(self.buckets)[-self.window:]
        total_imbalance = sum(abs(b['buy'] - b['sell']) for b in recent)
        total_vol = len(recent) * self.bucket_vol
        
        vpin = total_imbalance / total_vol if total_vol > 0 else 0
        self.vpin_history.append(vpin)
        
        zscore = 0
        if len(self.vpin_history) > 30:
            arr = np.array(self.vpin_history)
            zscore = (vpin - arr.mean()) / (arr.std() + 1e-6)
            
        toxicity = "LOW"
        if vpin > 0.5: toxicity = "EXTREME"
        elif vpin > 0.3: toxicity = "HIGH"
        elif vpin > 0.2: toxicity = "MEDIUM"
        
        recent_buy = sum(b['buy'] for b in self.buckets)
        recent_sell = sum(b['sell'] for b in self.buckets)
        direction = "BUYING" if recent_buy > recent_sell else "SELLING"
        
        alert = (toxicity in ["HIGH", "EXTREME"])
        action = "FOLLOW_SMART_MONEY" if alert else "NORMAL"
        
        sig = VPINSignal(datetime.now(), vpin, zscore, toxicity, direction, abs(zscore)/3, alert, action)
        self.last_signal = sig
        
        if alert:
            for cb in self.callbacks: cb(sig)
            
        return sig
