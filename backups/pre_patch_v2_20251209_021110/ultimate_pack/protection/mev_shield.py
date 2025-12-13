import random
from dataclasses import dataclass

@dataclass
class MEVProtection:
    safe_to_execute: bool
    delay_ms: int
    chunks: int

class MEVShield:
    """
    Protects against Sandwich Attacks and Front-Running by randomizing execution.
    """
    def __init__(self):
        pass
        
    def protect_order(self, size_usd: float) -> MEVProtection:
        # Large orders need splitting
        chunks = 1
        if size_usd > 10000:
            chunks = int(size_usd / 5000)
            
        # Random delay to confuse sniper bots
        delay = random.randint(100, 1500)
        
        return MEVProtection(
            safe_to_execute=True,
            delay_ms=delay,
            chunks=chunks
        )
