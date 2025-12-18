# -*- coding: utf-8 -*-
"""
🧠 SMART MONEY TRACKER - Follow the Winners
Track wallets with >60% win rate.
"""

import os
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Tuple
from dataclasses import dataclass, field
import json


@dataclass
class SmartWallet:
    address: str
    win_rate: float
    total_trades: int
    total_pnl_usd: float
    avg_trade_size_usd: float
    last_trade: datetime
    current_positions: List[str] = field(default_factory=list)
    
    @property
    def is_smart(self) -> bool:
        return self.win_rate >= 0.6 and self.total_trades >= 50


@dataclass 
class SmartMoneySignal:
    symbol: str
    sentiment: float  # -1 to 1
    smart_wallets_buying: int
    smart_wallets_selling: int
    total_buy_volume_usd: float
    total_sell_volume_usd: float
    confidence: float
    timestamp: datetime
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "sentiment": self.sentiment,
            "smart_wallets_buying": self.smart_wallets_buying,
            "smart_wallets_selling": self.smart_wallets_selling,
            "total_buy_volume_usd": self.total_buy_volume_usd,
            "total_sell_volume_usd": self.total_sell_volume_usd,
            "confidence": self.confidence,
            "direction": "bullish" if self.sentiment > 0.1 else "bearish" if self.sentiment < -0.1 else "neutral",
            "timestamp": self.timestamp.isoformat()
        }


class SmartMoneyTracker:
    """
    Track wallets with consistent profitability.
    
    Logic:
    - Backtest wallet history to find winners
    - Track their current positions
    - Generate follow signals
    """
    
    def __init__(self, min_winrate: float = 0.6, min_trades: int = 50):
        self.min_winrate = min_winrate
        self.min_trades = min_trades
        self._smart_wallets: List[SmartWallet] = []
        self._last_update: Optional[datetime] = None
    
    async def identify_smart_wallets(self) -> List[SmartWallet]:
        """Identify wallets with high win rates."""
        # In production, would analyze on-chain trade history
        # For now, generate mock smart wallets
        
        if self._smart_wallets and self._last_update:
            if datetime.now() - self._last_update < timedelta(hours=1):
                return self._smart_wallets
        
        self._smart_wallets = self._mock_smart_wallets()
        self._last_update = datetime.now()
        
        return self._smart_wallets
    
    def _mock_smart_wallets(self) -> List[SmartWallet]:
        """Generate mock smart wallet data."""
        import random
        
        wallets = []
        for i in range(100):
            win_rate = random.uniform(0.4, 0.85)
            total_trades = random.randint(20, 500)
            
            if win_rate >= self.min_winrate and total_trades >= self.min_trades:
                wallets.append(SmartWallet(
                    address=f"0x{''.join(random.choices('0123456789abcdef', k=40))}",
                    win_rate=win_rate,
                    total_trades=total_trades,
                    total_pnl_usd=random.uniform(100_000, 10_000_000),
                    avg_trade_size_usd=random.uniform(10_000, 1_000_000),
                    last_trade=datetime.now() - timedelta(hours=random.randint(0, 72)),
                    current_positions=random.sample(['BTC', 'ETH', 'SOL', 'AVAX', 'MATIC'], k=random.randint(1, 3))
                ))
        
        return sorted(wallets, key=lambda x: x.win_rate * x.total_pnl_usd, reverse=True)[:50]
    
    async def track_smart_money_flow(self, symbol: str) -> SmartMoneySignal:
        """Track what smart money is doing with a specific symbol."""
        smart_wallets = await self.identify_smart_wallets()
        
        # Check who's holding this symbol
        wallets_holding = [w for w in smart_wallets if symbol.upper() in w.current_positions]
        
        # Mock recent activity
        import random
        buying_wallets = random.randint(0, len(wallets_holding))
        selling_wallets = len(wallets_holding) - buying_wallets
        
        buy_volume = sum(w.avg_trade_size_usd for w in wallets_holding[:buying_wallets]) if buying_wallets else 0
        sell_volume = sum(w.avg_trade_size_usd for w in wallets_holding[buying_wallets:]) if selling_wallets else 0
        
        total = buy_volume + sell_volume
        sentiment = (buy_volume - sell_volume) / total if total > 0 else 0
        
        confidence = min(1.0, len(wallets_holding) / 10) * abs(sentiment)
        
        return SmartMoneySignal(
            symbol=symbol,
            sentiment=sentiment,
            smart_wallets_buying=buying_wallets,
            smart_wallets_selling=selling_wallets,
            total_buy_volume_usd=buy_volume,
            total_sell_volume_usd=sell_volume,
            confidence=confidence,
            timestamp=datetime.now()
        )
    
    async def copy_trade_signals(self) -> List[Dict]:
        """Generate copy-trade signals from top smart wallets."""
        smart_wallets = await self.identify_smart_wallets()
        
        signals = []
        for wallet in smart_wallets[:10]:  # Top 10 by performance
            for position in wallet.current_positions:
                signals.append({
                    "symbol": position,
                    "wallet_address": wallet.address[:10] + "...",
                    "wallet_win_rate": wallet.win_rate,
                    "wallet_pnl_usd": wallet.total_pnl_usd,
                    "signal": "follow",
                    "confidence": wallet.win_rate
                })
        
        # Aggregate by symbol
        symbol_scores = {}
        for sig in signals:
            sym = sig["symbol"]
            if sym not in symbol_scores:
                symbol_scores[sym] = {"count": 0, "total_confidence": 0}
            symbol_scores[sym]["count"] += 1
            symbol_scores[sym]["total_confidence"] += sig["confidence"]
        
        return [
            {
                "symbol": sym,
                "smart_wallet_count": data["count"],
                "avg_confidence": data["total_confidence"] / data["count"],
                "signal": "strong_buy" if data["count"] >= 5 else "buy"
            }
            for sym, data in sorted(symbol_scores.items(), key=lambda x: x[1]["count"], reverse=True)
        ]
    
    async def smart_money_sentiment(self) -> float:
        """
        Overall smart money sentiment.
        Returns: -1 (very bearish) to 1 (very bullish)
        """
        smart_wallets = await self.identify_smart_wallets()
        
        # Count positions across all smart wallets
        all_positions = []
        for w in smart_wallets:
            all_positions.extend(w.current_positions)
        
        if not all_positions:
            return 0.0
        
        # More positions = more bullish
        avg_positions = len(all_positions) / len(smart_wallets)
        
        # Normalize to -1 to 1 (assume 3 positions is neutral)
        sentiment = (avg_positions - 3) / 3
        return max(-1.0, min(1.0, sentiment))


# Convenience function
async def get_smart_money_signal(symbol: str) -> SmartMoneySignal:
    """Quick smart money signal check."""
    tracker = SmartMoneyTracker()
    return await tracker.track_smart_money_flow(symbol)
