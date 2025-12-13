from dataclasses import dataclass
from datetime import datetime

@dataclass
class SentimentSignal:
    timestamp: datetime
    score: float
    velocity: float
    signal: str

class SentimentVelocity:
    """
    Tracks the rate of change (velocity) of market sentiment.
    """
    def __init__(self):
        self.history = []
        
    def update(self, current_score: float) -> SentimentSignal:
        self.history.append((datetime.now(), current_score))
        if len(self.history) > 10: self.history.pop(0)
        
        velocity = 0.0
        if len(self.history) > 1:
            # Simple diff
            velocity = self.history[-1][1] - self.history[-2][1]
            
        signal = "NEUTRAL"
        if velocity > 5: signal = "BULLISH_VELOCITY"
        elif velocity < -5: signal = "BEARISH_VELOCITY"
        
        return SentimentSignal(
            timestamp=datetime.now(),
            score=current_score,
            velocity=velocity,
            signal=signal
        )
