import numpy as np
import pandas as pd
from enum import Enum
from dataclasses import dataclass
from typing import Dict, List, Optional
from datetime import datetime

class RegimeType(Enum):
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    VOLATILE = "VOLATILE"
    CRISIS = "CRISIS"
    EUPHORIA = "EUPHORIA"
    UNKNOWN = "UNKNOWN"

@dataclass
class RegimeSignal:
    timestamp: datetime
    regime: RegimeType
    confidence: float
    sub_regime: str
    recommended_strategy: str
    position_size_multiplier: float
    stop_loss_multiplier: float
    indicators: Dict[str, float]
    regime_age_minutes: int

class RegimeDetector:
    def __init__(self, lookback_period: int = 100):
        self.lookback = lookback_period
        self.current_regime = RegimeType.UNKNOWN
        self.regime_start_time = datetime.now()
        
    def analyze(self, ohlcv_df: pd.DataFrame) -> RegimeSignal:
        if len(ohlcv_df) < self.lookback:
            return self._default_signal()
            
        df = ohlcv_df.copy()
        
        # Calculate Core Indicators
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(20).std()
        
        # Simple Moving Averages
        df['sma_50'] = df['close'].rolling(50).mean()
        df['sma_200'] = df['close'].rolling(200).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # ADX Approximation (Simplified for standalone)
        df['tr'] = np.maximum(
            df['high'] - df['low'], 
            np.maximum(
                abs(df['high'] - df['close'].shift(1)), 
                abs(df['low'] - df['close'].shift(1))
            )
        )
        df['atr'] = df['tr'].rolling(14).mean()
        # Mock ADX logic: If ATR is rising and trends exist
        adx_proxy = (df['atr'] / df['close']) * 1000  # Normalized ATR score
        
        current = df.iloc[-1]
        
        # Classification Logic
        regime = RegimeType.RANGING
        strategy = "mean_revert"
        pos_mult = 1.0
        sl_mult = 1.0
        confidence = 0.6
        
        # 1. CRISIS Check (High Volatility + Crash)
        if current['volatility'] > df['volatility'].mean() * 3:
            regime = RegimeType.CRISIS
            strategy = "reduce_exposure"
            pos_mult = 0.0
            sl_mult = 0.5
            confidence = 0.9
            
        # 2. EUPHORIA Check
        elif current['rsi'] > 80 and current['close'] > current['sma_50']:
            regime = RegimeType.EUPHORIA
            strategy = "trend_follow_tight_sl"
            pos_mult = 0.5
            sl_mult = 0.8
            confidence = 0.8
            
        # 3. TRENDING Checks
        elif current['close'] > current['sma_50'] and adx_proxy > 15:
            regime = RegimeType.TRENDING_UP
            strategy = "trend_follow"
            pos_mult = 1.5
            sl_mult = 1.2 # Wider SL allowed
            confidence = 0.75
            
        elif current['close'] < current['sma_50'] and adx_proxy > 15:
            regime = RegimeType.TRENDING_DOWN
            strategy = "trend_follow_short"
            pos_mult = 1.5
            sl_mult = 1.2
            confidence = 0.75
            
        # 4. VOLATILE Check
        elif current['volatility'] > df['volatility'].mean() * 1.5:
            regime = RegimeType.VOLATILE
            strategy = "breakout_or_sidelines"
            pos_mult = 0.5
            sl_mult = 1.5
            
        # Update State
        if regime != self.current_regime:
            self.current_regime = regime
            self.regime_start_time = datetime.now()
            
        age_minutes = int((datetime.now() - self.regime_start_time).total_seconds() / 60)
        
        return RegimeSignal(
            timestamp=datetime.now(),
            regime=regime,
            confidence=confidence,
            sub_regime="standard",
            recommended_strategy=strategy,
            position_size_multiplier=pos_mult,
            stop_loss_multiplier=sl_mult,
            indicators={
                "rsi": current['rsi'],
                "volatility": current['volatility'],
                "adx_proxy": adx_proxy
            },
            regime_age_minutes=age_minutes
        )

    def _default_signal(self):
        return RegimeSignal(
            timestamp=datetime.now(),
            regime=RegimeType.UNKNOWN,
            confidence=0.0,
            sub_regime="init",
            recommended_strategy="hold",
            position_size_multiplier=0.0,
            stop_loss_multiplier=1.0,
            indicators={},
            regime_age_minutes=0
        )
