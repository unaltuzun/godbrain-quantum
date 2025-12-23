# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
  LIQUIDATION HUNTER v1.0 - THE CHEAT CODE
  ─────────────────────────────────────────────────────────────────────────────
  
  "Hunt where the whales bleed"
  
  Bu modül:
  1. Liquidation seviyelerini tespit eder
  2. Whale pozisyonlarını takip eder  
  3. Stop hunt bölgelerini tahmin eder
  4. Cascade liquidation öncesi pozisyon alır
  
  Author: Azun'el Skywolf
  System: GODBRAIN / GOD FUND
═══════════════════════════════════════════════════════════════════════════════
"""

import ccxt
import pandas as pd
import numpy as np
from datetime import datetime
from dataclasses import dataclass
from typing import List, Dict, Optional, Tuple
import logging
import json
from pathlib import Path

logging.basicConfig(level=logging.INFO, format='[HUNTER] %(asctime)s | %(message)s')
logger = logging.getLogger("LIQUIDATION_HUNTER")

# ═══════════════════════════════════════════════════════════════════════════════
# DATA STRUCTURES
# ═══════════════════════════════════════════════════════════════════════════════

@dataclass
class LiquidationZone:
    """Bir liquidation bölgesi"""
    price: float
    side: str  # "LONG" or "SHORT"
    estimated_size_usd: float
    leverage_estimate: int
    magnetic_strength: float  # 0-1, fiyatı çekme gücü
    distance_pct: float  # Mevcut fiyattan uzaklık %

@dataclass 
class WhaleAlert:
    """Whale hareketi uyarısı"""
    symbol: str
    side: str  # "BUY" or "SELL"
    size_usd: float
    price: float
    timestamp: datetime
    impact_score: float  # 0-1

@dataclass
class HuntSignal:
    """Avlanma sinyali"""
    symbol: str
    action: str  # "LONG_BEFORE_SHORT_SQUEEZE" or "SHORT_BEFORE_LONG_CASCADE"
    target_zone: LiquidationZone
    entry_price: float
    take_profit: float
    stop_loss: float
    confidence: float
    reasoning: str

# ═══════════════════════════════════════════════════════════════════════════════
# LIQUIDATION CALCULATOR
# ═══════════════════════════════════════════════════════════════════════════════

class LiquidationCalculator:
    """
    Liquidation seviyelerini hesaplar.
    
    Formül: Liq Price = Entry * (1 - 1/Leverage) for LONG
            Liq Price = Entry * (1 + 1/Leverage) for SHORT
    """
    
    @staticmethod
    def calc_long_liquidation(entry: float, leverage: int) -> float:
        """Long pozisyon için liquidation fiyatı"""
        return entry * (1 - 1/leverage)
    
    @staticmethod
    def calc_short_liquidation(entry: float, leverage: int) -> float:
        """Short pozisyon için liquidation fiyatı"""
        return entry * (1 + 1/leverage)
    
    @staticmethod
    def estimate_liquidation_zones(
        current_price: float,
        recent_highs: List[float],
        recent_lows: List[float],
        common_leverages: List[int] = [5, 10, 20, 25, 50, 100]
    ) -> List[LiquidationZone]:
        """
        Olası liquidation bölgelerini tahmin et.
        
        Mantık: Trader'lar genellikle recent high/low'larda pozisyon açar
        """
        zones = []
        
        # Long liquidation zones (fiyat düşerse long'lar liq olur)
        for high in recent_highs:
            for lev in common_leverages:
                liq_price = LiquidationCalculator.calc_long_liquidation(high, lev)
                if liq_price < current_price:  # Sadece mevcut fiyatın altındakiler
                    distance = (current_price - liq_price) / current_price * 100
                    if distance < 15:  # %15'ten yakın olanlar
                        zones.append(LiquidationZone(
                            price=liq_price,
                            side="LONG",
                            estimated_size_usd=estimate_cluster_size(lev),
                            leverage_estimate=lev,
                            magnetic_strength=calc_magnetic_strength(distance, lev),
                            distance_pct=distance
                        ))
        
        # Short liquidation zones (fiyat yükselirse short'lar liq olur)
        for low in recent_lows:
            for lev in common_leverages:
                liq_price = LiquidationCalculator.calc_short_liquidation(low, lev)
                if liq_price > current_price:  # Sadece mevcut fiyatın üstündekiler
                    distance = (liq_price - current_price) / current_price * 100
                    if distance < 15:  # %15'ten yakın olanlar
                        zones.append(LiquidationZone(
                            price=liq_price,
                            side="SHORT",
                            estimated_size_usd=estimate_cluster_size(lev),
                            leverage_estimate=lev,
                            magnetic_strength=calc_magnetic_strength(distance, lev),
                            distance_pct=distance
                        ))
        
        # En güçlü mıknatısları önce sırala
        zones.sort(key=lambda z: z.magnetic_strength, reverse=True)
        return zones[:10]  # Top 10

def estimate_cluster_size(leverage: int) -> float:
    """Leverage'a göre tahmini cluster büyüklüğü"""
    # Düşük leverage = daha büyük pozisyonlar
    # Yüksek leverage = daha küçük ama daha çok pozisyon
    base = 1_000_000  # $1M base
    if leverage <= 5:
        return base * 5
    elif leverage <= 10:
        return base * 3
    elif leverage <= 25:
        return base * 2
    else:
        return base * 1

