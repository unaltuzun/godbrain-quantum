# -*- coding: utf-8 -*-
"""
🐋 WHALE TRACKER - On-Chain Whale Movement Detection
Track large wallet movements across chains.
"""

import os
import json
import asyncio
import aiohttp
from datetime import datetime, timedelta
from typing import List, Dict, Optional
from dataclasses import dataclass, field
from enum import Enum

# API Configuration
ETHERSCAN_API_KEY = os.getenv('ETHERSCAN_API_KEY', '')
BLOCKCHAIN_API_KEY = os.getenv('BLOCKCHAIN_API_KEY', '')


class MovementType(Enum):
    ACCUMULATION = "accumulation"
    DISTRIBUTION = "distribution"
    EXCHANGE_INFLOW = "exchange_inflow"
    EXCHANGE_OUTFLOW = "exchange_outflow"
    TRANSFER = "transfer"


@dataclass
class Wallet:
    address: str
    balance: float
    balance_usd: float
    last_active: datetime
    label: Optional[str] = None
    is_exchange: bool = False


@dataclass
class Movement:
    tx_hash: str
    from_address: str
    to_address: str
    amount: float
    amount_usd: float
    timestamp: datetime
    movement_type: MovementType
    is_whale: bool = False


@dataclass
class WhaleSignal:
    type: MovementType
    symbol: str
    magnitude_usd: float
    confidence: float
    wallets_involved: int
    timestamp: datetime
    direction: str  # 'bullish' or 'bearish'
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "symbol": self.symbol,
            "magnitude_usd": self.magnitude_usd,
            "confidence": self.confidence,
            "wallets_involved": self.wallets_involved,
            "timestamp": self.timestamp.isoformat(),
            "direction": self.direction,
        }


# Known exchange addresses (partial list)
EXCHANGE_ADDRESSES = {
    # Binance
    "0x28c6c06298d514db089934071355e5743bf21d60": "binance",
    "0x21a31ee1afc51d94c2efccaa2092ad1028285549": "binance",
    # Coinbase
    "0x71660c4005ba85c37ccec55d0c4493e66fe775d3": "coinbase",
    # Kraken
    "0x267be1c1d684f78cb4f6a176c4911b741e4ffdc0": "kraken",
    # FTX (historical)
    "0x2faf487a4414fe77e2327f0bf4ae2a264a776ad2": "ftx",
}


