#!/usr/bin/env python3
# -*- coding: utf-8 -*-
# =============================================================================
# GODBRAIN QUANTUM LAB - CHRONOS MODULE v2.3 (FIXED)
# PATCH: Safe Orderbook Unpacking for OKX
# =============================================================================

import argparse
import json
import logging
import math
import os
import secrets
import sys
import time
import threading
import queue
import urllib.request
import urllib.error
from datetime import datetime
from pathlib import Path
from typing import Optional, Tuple, List, Dict, Any

import ccxt

try:
    from resonance_bus import ResonanceBus
except ImportError:
    ResonanceBus = None

# --- CONSTANTS ---
HIGH_COHERENCE_THRESHOLD = 0.85
MED_COHERENCE_THRESHOLD = 0.70
LOW_COHERENCE_THRESHOLD = 0.30

# Market Microstructure Weights
SPREAD_THRESHOLD = 0.002
IMBALANCE_THRESHOLD = 0.5
CONCENTRATION_TARGET = 0.3
CLUSTER_THRESHOLD = 0.003
VOL_THRESHOLD = 0.002

# Fusion Weights
W_MICRO = 0.7 
W_SIM = 0.3

# Sub-weights
W_ORDERBOOK = 0.5
W_TRADE = 0.5
W_SPREAD = 0.4
W_IMBALANCE = 0.3
W_CONCENTRATION = 0.3
W_DIRECTION = 0.4
W_CLUSTER = 0.3
W_VOL_SMOOTH = 0.3

EMA_ALPHA = 0.2

# Paths
ROOT = Path("/mnt/c/godbrain-quantum")
LOG_DIR = ROOT / "logs"
NEURAL_STREAM_LOG = LOG_DIR / "neural_stream.log"
CHRONOS_LOG = LOG_DIR / "chronos.log"

# Entropy Source
ENTROPY_API_URL = "https://www.random.org/integers/?num=50&min=0&max=255&col=1&base=10&format=plain&rnd=new"
ENTROPY_FETCH_TIMEOUT = 3.0
ENTROPY_BUFFER_SIZE = 100
ENTROPY_REFILL_THRESHOLD = 20

def clamp01(value: float) -> float:
    return max(0.0, min(1.0, value))

def setup_logging(verbose: bool = False) -> logging.Logger:
    LOG_DIR.mkdir(parents=True, exist_ok=True)
    logger = logging.getLogger("CHRONOS")
    logger.setLevel(logging.DEBUG)
    logger.handlers.clear()
    
    file_handler = logging.FileHandler(CHRONOS_LOG, mode="a", encoding="utf-8")
    file_handler.setLevel(logging.DEBUG)
    file_handler.setFormatter(logging.Formatter("%(asctime)s | %(levelname)-8s | %(message)s", datefmt="%Y-%m-%d %H:%M:%S"))
    logger.addHandler(file_handler)
    
    console_handler = logging.StreamHandler(sys.stdout)
    console_handler.setLevel(logging.DEBUG if verbose else logging.INFO)
    console_handler.setFormatter(logging.Formatter("[CHRONOS] %(message)s"))
    logger.addHandler(console_handler)
    return logger

class EntropyHarvester:
    def __init__(self, logger: logging.Logger):
        self.logger = logger
        self._buffer: queue.Queue = queue.Queue(maxsize=ENTROPY_BUFFER_SIZE)
        self._fetch_lock = threading.Lock()
        self._is_fetching = False
        self._api_failures = 0
        self._api_successes = 0
        self._os_fallbacks = 0
        self._last_source = "INITIALIZING"
        self._seed_buffer_from_os(30)
        self._start_background_fetcher()
        self.logger.info("EntropyHarvester initialized - REALITY LINK ACTIVE")
    
    def _seed_buffer_from_os(self, count):
        for _ in range(count):
            try: self._buffer.put_nowait(secrets.token_bytes(1)[0])
            except queue.Full: break
    
    def _get_os_entropy_float(self):
        return int.from_bytes(secrets.token_bytes(8), 'big') / ((1 << 64) - 1)
    
    def _fetch_from_api(self):
        try:
            req = urllib.request.Request(ENTROPY_API_URL, headers={"User-Agent": "GODBRAIN/2.3"})
            with urllib.request.urlopen(req, timeout=ENTROPY_FETCH_TIMEOUT) as r:
                return [int(line.strip()) for line in r.read().decode().strip().split('\n') if line.strip()]
        except: return []

    def _background_fetch_worker(self):
        while True:
            try:
                if self._buffer.qsize() < ENTROPY_REFILL_THRESHOLD:
                    with self._fetch_lock:
                        if self._is_fetching: 
                            time.sleep(0.5)
                            continue
                        self._is_fetching = True
                    try:
                        vals = self._fetch_from_api()
                        if vals:
                            self._api_successes += 1
                            for v in vals: 
                                try: self._buffer.put_nowait(v)
                                except queue.Full: break
                        else:
                            self._api_failures += 1
                            for _ in range(30):
                                try: self._buffer.put_nowait(secrets.token_bytes(1)[0])
                                except queue.Full: break
                    finally:
                        with self._fetch_lock: self._is_fetching = False
                time.sleep(2.0)
            except: time.sleep(5.0)

    def _start_background_fetcher(self):
        threading.Thread(target=self._background_fetch_worker, daemon=True, name="EntropyFetcher").start()

    def get_entropy(self):
        try:
            val = self._buffer.get_nowait()
            self._last_source = "ATMOSPHERIC_NOISE"
            return val / 255.0
        except queue.Empty:
            self._os_fallbacks += 1
            self._last_source = "OS_ENTROPY_POOL"
            return self._get_os_entropy_float()

    def get_entropy_range(self, low, high):
        return low + self.get_entropy() * (high - low)
        
    def get_stats(self):
        return {
            "buffer": self._buffer.qsize(),
            "api_ok": self._api_successes,
            "source": self._last_source
        }