def calc_magnetic_strength(distance_pct: float, leverage: int) -> float:
    """
    Fiyatı çekme gücünü hesapla.
    Yakın + yüksek leverage = güçlü mıknatıs
    """
    distance_score = max(0, 1 - distance_pct / 15)  # %15'te 0, %0'da 1
    leverage_score = min(1, leverage / 50)  # 50x'te max
    return distance_score * 0.6 + leverage_score * 0.4

# ═══════════════════════════════════════════════════════════════════════════════
# WHALE DETECTOR
# ═══════════════════════════════════════════════════════════════════════════════

class WhaleDetector:
    """
    Büyük işlemleri tespit eder.
    """
    
    def __init__(self, exchange: ccxt.Exchange):
        self.exchange = exchange
        self.whale_threshold_usd = 100_000  # $100k+ = whale
        
    def scan_recent_trades(self, symbol: str, limit: int = 100) -> List[WhaleAlert]:
        """Son işlemlerde whale aktivitesi ara"""
        try:
            trades = self.exchange.fetch_trades(symbol, limit=limit)
            alerts = []
            
            for trade in trades:
                size_usd = trade['cost'] if trade['cost'] else trade['amount'] * trade['price']
                
                if size_usd >= self.whale_threshold_usd:
                    alerts.append(WhaleAlert(
                        symbol=symbol,
                        side="BUY" if trade['side'] == 'buy' else "SELL",
                        size_usd=size_usd,
                        price=trade['price'],
                        timestamp=datetime.fromtimestamp(trade['timestamp']/1000),
                        impact_score=min(1, size_usd / 1_000_000)  # $1M = max impact
                    ))
            
            return alerts
        except Exception as e:
            logger.warning(f"Whale scan failed for {symbol}: {e}")
            return []
    
    def analyze_order_book_imbalance(self, symbol: str) -> Tuple[float, str]:
        """
        Order book dengesizliğini analiz et.
        Returns: (imbalance_ratio, dominant_side)
        """
        try:
            orderbook = self.exchange.fetch_order_book(symbol, limit=50)
            
            bid_volume = sum([bid[1] for bid in orderbook['bids'][:20]])
            ask_volume = sum([ask[1] for ask in orderbook['asks'][:20]])
            
            total = bid_volume + ask_volume
            if total == 0:
                return 0.5, "NEUTRAL"
            
            bid_ratio = bid_volume / total
            
            if bid_ratio > 0.6:
                return bid_ratio, "BUY_PRESSURE"
            elif bid_ratio < 0.4:
                return bid_ratio, "SELL_PRESSURE"
            else:
                return bid_ratio, "NEUTRAL"
                
        except Exception as e:
            logger.warning(f"Order book analysis failed: {e}")
            return 0.5, "NEUTRAL"

