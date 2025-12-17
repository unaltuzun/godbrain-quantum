# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN Multi-Exchange Data Aggregator
Reads from multiple exchanges and provides consensus signals.
═══════════════════════════════════════════════════════════════════════════════
"""

import asyncio
import logging
from datetime import datetime
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field
import numpy as np

logger = logging.getLogger("godbrain.aggregator")


@dataclass
class ExchangePrice:
    """Price data from an exchange."""
    exchange: str
    symbol: str
    bid: float
    ask: float
    last: float
    volume_24h: float
    timestamp: datetime = field(default_factory=datetime.now)
    
    @property
    def mid(self) -> float:
        return (self.bid + self.ask) / 2
    
    @property
    def spread_pct(self) -> float:
        return (self.ask - self.bid) / self.mid * 100 if self.mid > 0 else 0


@dataclass
class ConsensusSignal:
    """
    Consensus signal from multiple exchanges.
    
    Combines data from all sources to provide:
    - Fair price estimate
    - Confidence level
    - Arbitrage opportunities
    """
    symbol: str
    fair_price: float          # Weighted average price
    price_std: float           # Price deviation across exchanges
    confidence: float          # 0-1, how much exchanges agree
    
    # Individual exchange data
    exchange_prices: Dict[str, float] = field(default_factory=dict)
    
    # Signals
    arbitrage_spread: float = 0.0  # Max spread between exchanges
    best_bid_exchange: str = ""
    best_ask_exchange: str = ""
    
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "symbol": self.symbol,
            "fair_price": self.fair_price,
            "price_std": self.price_std,
            "confidence": self.confidence,
            "exchange_prices": self.exchange_prices,
            "arbitrage_spread": self.arbitrage_spread,
            "best_bid_exchange": self.best_bid_exchange,
            "best_ask_exchange": self.best_ask_exchange,
            "timestamp": self.timestamp.isoformat(),
        }


class MultiExchangeAggregator:
    """
    Multi-exchange data aggregator.
    
    Reads from OKX and Binance, combines data for consensus decisions.
    
    Usage:
        aggregator = MultiExchangeAggregator()
        await aggregator.connect()
        
        # Get consensus price
        signal = await aggregator.get_consensus("BTC/USDT")
        print(f"Fair price: {signal.fair_price}, Confidence: {signal.confidence}")
    """
    
    def __init__(self):
        self.exchanges = {}
        self._connected = False
        
    async def connect(self):
        """Connect to all configured exchanges."""
        try:
            import ccxt.async_support as ccxt
        except ImportError:
            logger.error("ccxt not installed. Run: pip install ccxt")
            return False
        
        from config import OKX_CONFIG, BINANCE_CONFIG
        
        # Connect to OKX
        if OKX_CONFIG.get("api_key"):
            try:
                self.exchanges["okx"] = ccxt.okx({
                    "apiKey": OKX_CONFIG["api_key"],
                    "secret": OKX_CONFIG["secret"],
                    "password": OKX_CONFIG.get("password", ""),
                    "enableRateLimit": True,
                    "options": {"defaultType": "swap"},
                })
                if OKX_CONFIG.get("use_demo"):
                    self.exchanges["okx"].set_sandbox_mode(True)
                logger.info("Connected to OKX")
            except Exception as e:
                logger.warning(f"OKX connection failed: {e}")
        
        # Connect to Binance
        if BINANCE_CONFIG.get("api_key"):
            try:
                self.exchanges["binance"] = ccxt.binance({
                    "apiKey": BINANCE_CONFIG["api_key"],
                    "secret": BINANCE_CONFIG["secret"],
                    "enableRateLimit": True,
                    "options": {"defaultType": "spot"},
                })
                logger.info("Connected to Binance")
            except Exception as e:
                logger.warning(f"Binance connection failed: {e}")
        
        self._connected = len(self.exchanges) > 0
        logger.info(f"Aggregator connected to {len(self.exchanges)} exchanges: {list(self.exchanges.keys())}")
        
        return self._connected
    
    async def close(self):
        """Close all exchange connections."""
        for name, exchange in self.exchanges.items():
            try:
                await exchange.close()
            except:
                pass
        self.exchanges = {}
        self._connected = False
    
    async def fetch_ticker(self, exchange_name: str, symbol: str) -> Optional[ExchangePrice]:
        """Fetch ticker from a single exchange."""
        if exchange_name not in self.exchanges:
            return None
        
        exchange = self.exchanges[exchange_name]
        
        try:
            ticker = await exchange.fetch_ticker(symbol)
            
            return ExchangePrice(
                exchange=exchange_name,
                symbol=symbol,
                bid=ticker.get("bid", 0) or 0,
                ask=ticker.get("ask", 0) or 0,
                last=ticker.get("last", 0) or 0,
                volume_24h=ticker.get("quoteVolume", 0) or 0,
            )
        except Exception as e:
            logger.debug(f"Failed to fetch {symbol} from {exchange_name}: {e}")
            return None
    
    async def fetch_all_tickers(self, symbol: str) -> List[ExchangePrice]:
        """Fetch ticker from all connected exchanges."""
        tasks = [
            self.fetch_ticker(name, symbol)
            for name in self.exchanges.keys()
        ]
        
        results = await asyncio.gather(*tasks, return_exceptions=True)
        
        return [r for r in results if isinstance(r, ExchangePrice)]
    
    async def get_consensus(self, symbol: str) -> ConsensusSignal:
        """
        Get consensus price signal from all exchanges.
        
        Returns:
            ConsensusSignal with fair price and confidence
        """
        tickers = await self.fetch_all_tickers(symbol)
        
        if not tickers:
            return ConsensusSignal(
                symbol=symbol,
                fair_price=0,
                price_std=0,
                confidence=0,
            )
        
        # Calculate weighted average (by volume)
        total_volume = sum(t.volume_24h for t in tickers) or 1
        weighted_price = sum(t.last * t.volume_24h for t in tickers) / total_volume
        
        # Price standard deviation
        prices = [t.last for t in tickers]
        price_std = np.std(prices) if len(prices) > 1 else 0
        
        # Confidence: inversely proportional to price deviation
        # If exchanges agree (low std), confidence is high
        avg_price = np.mean(prices)
        if avg_price > 0:
            relative_std = price_std / avg_price
            confidence = max(0, 1 - relative_std * 100)  # 1% deviation = 0 confidence
        else:
            confidence = 0
        
        # Find arbitrage opportunity
        best_bid = max(tickers, key=lambda t: t.bid)
        best_ask = min(tickers, key=lambda t: t.ask)
        arb_spread = (best_bid.bid - best_ask.ask) / best_ask.ask * 100 if best_ask.ask > 0 else 0
        
        # Build exchange prices dict
        exchange_prices = {t.exchange: t.last for t in tickers}
        
        return ConsensusSignal(
            symbol=symbol,
            fair_price=weighted_price,
            price_std=price_std,
            confidence=confidence,
            exchange_prices=exchange_prices,
            arbitrage_spread=arb_spread,
            best_bid_exchange=best_bid.exchange,
            best_ask_exchange=best_ask.exchange,
        )
    
    async def get_multi_symbol_consensus(self, symbols: List[str]) -> Dict[str, ConsensusSignal]:
        """Get consensus for multiple symbols."""
        tasks = [self.get_consensus(s) for s in symbols]
        results = await asyncio.gather(*tasks)
        return {s.symbol: s for s in results}


# =============================================================================
# CONVENIENCE FUNCTIONS
# =============================================================================

_aggregator: Optional[MultiExchangeAggregator] = None


async def get_aggregator() -> MultiExchangeAggregator:
    """Get or create global aggregator instance."""
    global _aggregator
    if _aggregator is None:
        _aggregator = MultiExchangeAggregator()
        await _aggregator.connect()
    return _aggregator


async def get_consensus_price(symbol: str = "BTC/USDT") -> ConsensusSignal:
    """Quick access to consensus price."""
    agg = await get_aggregator()
    return await agg.get_consensus(symbol)


def get_consensus_price_sync(symbol: str = "BTC/USDT") -> ConsensusSignal:
    """Synchronous wrapper for consensus price."""
    return asyncio.run(get_consensus_price(symbol))


# =============================================================================
# CLI / TEST
# =============================================================================

async def demo():
    """Demo the aggregator."""
    print("=" * 60)
    print("GODBRAIN Multi-Exchange Aggregator Demo")
    print("=" * 60)
    
    aggregator = MultiExchangeAggregator()
    connected = await aggregator.connect()
    
    if not connected:
        print("No exchanges connected!")
        return
    
    print(f"\nConnected to: {list(aggregator.exchanges.keys())}")
    
    symbols = ["BTC/USDT", "ETH/USDT"]
    
    for symbol in symbols:
        print(f"\n--- {symbol} ---")
        signal = await aggregator.get_consensus(symbol)
        
        print(f"  Fair Price: ${signal.fair_price:,.2f}")
        print(f"  Confidence: {signal.confidence:.1%}")
        print(f"  Price StdDev: ${signal.price_std:.2f}")
        
        for ex, price in signal.exchange_prices.items():
            print(f"    {ex}: ${price:,.2f}")
        
        if signal.arbitrage_spread > 0:
            print(f"  ⚡ Arbitrage: {signal.arbitrage_spread:.3f}%")
            print(f"     Buy on {signal.best_ask_exchange}, Sell on {signal.best_bid_exchange}")
    
    await aggregator.close()
    print("\n✅ Demo complete")


if __name__ == "__main__":
    asyncio.run(demo())