class MicrostructureEngine:
    def __init__(self, logger):
        self.logger = logger
        self._coherence_micro = 0.5
        self._last_mid = 0.0
    
    def compute(self, order_book, trades, depth):
        score = self._compute_orderbook_score(order_book, depth)
        trade_score = self._compute_trade_score(trades)
        raw = W_ORDERBOOK * score + W_TRADE * trade_score
        self._coherence_micro = EMA_ALPHA * raw + (1.0 - EMA_ALPHA) * self._coherence_micro
        return clamp01(self._coherence_micro)
    
    def _compute_orderbook_score(self, ob, depth):
        bids = ob.get("bids", [])
        asks = ob.get("asks", [])
        if not bids or not asks: return 0.5
        
        # --- FIX: SAFE UNPACKING ---
        try:
            best_bid = float(bids[0][0])
            best_ask = float(asks[0][0])
        except: return 0.5
        
        mid = (best_bid + best_ask) / 2.0
        self._last_mid = mid
        if mid <= 0: return 0.5
        
        spread_score = clamp01(1.0 - ((best_ask - best_bid) / mid / SPREAD_THRESHOLD))
        
        # Calculate Imbalance & Concentration safely
        sum_bids = 0.0
        sum_asks = 0.0
        
        for i in range(min(len(bids), depth)):
            try: sum_bids += float(bids[i][1])
            except: pass
            
        for i in range(min(len(asks), depth)):
            try: sum_asks += float(asks[i][1])
            except: pass
            
        total = sum_bids + sum_asks
        imbalance_score = 0.5
        if total > 0:
            imbalance = (sum_bids - sum_asks) / total
            imbalance_score = 1.0 - clamp01(abs(imbalance) / IMBALANCE_THRESHOLD)
            
        concentration_score = 0.5
        if sum_bids > 0 and sum_asks > 0:
            try:
                # Use index [1] for quantity, safe check
                top_bid_ratio = float(bids[0][1]) / sum_bids
                top_ask_ratio = float(asks[0][1]) / sum_asks
                concentration = (top_bid_ratio + top_ask_ratio) / 2.0
                concentration_score = 1.0 - clamp01(abs(concentration - CONCENTRATION_TARGET) / CONCENTRATION_TARGET)
            except: pass
            
        return clamp01(W_SPREAD * spread_score + W_IMBALANCE * imbalance_score + W_CONCENTRATION * concentration_score)

    def _compute_trade_score(self, trades):
        if not trades: return 0.5
        buys = sum(1 for t in trades if t['side'] == 'buy')
        total = len(trades)
        dir_score = clamp01(4.0 * abs((buys/total) - 0.5)) if total > 0 else 0.5
        
        prices = [t['price'] for t in trades if t['price'] > 0]
        if len(prices) > 1:
            # Simplified Volatility Score
            log_rets = [math.log(prices[i]/prices[i-1]) for i in range(1, len(prices))]
            vol = math.sqrt(sum(r**2 for r in log_rets) / len(log_rets))
            vol_score = clamp01(1.0 - (vol / VOL_THRESHOLD))
        else:
            vol_score = 0.5
            
        return clamp01(W_DIRECTION * dir_score + 0.5 * vol_score + 0.1) # Mixed

    @property
    def coherence(self): return self._coherence_micro

