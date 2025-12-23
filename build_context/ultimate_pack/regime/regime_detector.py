import numpy as np
import pandas as pd
from enum import Enum
from dataclasses import dataclass
from typing import Dict
from datetime import datetime, timedelta

class RegimeType(Enum):
    TRENDING_UP = "TRENDING_UP"
    TRENDING_DOWN = "TRENDING_DOWN"
    RANGING = "RANGING"
    VOLATILE = "VOLATILE"
    CRISIS = "CRISIS"
    EUPHORIA = "EUPHORIA"
    UNKNOWN = "UNKNOWN"
    HOLD = "HOLD"

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
        # Anti-Whipsaw Config
        self.COOLDOWN_SEC = 600 # 5 min
        
    def analyze(self, ohlcv_df: pd.DataFrame) -> RegimeSignal:
        if ohlcv_df.empty or len(ohlcv_df) < 20:
            return self._default_signal()
            
        df = ohlcv_df.copy()
        for col in ['open','high','low','close','vol']:
            if col in df.columns: df[col] = pd.to_numeric(df[col], errors='coerce')
        df.dropna(inplace=True)

        # Indicators
        df['returns'] = df['close'].pct_change()
        df['volatility'] = df['returns'].rolling(20).std()
        df['sma_50'] = df['close'].rolling(50).mean()
        
        # RSI
        delta = df['close'].diff()
        gain = (delta.where(delta > 0, 0)).rolling(14).mean()
        loss = (-delta.where(delta < 0, 0)).rolling(14).mean()
        rs = gain / loss
        df['rsi'] = 100 - (100 / (1 + rs))
        
        # ATR Proxy
        df['tr'] = df['high'] - df['low']
        df['atr'] = df['tr'].rolling(14).mean()
        
        try:
            curr = df.iloc[-1]
            close = float(curr['close'])
            vol = float(curr['volatility']) if not pd.isna(curr['volatility']) else 0.0
            mean_vol = float(df['volatility'].mean()) if not pd.isna(df['volatility'].mean()) else 0.0
            rsi = float(curr['rsi']) if not pd.isna(curr['rsi']) else 50.0
            sma = float(curr['sma_50']) if not pd.isna(curr['sma_50']) else close
            atr = float(curr['atr']) if not pd.isna(curr['atr']) else 0.0
        except: return self._default_signal()

        # Classification Logic
        regime = RegimeType.RANGING
        strategy = "mean_revert"
        pos_mult = 1.0
        confidence = 0.5
        
        if vol > mean_vol * 3 and mean_vol > 0:
            regime = RegimeType.CRISIS
            strategy = "reduce_exposure"
            pos_mult = 0.0
            confidence = 0.9
        elif rsi > 80 and close > sma:
            regime = RegimeType.EUPHORIA
            strategy = "trend_follow_tight_sl"
            pos_mult = 0.5
            confidence = 0.8
        elif close > sma:
            regime = RegimeType.TRENDING_UP
            strategy = "trend_follow"
            pos_mult = 1.5
            confidence = 0.75
        elif close < sma:
            regime = RegimeType.TRENDING_DOWN
            strategy = "trend_follow_short"
            pos_mult = 1.5
            confidence = 0.75

        # Anti-Whipsaw: Cooldown Logic
        time_diff = (datetime.now() - self.regime_start_time).total_seconds()
        if regime != self.current_regime:
            if time_diff < self.COOLDOWN_SEC and regime != RegimeType.CRISIS and self.current_regime != RegimeType.UNKNOWN:
                # Force stick to old regime if cooldown active
                regime = self.current_regime
                confidence *= 0.5
            else:
                self.current_regime = regime
                self.regime_start_time = datetime.now()

        return RegimeSignal(
            timestamp=datetime.now(),
            regime=regime,
            confidence=confidence,
            sub_regime="standard",
            recommended_strategy=strategy,
            position_size_multiplier=pos_mult,
            stop_loss_multiplier=1.0,
            indicators={"rsi": rsi, "vol": vol},
            regime_age_minutes=int(time_diff/60)
        )

    def _default_signal(self):
        return RegimeSignal(datetime.now(), RegimeType.UNKNOWN, 0.0, "init", "hold", 0.0, 1.0, {}, 0)