class WhaleTracker:
    """
    Track whale wallet movements across chains.
    
    Usage:
        tracker = WhaleTracker(min_whale_usd=1_000_000)
        movements = await tracker.track_movements('ETH', hours=24)
        signal = await tracker.detect_accumulation('BTC')
    """
    
    def __init__(self, min_whale_usd: float = 1_000_000):
        self.min_whale_usd = min_whale_usd
        self.session: Optional[aiohttp.ClientSession] = None
        self._cache: Dict[str, any] = {}
    
    async def _get_session(self) -> aiohttp.ClientSession:
        if self.session is None or self.session.closed:
            self.session = aiohttp.ClientSession()
        return self.session
    
    async def close(self):
        if self.session and not self.session.closed:
            await self.session.close()
    
    async def get_top_wallets(self, symbol: str, n: int = 100) -> List[Wallet]:
        """Get top N whale wallets by balance."""
        wallets = []
        
        if symbol.upper() in ['ETH', 'ERC20']:
            wallets = await self._get_eth_whales(n)
        elif symbol.upper() == 'BTC':
            wallets = await self._get_btc_whales(n)
        
        return wallets
    
    async def _get_eth_whales(self, n: int) -> List[Wallet]:
        """Get top ETH holders from Etherscan."""
        if not ETHERSCAN_API_KEY:
            return self._mock_eth_whales(n)
        
        session = await self._get_session()
        url = f"https://api.etherscan.io/api?module=account&action=listaccounts&apikey={ETHERSCAN_API_KEY}"
        
        try:
            async with session.get(url) as resp:
                data = await resp.json()
                if data.get('status') == '1':
                    accounts = data.get('result', [])[:n]
                    return [
                        Wallet(
                            address=acc['address'],
                            balance=float(acc.get('balance', 0)) / 1e18,
                            balance_usd=float(acc.get('balance', 0)) / 1e18 * 3500,  # ETH price estimate
                            last_active=datetime.now(),
                            is_exchange=acc['address'].lower() in EXCHANGE_ADDRESSES
                        )
                        for acc in accounts
                    ]
        except Exception as e:
            print(f"[WhaleTracker] Etherscan error: {e}")
        
        return self._mock_eth_whales(n)
    
    async def _get_btc_whales(self, n: int) -> List[Wallet]:
        """Get top BTC holders."""
        # BTC whale tracking would use blockchain.com API
        return self._mock_btc_whales(n)
    
    def _mock_eth_whales(self, n: int) -> List[Wallet]:
        """Mock data for testing without API."""
        import random
        return [
            Wallet(
                address=f"0x{''.join(random.choices('0123456789abcdef', k=40))}",
                balance=random.uniform(10000, 500000),
                balance_usd=random.uniform(35_000_000, 1_750_000_000),
                last_active=datetime.now() - timedelta(hours=random.randint(0, 72)),
                is_exchange=random.random() < 0.2
            )
            for _ in range(n)
        ]
    
    def _mock_btc_whales(self, n: int) -> List[Wallet]:
        """Mock BTC whale data."""
        import random
        return [
            Wallet(
                address=f"bc1{''.join(random.choices('023456789acdefghjklmnpqrstuvwxyz', k=38))}",
                balance=random.uniform(1000, 100000),
                balance_usd=random.uniform(100_000_000, 10_000_000_000),
                last_active=datetime.now() - timedelta(hours=random.randint(0, 72)),
                is_exchange=random.random() < 0.15
            )
            for _ in range(n)
        ]
    
    async def track_movements(self, symbol: str, hours: int = 24) -> List[Movement]:
        """Track large movements in the last N hours."""
        movements = []
        
        if symbol.upper() in ['ETH', 'ERC20']:
            movements = await self._track_eth_movements(hours)
        elif symbol.upper() == 'BTC':
            movements = await self._track_btc_movements(hours)
        
        # Filter by whale threshold
        whale_movements = [m for m in movements if m.amount_usd >= self.min_whale_usd]
        return sorted(whale_movements, key=lambda x: x.amount_usd, reverse=True)
    
    async def _track_eth_movements(self, hours: int) -> List[Movement]:
        """Track ETH whale transactions."""
        if not ETHERSCAN_API_KEY:
            return self._mock_movements('ETH', hours)
        
        # Would query Etherscan for large transactions
        # For now, return mock data
        return self._mock_movements('ETH', hours)
    
    async def _track_btc_movements(self, hours: int) -> List[Movement]:
        """Track BTC whale transactions."""
        return self._mock_movements('BTC', hours)
    
    def _mock_movements(self, symbol: str, hours: int) -> List[Movement]:
        """Generate mock movement data."""
        import random
        
        movements = []
        for i in range(random.randint(5, 20)):
            is_exchange_involved = random.random() < 0.4
            to_exchange = random.random() < 0.5 if is_exchange_involved else False
            
            if to_exchange:
                movement_type = MovementType.EXCHANGE_INFLOW
            elif is_exchange_involved:
                movement_type = MovementType.EXCHANGE_OUTFLOW
            else:
                movement_type = random.choice([MovementType.ACCUMULATION, MovementType.DISTRIBUTION, MovementType.TRANSFER])
            
            amount_usd = random.uniform(500_000, 50_000_000)
            
            movements.append(Movement(
                tx_hash=f"0x{''.join(random.choices('0123456789abcdef', k=64))}",
                from_address=f"0x{''.join(random.choices('0123456789abcdef', k=40))}",
                to_address=f"0x{''.join(random.choices('0123456789abcdef', k=40))}",
                amount=amount_usd / (3500 if symbol == 'ETH' else 100000),
                amount_usd=amount_usd,
                timestamp=datetime.now() - timedelta(hours=random.uniform(0, hours)),
                movement_type=movement_type,
                is_whale=amount_usd >= self.min_whale_usd
            ))
        
        return movements
    
    async def detect_accumulation(self, symbol: str) -> Optional[WhaleSignal]:
        """Detect whale accumulation pattern."""
        movements = await self.track_movements(symbol, hours=24)
        
        # Count accumulation vs distribution
        accumulation_usd = sum(
            m.amount_usd for m in movements 
            if m.movement_type in [MovementType.ACCUMULATION, MovementType.EXCHANGE_OUTFLOW]
        )
        distribution_usd = sum(
            m.amount_usd for m in movements 
            if m.movement_type in [MovementType.DISTRIBUTION, MovementType.EXCHANGE_INFLOW]
        )
        
        total = accumulation_usd + distribution_usd
        if total == 0:
            return None
        
        accumulation_ratio = accumulation_usd / total
        
        if accumulation_ratio > 0.6:
            return WhaleSignal(
                type=MovementType.ACCUMULATION,
                symbol=symbol,
                magnitude_usd=accumulation_usd,
                confidence=accumulation_ratio,
                wallets_involved=len(set(m.from_address for m in movements)),
                timestamp=datetime.now(),
                direction='bullish'
            )
        
        return None
    
    async def detect_distribution(self, symbol: str) -> Optional[WhaleSignal]:
        """Detect whale distribution pattern."""
        movements = await self.track_movements(symbol, hours=24)
        
        distribution_usd = sum(
            m.amount_usd for m in movements 
            if m.movement_type in [MovementType.DISTRIBUTION, MovementType.EXCHANGE_INFLOW]
        )
        accumulation_usd = sum(
            m.amount_usd for m in movements 
            if m.movement_type in [MovementType.ACCUMULATION, MovementType.EXCHANGE_OUTFLOW]
        )
        
        total = accumulation_usd + distribution_usd
        if total == 0:
            return None
        
        distribution_ratio = distribution_usd / total
        
        if distribution_ratio > 0.6:
            return WhaleSignal(
                type=MovementType.DISTRIBUTION,
                symbol=symbol,
                magnitude_usd=distribution_usd,
                confidence=distribution_ratio,
                wallets_involved=len(set(m.from_address for m in movements)),
                timestamp=datetime.now(),
                direction='bearish'
            )
        
        return None
    
    async def exchange_flow(self, symbol: str) -> Dict:
        """Get exchange inflow/outflow summary."""
        movements = await self.track_movements(symbol, hours=24)
        
        inflow = sum(m.amount_usd for m in movements if m.movement_type == MovementType.EXCHANGE_INFLOW)
        outflow = sum(m.amount_usd for m in movements if m.movement_type == MovementType.EXCHANGE_OUTFLOW)
        
        net_flow = inflow - outflow
        
        return {
            "symbol": symbol,
            "inflow_usd": inflow,
            "outflow_usd": outflow,
            "net_flow_usd": net_flow,
            "direction": "bearish" if net_flow > 0 else "bullish",
            "timestamp": datetime.now().isoformat()
        }
    
    def get_signal_summary(self, movements: List[Movement]) -> Dict:
        """Generate summary signal from movements."""
        if not movements:
            return {"signal": "neutral", "confidence": 0}
        
        inflow = sum(m.amount_usd for m in movements if m.movement_type == MovementType.EXCHANGE_INFLOW)
        outflow = sum(m.amount_usd for m in movements if m.movement_type == MovementType.EXCHANGE_OUTFLOW)
        
        total = inflow + outflow
        if total == 0:
            return {"signal": "neutral", "confidence": 0}
        
        if outflow > inflow * 1.5:
            return {"signal": "bullish", "confidence": min(1.0, outflow / total)}
        elif inflow > outflow * 1.5:
            return {"signal": "bearish", "confidence": min(1.0, inflow / total)}
        
        return {"signal": "neutral", "confidence": 0.3}


# Convenience function
async def get_whale_signal(symbol: str) -> Optional[WhaleSignal]:
    """Quick whale signal check."""
    tracker = WhaleTracker()
    try:
        acc = await tracker.detect_accumulation(symbol)
        if acc:
            return acc
        dist = await tracker.detect_distribution(symbol)
        return dist
    finally:
        await tracker.close()
