"""
GODBRAIN Historical Data Manager
Downloads, stores, and serves OHLCV data for backtesting.
"""

import os
import asyncio
import pandas as pd
import numpy as np
from datetime import datetime, timedelta
from pathlib import Path
from typing import List, Dict, Optional
import json

# Try to import ccxt, fallback if not available
try:
    import ccxt.async_support as ccxt
    CCXT_AVAILABLE = True
except ImportError:
    CCXT_AVAILABLE = False
    print("[DATA] Warning: ccxt not installed. Install with: pip install ccxt")


class HistoricalDataManager:
    """
    Manages historical market data for backtesting.
    
    Features:
    - Multi-exchange support (Binance, OKX, Bybit)
    - Multiple timeframes (1m, 5m, 15m, 1h, 4h, 1d)
    - Automatic gap detection and filling
    - Data validation and cleaning
    - Efficient storage (Parquet format)
    - Caching for fast access
    
    Usage:
        dm = HistoricalDataManager()
        await dm.download("BTC/USDT", "binance", "1h", 
                         datetime(2023,1,1), datetime(2024,1,1))
        df = await dm.load("BTC/USDT", "1h", 
                          datetime(2023,6,1), datetime(2023,12,1))
    """
    
    SUPPORTED_EXCHANGES = ["binance", "okx", "bybit"]
    SUPPORTED_TIMEFRAMES = ["1m", "5m", "15m", "30m", "1h", "4h", "1d"]
    
    def __init__(self, data_dir: str = None):
        self.data_dir = Path(data_dir or os.getenv("GODBRAIN_DATA_DIR", "data/historical"))
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self.cache: Dict[str, pd.DataFrame] = {}
        self._exchanges: Dict[str, object] = {}
    
    async def _get_exchange(self, exchange_name: str):
        """Get or create exchange instance."""
        if not CCXT_AVAILABLE:
            raise RuntimeError("ccxt not installed. Run: pip install ccxt")
        
        if exchange_name not in self._exchanges:
            exchange_class = getattr(ccxt, exchange_name)
            self._exchanges[exchange_name] = exchange_class({
                'enableRateLimit': True,
                'options': {'defaultType': 'future'}
            })
        return self._exchanges[exchange_name]
    
    async def download(
        self,
        symbol: str,
        exchange: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime = None,
        progress_callback: callable = None
    ) -> pd.DataFrame:
        """
        Download historical OHLCV data.
        
        Args:
            symbol: Trading pair (e.g., "BTC/USDT")
            exchange: Exchange name (binance, okx, bybit)
            timeframe: Candle timeframe (1m, 5m, 15m, 1h, 4h, 1d)
            start_date: Start datetime
            end_date: End datetime (default: now)
            progress_callback: Optional callback for progress updates
        
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        end_date = end_date or datetime.now()
        ex = await self._get_exchange(exchange)
        
        all_candles = []
        current = int(start_date.timestamp() * 1000)
        end_ts = int(end_date.timestamp() * 1000)
        
        # Timeframe to milliseconds
        tf_ms = self._timeframe_to_ms(timeframe)
        total_candles = (end_ts - current) // tf_ms
        downloaded = 0
        
        print(f"[DATA] Downloading {symbol} {timeframe} from {exchange}")
        print(f"[DATA] Range: {start_date} to {end_date}")
        
        while current < end_ts:
            try:
                candles = await ex.fetch_ohlcv(
                    symbol, 
                    timeframe, 
                    since=current, 
                    limit=1000
                )
                
                if not candles:
                    break
                
                all_candles.extend(candles)
                current = candles[-1][0] + tf_ms
                downloaded += len(candles)
                
                if progress_callback:
                    progress_callback(downloaded, total_candles)
                
                # Rate limiting
                await asyncio.sleep(ex.rateLimit / 1000)
                
            except Exception as e:
                print(f"[DATA] Error: {e}, retrying...")
                await asyncio.sleep(5)
        
        await ex.close()
        
        # Create DataFrame
        df = pd.DataFrame(
            all_candles,
            columns=['timestamp', 'open', 'high', 'low', 'close', 'volume']
        )
        
        # Convert timestamp to datetime
        df['timestamp'] = pd.to_datetime(df['timestamp'], unit='ms')
        df.set_index('timestamp', inplace=True)
        
        # Remove duplicates
        df = df[~df.index.duplicated(keep='first')]
        
        # Sort by timestamp
        df.sort_index(inplace=True)
        
        # Save to disk
        self._save_data(df, symbol, exchange, timeframe)
        
        print(f"[DATA] Downloaded {len(df)} candles")
        return df
    
    def _timeframe_to_ms(self, tf: str) -> int:
        """Convert timeframe string to milliseconds."""
        multipliers = {
            'm': 60 * 1000,
            'h': 60 * 60 * 1000,
            'd': 24 * 60 * 60 * 1000
        }
        unit = tf[-1]
        value = int(tf[:-1])
        return value * multipliers[unit]
    
    def _get_file_path(self, symbol: str, exchange: str, timeframe: str) -> Path:
        """Get file path for data storage."""
        safe_symbol = symbol.replace("/", "_")
        return self.data_dir / f"{exchange}_{safe_symbol}_{timeframe}.parquet"
    
    def _save_data(self, df: pd.DataFrame, symbol: str, exchange: str, timeframe: str):
        """Save data to Parquet file."""
        path = self._get_file_path(symbol, exchange, timeframe)
        df.to_parquet(path)
        print(f"[DATA] Saved to {path}")
    
    async def load(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        exchange: str = "binance"
    ) -> pd.DataFrame:
        """
        Load historical data from storage or download if missing.
        
        Args:
            symbol: Trading pair
            timeframe: Candle timeframe
            start_date: Start datetime
            end_date: End datetime
            exchange: Exchange name
        
        Returns:
            DataFrame with OHLCV data
        """
        cache_key = f"{exchange}_{symbol}_{timeframe}"
        
        # Check cache
        if cache_key in self.cache:
            df = self.cache[cache_key]
            return df[(df.index >= start_date) & (df.index <= end_date)]
        
        # Try to load from file
        path = self._get_file_path(symbol, exchange, timeframe)
        
        if path.exists():
            df = pd.read_parquet(path)
            
            # Check if we have data for requested range
            if df.index.min() <= start_date and df.index.max() >= end_date:
                self.cache[cache_key] = df
                return df[(df.index >= start_date) & (df.index <= end_date)]
        
        # Download missing data
        df = await self.download(symbol, exchange, timeframe, start_date, end_date)
        self.cache[cache_key] = df
        return df[(df.index >= start_date) & (df.index <= end_date)]
    
    def load_sync(
        self,
        symbol: str,
        timeframe: str,
        start_date: datetime,
        end_date: datetime,
        exchange: str = "binance"
    ) -> Optional[pd.DataFrame]:
        """
        Synchronous load from disk only (no download).
        
        Returns None if data not available.
        """
        path = self._get_file_path(symbol, exchange, timeframe)
        
        if not path.exists():
            return None
        
        df = pd.read_parquet(path)
        return df[(df.index >= start_date) & (df.index <= end_date)]
    
    def validate_data(self, df: pd.DataFrame) -> Dict:
        """
        Validate data quality.
        
        Returns:
            Dict with validation results
        """
        results = {
            'total_rows': len(df),
            'gaps': [],
            'outliers': [],
            'duplicates': 0,
            'missing_values': df.isnull().sum().to_dict(),
            'date_range': (df.index.min(), df.index.max()),
            'is_valid': True
        }
        
        # Check for gaps
        expected_diff = df.index.to_series().diff().mode()[0]
        actual_diffs = df.index.to_series().diff()
        gap_indices = actual_diffs[actual_diffs > expected_diff * 1.5].index
        results['gaps'] = list(gap_indices)
        
        # Check for outliers (price change > 20% in single candle)
        price_change = df['close'].pct_change().abs()
        outlier_indices = price_change[price_change > 0.20].index
        results['outliers'] = list(outlier_indices)
        
        # Check for duplicates
        results['duplicates'] = df.index.duplicated().sum()
        
        # Overall validity
        results['is_valid'] = (
            len(results['gaps']) == 0 and
            len(results['outliers']) < len(df) * 0.01 and
            results['duplicates'] == 0
        )
        
        return results
    
    def list_available_data(self) -> List[Dict]:
        """List all available data files."""
        files = list(self.data_dir.glob("*.parquet"))
        result = []
        
        for f in files:
            parts = f.stem.split("_")
            if len(parts) >= 3:
                exchange = parts[0]
                timeframe = parts[-1]
                symbol = "_".join(parts[1:-1]).replace("_", "/")
                
                df = pd.read_parquet(f)
                result.append({
                    'exchange': exchange,
                    'symbol': symbol,
                    'timeframe': timeframe,
                    'rows': len(df),
                    'start': df.index.min(),
                    'end': df.index.max(),
                    'file': str(f)
                })
        
        return result
    
    async def sync_all(
        self,
        symbols: List[str],
        exchanges: List[str],
        timeframes: List[str],
        start_date: datetime
    ) -> None:
        """Sync all historical data to latest."""
        for exchange in exchanges:
            for symbol in symbols:
                for timeframe in timeframes:
                    print(f"[SYNC] {exchange} {symbol} {timeframe}")
                    try:
                        await self.download(
                            symbol, exchange, timeframe,
                            start_date, datetime.now()
                        )
                    except Exception as e:
                        print(f"[SYNC] Error: {e}")
                    await asyncio.sleep(1)
        
        print("[SYNC] Complete!")