class SimulatedCoherenceEngine:
    def __init__(self, logger, harvester):
        self.harvester = harvester
        self._obs_noise = 0.5
        self._coh = 0.5
        self._phase = 0.0
    
    def tick(self):
        self._obs_noise = clamp01(self._obs_noise + self.harvester.get_entropy_range(-0.05, 0.05))
        self._phase = (self._phase + self.harvester.get_entropy_range(-0.1, 0.1)) % (2*math.pi)
        wave = math.cos(self._phase)**2
        jitter = self.harvester.get_entropy_range(-0.02, 0.02)
        self._coh = clamp01((1.0 - self._obs_noise) * (0.8 + 0.2*wave) + jitter)
        return self._coh

class NeuralStreamWriter:
    def __init__(self, path, logger):
        self.path = path
    def write(self, **kwargs):
        line = f"{datetime.now().strftime('%Y-%m-%d %H:%M:%S')} | CHANNEL:PROMETHEUS_ALERT >>> {json.dumps({'source':'CHRONOS','status':kwargs})}\n"
        try:
            with open(self.path, "a") as f: f.write(line)
        except: pass

class ResonanceBusPublisher:
    def __init__(self, dsn, chan, logger):
        self.bus = None
        if ResonanceBus:
            try: self.bus = ResonanceBus(redis_dsn=dsn, channel=chan)
            except: pass
    def publish(self, **kwargs):
        if self.bus:
            try: self.bus.publish_json(kwargs)
            except: pass

class ChronosController:
    def __init__(self, symbol, logger):
        self.symbol = symbol
        self.logger = logger
        self.ex = ccxt.okx()
        self.harvester = EntropyHarvester(logger)
        self.micro = MicrostructureEngine(logger)
        self.sim = SimulatedCoherenceEngine(logger, self.harvester)
        self.writer = NeuralStreamWriter(NEURAL_STREAM_LOG, logger)
        dsn = os.getenv("GODBRAIN_REDIS_DSN", "redis://127.0.0.1:6379")
        self.pub = ResonanceBusPublisher(dsn, "resonance:chronos", logger)
        
    def tick(self):
        coh_sim = self.sim.tick()
        coh_micro = 0.5
        try:
            ob = self.ex.fetch_order_book(self.symbol, limit=10)
            trades = self.ex.fetch_trades(self.symbol, limit=50)
            coh_micro = self.micro.compute(ob, trades, 10)
        except Exception as e:
            self.logger.warning(f"Market Data Error: {e}")
            
        coh_final = clamp01(W_MICRO * coh_micro + W_SIM * coh_sim)
        
        mode = "STANDARD_FLOW"
        mult = 1.0
        if coh_final > HIGH_COHERENCE_THRESHOLD: mode, mult = "TIME_DILATION_ACTIVE", 2.0
        elif coh_final > MED_COHERENCE_THRESHOLD: mode, mult = "PRECOGNITION_READY", 1.5
        elif coh_final < LOW_COHERENCE_THRESHOLD: mode, mult = "REALITY_COLLAPSE", 0.5
        
        direction = "NEUTRAL"
        if mode == "TIME_DILATION_ACTIVE": direction = "QUANTUM_RESONANCE"
        elif mode == "PRECOGNITION_READY": direction = "COHERENT"
        elif mode == "REALITY_COLLAPSE": direction = "DECOHERENCE"
        
        src = self.harvester.get_stats()['source']
        
        self.writer.write(direction=direction, flow_multiplier=mult, chronos_mode=mode, coherence=coh_final)
        self.pub.publish(mode=direction, energy=coh_final, flow_multiplier=mult, chronos_mode=mode)
        
        return mode, coh_final, coh_micro, coh_sim, mult, src

def main():
    logger = setup_logging()
    logger.info("Chronos v2.3 Starting...")
    try:
        ctrl = ChronosController("BTC/USDT:USDT", logger)
        tick = 0
        while True:
            mode, coh, micro, sim, mult, src = ctrl.tick()
            tick += 1
            logger.info(f"mode={mode} | coh={coh:.4f} (micro={micro:.2f} sim={sim:.2f}) | entropy={src}")
            if tick % 10 == 0:
                stats = ctrl.harvester.get_stats()
                logger.info(f"[ENTROPY] buffer={stats['buffer']} source={stats['source']}")
            time.sleep(5)
    except KeyboardInterrupt:
        sys.exit(0)

if __name__ == "__main__":
    main()