# ═══════════════════════════════════════════════════════════════════════════════
# FUNDING RATE ANALYZER
# ═══════════════════════════════════════════════════════════════════════════════

class FundingAnalyzer:
    """
    Funding rate analizi - crowd positioning göstergesi
    """
    
    def __init__(self, exchange: ccxt.Exchange):
        self.exchange = exchange
    
    def get_funding_signal(self, symbol: str) -> Tuple[float, str, str]:
        """
        Funding rate'e göre sinyal üret.
        
        Negatif funding = Short'lar fazla = Long aç (short squeeze potansiyeli)
        Pozitif funding = Long'lar fazla = Short aç (long cascade potansiyeli)
        
        Returns: (funding_rate, signal, reasoning)
        """
        try:
            funding = self.exchange.fetch_funding_rate(symbol)
            rate = funding['fundingRate'] * 100  # Yüzde olarak
            
            if rate < -0.03:  # -%0.03'ten düşük
                return rate, "STRONG_LONG", "Extreme negative funding - short squeeze imminent"
            elif rate < -0.01:
                return rate, "LONG", "Negative funding - shorts overcrowded"
            elif rate > 0.03:
                return rate, "STRONG_SHORT", "Extreme positive funding - long cascade imminent"
            elif rate > 0.01:
                return rate, "SHORT", "Positive funding - longs overcrowded"
            else:
                return rate, "NEUTRAL", "Balanced funding"
                
        except Exception as e:
            logger.warning(f"Funding analysis failed: {e}")
            return 0, "NEUTRAL", "Unable to fetch funding"

# ═══════════════════════════════════════════════════════════════════════════════
# LIQUIDATION HUNTER ENGINE
# ═══════════════════════════════════════════════════════════════════════════════

