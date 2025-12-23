import asyncio
import aiohttp
import json
import logging
from datetime import datetime
from typing import Dict, List, Optional
from dataclasses import dataclass
from collections import deque

try: import websockets
except ImportError: websockets = None

logging.basicConfig(level=logging.WARNING)
logger = logging.getLogger("DATA_FEEDS")

@dataclass
class TickData:
    timestamp: datetime
    symbol: str
    price: float
    amount: float
    side: str

@dataclass
class LongShortRatio:
    timestamp: datetime
    symbol: str
    long_short_ratio: float
    long_account: float
    short_account: float
    source: str

@dataclass
class FearGreedData:
    timestamp: datetime
    value: int
    classification: str
    previous_value: int
    velocity: float

class OKXTickFeed:
    WS_URL = "wss://ws.okx.com:8443/ws/v5/public"
    def __init__(self, symbols=None):
        self.symbols = symbols or ["BTC-USDT-SWAP"]
        self.callbacks = []
        self.tick_buffer = deque(maxlen=10000)
        self.running = False
    async def start(self):
        if not websockets: return
        self.running = True
        while self.running:
            try:
                async with websockets.connect(self.WS_URL) as ws:
                    for sym in self.symbols:
                        await ws.send(json.dumps({"op": "subscribe", "args": [{"channel": "trades", "instId": sym}]}))
                    async for msg in ws:
                        if not self.running: break
                        d = json.loads(msg)
                        if "data" in d and d.get("arg",{}).get("channel")=="trades":
                            for t in d["data"]:
                                tick = TickData(datetime.now(), t["instId"], float(t["px"]), float(t["sz"]), t["side"])
                                self.tick_buffer.append(tick)
            except: await asyncio.sleep(5)
    def stop(self): self.running = False
    def get_recent_ticks(self, count=100): return list(self.tick_buffer)[-count:]

class LongShortRatioFeed:
    URL = "https://fapi.binance.com/futures/data/globalLongShortAccountRatio"
    def __init__(self): self.cache = {}
    async def fetch_ratio(self, symbol="BTCUSDT"):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(self.URL, params={"symbol": symbol, "period": "5m", "limit": 1}) as r:
                    if r.status == 200:
                        d = await r.json()
                        if d:
                            e = d[0]
                            ratio = LongShortRatio(datetime.now(), symbol, float(e["longShortRatio"]), float(e["longAccount"]), float(e["shortAccount"]), "binance")
                            self.cache[symbol] = ratio
        except: pass
        return self.cache.get(symbol)

class FearGreedFeed:
    URL = "https://api.alternative.me/fng/?limit=2"
    def __init__(self): self.current = None
    async def fetch(self):
        try:
            async with aiohttp.ClientSession() as s:
                async with s.get(self.URL) as r:
                    d = await r.json()
                    if d.get("data"):
                        c, p = d["data"][0], d["data"][1]
                        self.current = FearGreedData(datetime.now(), int(c["value"]), c["value_classification"], int(p["value"]), float(int(c["value"])-int(p["value"])))
        except: pass
        return self.current
    def get_velocity_signal(self):
        if not self.current: return "NEUTRAL"
        v = self.current.velocity
        if v > 5: return "BULLISH_VELOCITY"
        if v < -5: return "BEARISH_VELOCITY"
        return "NEUTRAL"

class LiquidationHeatmapFeed:
    def calculate_heatmap(self, price, oi):
        return {"magnet_direction": "NEUTRAL", "nearest_long_magnet": None, "nearest_short_magnet": None}

class MultiExchangePriceFeed:
    def __init__(self): self.prices = {}
    async def fetch_all(self): pass
    def check_arbitrage(self, threshold=0.01): return None

# THE CRITICAL DATAHUB CLASS
class DataHub:
    def __init__(self):
        self.tick_feed = OKXTickFeed()
        self.ls_ratio_feed = LongShortRatioFeed()
        self.fear_greed_feed = FearGreedFeed()
        self.liq_heatmap = LiquidationHeatmapFeed()
        self.multi_price = MultiExchangePriceFeed()
        self._running = False

    async def start_all_feeds(self):
        self._running = True
        asyncio.create_task(self.tick_feed.start())
        asyncio.create_task(self._periodic_fetcher())
        logger.info("DataHub Started")

    async def _periodic_fetcher(self):
        while self._running:
            try:
                await self.ls_ratio_feed.fetch_ratio("BTCUSDT")
                await self.fear_greed_feed.fetch()
            except: pass
            await asyncio.sleep(60)

    def stop(self):
        self._running = False
        self.tick_feed.stop()