class LiquidationHunter:
    """
    Ana avlanma motoru.
    
    Tüm sinyalleri birleştirip optimal entry/exit hesaplar.
    """
    
    def __init__(self, api_key: str = None, secret: str = None, password: str = None):
        self.exchange = ccxt.okx({
            'apiKey': api_key,
            'secret': secret,
            'password': password
        }) if api_key else ccxt.okx()
        
        self.whale_detector = WhaleDetector(self.exchange)
        self.funding_analyzer = FundingAnalyzer(self.exchange)
        self.calculator = LiquidationCalculator()
        
    def analyze_symbol(self, symbol: str) -> Optional[HuntSignal]:
        """Tek bir sembol için avlanma analizi yap"""
        try:
            # 1. OHLCV verisi al
            ohlcv = self.exchange.fetch_ohlcv(symbol, '1h', limit=100)
            df = pd.DataFrame(ohlcv, columns=['ts', 'open', 'high', 'low', 'close', 'vol'])
            
            current_price = df['close'].iloc[-1]
            recent_highs = df['high'].nlargest(10).tolist()
            recent_lows = df['low'].nsmallest(10).tolist()
            
            # 2. Liquidation bölgelerini hesapla
            liq_zones = self.calculator.estimate_liquidation_zones(
                current_price, recent_highs, recent_lows
            )
            
            if not liq_zones:
                return None
            
            # 3. Funding rate analizi
            funding_rate, funding_signal, funding_reason = self.funding_analyzer.get_funding_signal(symbol)
            
            # 4. Order book imbalance
            imbalance, pressure = self.whale_detector.analyze_order_book_imbalance(symbol)
            
            # 5. En güçlü zone'u seç
            best_zone = liq_zones[0]
            
            # 6. Sinyal oluştur
            confidence = best_zone.magnetic_strength
            
            # Funding ile uyum kontrolü
            if best_zone.side == "LONG" and funding_signal in ["LONG", "STRONG_LONG"]:
                # Short squeeze potansiyeli - LONG aç
                action = "LONG_BEFORE_SHORT_SQUEEZE"
                confidence *= 1.3
                tp_mult = 1.02  # %2 TP
                sl_mult = 0.985  # %1.5 SL
            elif best_zone.side == "SHORT" and funding_signal in ["SHORT", "STRONG_SHORT"]:
                # Long cascade potansiyeli - SHORT aç
                action = "SHORT_BEFORE_LONG_CASCADE"
                confidence *= 1.3
                tp_mult = 0.98
                sl_mult = 1.015
            else:
                # Uyumsuz - düşük confidence
                action = f"WATCH_{best_zone.side}_ZONE"
                confidence *= 0.5
                tp_mult = 1.015 if "LONG" in action else 0.985
                sl_mult = 0.99 if "LONG" in action else 1.01
            
            # Order book pressure ile uyum
            if pressure == "BUY_PRESSURE" and "LONG" in action:
                confidence *= 1.1
            elif pressure == "SELL_PRESSURE" and "SHORT" in action:
                confidence *= 1.1
            
            confidence = min(0.95, confidence)
            
            return HuntSignal(
                symbol=symbol,
                action=action,
                target_zone=best_zone,
                entry_price=current_price,
                take_profit=current_price * tp_mult,
                stop_loss=current_price * sl_mult,
                confidence=confidence,
                reasoning=f"Zone: ${best_zone.price:.2f} ({best_zone.side} liq at {best_zone.leverage_estimate}x) | {funding_reason} | {pressure}"
            )
            
        except Exception as e:
            logger.error(f"Analysis failed for {symbol}: {e}")
            return None
    
    def hunt(self, symbols: List[str] = None) -> List[HuntSignal]:
        """Tüm semboller için avlan"""
        if symbols is None:
            symbols = [
                "BTC/USDT:USDT", "ETH/USDT:USDT", "SOL/USDT:USDT",
                "XRP/USDT:USDT", "DOGE/USDT:USDT", "PEPE/USDT:USDT"
            ]
        
        signals = []
        for symbol in symbols:
            logger.info(f"🎯 Hunting {symbol}...")
            signal = self.analyze_symbol(symbol)
            if signal and signal.confidence >= 0.5:
                signals.append(signal)
                logger.info(f"   ✅ {signal.action} | Conf: {signal.confidence:.2f} | {signal.reasoning}")
            else:
                logger.info(f"   ⚪ No opportunity")
        
        # En yüksek confidence'a göre sırala
        signals.sort(key=lambda s: s.confidence, reverse=True)
        return signals
    
    def print_report(self, signals: List[HuntSignal]):
        """Avlanma raporu yazdır"""
        print("\n" + "=" * 70)
        print("  🎯 LIQUIDATION HUNTER REPORT")
        print("=" * 70)
        
        if not signals:
            print("  No hunting opportunities found.")
            return
        
        for i, sig in enumerate(signals, 1):
            print(f"\n  #{i} {sig.symbol}")
            print(f"      Action: {sig.action}")
            print(f"      Confidence: {sig.confidence:.2%}")
            print(f"      Entry: ${sig.entry_price:.4f}")
            print(f"      TP: ${sig.take_profit:.4f} | SL: ${sig.stop_loss:.4f}")
            print(f"      Zone: ${sig.target_zone.price:.4f} ({sig.target_zone.side} liq)")
            print(f"      Reasoning: {sig.reasoning}")
        
        print("\n" + "=" * 70)


# ═══════════════════════════════════════════════════════════════════════════════
# MAIN
# ═══════════════════════════════════════════════════════════════════════════════

if __name__ == "__main__":
    import os
    from dotenv import load_dotenv
    
    load_dotenv("/mnt/c/godbrain-quantum/.env")
    
    hunter = LiquidationHunter(
        api_key=os.getenv("OKX_API_KEY"),
        secret=os.getenv("OKX_SECRET"),
        password=os.getenv("OKX_PASSWORD")
    )
    
    # Avlan!
    signals = hunter.hunt([
        "BTC/USDT:USDT",
        "ETH/USDT:USDT", 
        "SOL/USDT:USDT",
        "XRP/USDT:USDT",
        "DOGE/USDT:USDT",
        "PEPE/USDT:USDT",
        "WIF/USDT:USDT",
        "BONK/USDT:USDT"
    ])
    
    hunter.print_report(signals)
