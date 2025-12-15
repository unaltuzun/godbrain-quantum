# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
GODBRAIN Historical Data Downloader
Download OHLCV data from OKX for backtesting.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import sys
import asyncio
import argparse
from pathlib import Path
from datetime import datetime, timedelta
from typing import List, Optional, Tuple

import pandas as pd

# Add project root
ROOT = Path(__file__).parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


class HistoricalDownloader:
    """
    Download historical OHLCV data from OKX.
    
    Usage:
        downloader = HistoricalDownloader()
        df = await downloader.download("DOGE/USDT:USDT", days=365)
        downloader.save_parquet(df, "DOGE_1h")
    """
    
    TIMEFRAME_MAP = {
        "1m": 60,
        "5m": 300,
        "15m": 900,
        "1h": 3600,
        "4h": 14400,
        "1d": 86400,
    }
    
    def __init__(self, data_dir: Optional[Path] = None):
        self.data_dir = data_dir or ROOT / "data" / "historical"
        self.data_dir.mkdir(parents=True, exist_ok=True)
        self._exchange = None
    
    async def _get_exchange(self):
        """Lazy load exchange client."""
        if self._exchange is None:
            try:
                import ccxt.async_support as ccxt_async
                self._exchange = ccxt_async.okx({
                    "enableRateLimit": True,
                    "options": {"defaultType": "swap"},
                })
            except ImportError:
                import ccxt
                self._exchange = ccxt.okx({
                    "enableRateLimit": True,
                    "options": {"defaultType": "swap"},
                })
        return self._exchange
    
    async def download(
        self,
        symbol: str,
        timeframe: str = "1h",
        days: int = 365,
        end_date: Optional[datetime] = None
    ) -> pd.DataFrame:
        """
        Download historical OHLCV data.
        
        Args:
            symbol: Trading pair (e.g., "DOGE/USDT:USDT")
            timeframe: Candle timeframe (1m, 5m, 15m, 1h, 4h, 1d)
            days: Number of days to download
            end_date: End date (default: now)
        
        Returns:
            DataFrame with columns: timestamp, open, high, low, close, volume
        """
        exchange = await self._get_exchange()
        
        end_ts = int((end_date or datetime.now()).timestamp() * 1000)
        start_ts = end_ts - (days * 24 * 60 * 60 * 1000)
        
        all_candles = []
        current_ts = start_ts
        limit = 100  # OKX limit per request
        
        print(f"[DOWNLOAD] {symbol} | {timeframe} | {days} days")
        print(f"[DOWNLOAD] Period: {datetime.fromtimestamp(start_ts/1000)} to {datetime.fromtimestamp(end_ts/1000)}")
        
        request_count = 0
        timeframe_ms = self.TIMEFRAME_MAP.get(timeframe, 3600) * 1000
        
        while current_ts < end_ts:
            try:
                candles = await exchange.fetch_ohlcv(
                    symbol,
                    timeframe,
                    since=current_ts,
                    limit=limit
                )
                
                if not candles:
                    break
                
                all_candles.extend(candles)
                current_ts = candles[-1][0] + timeframe_ms
                request_count += 1
                
                if request_count % 10 == 0:
                    print(f"[DOWNLOAD] Progress: {len(all_candles)} candles...")
                
            except Exception as e:
                print(f"[DOWNLOAD] Error: {e}")
                await asyncio.sleep(1)
                continue
        
        await exchange.close()
        
        if not all_candles:
            print("[DOWNLOAD] No data received")
            return pd.DataFrame()
        
        df = pd.DataFrame(
            all_candles,
            columns=["timestamp", "open", "high", "low", "close", "volume"]
        )
        
        # Convert timestamp to datetime
        df["timestamp"] = pd.to_datetime(df["timestamp"], unit="ms")
        df = df.drop_duplicates(subset=["timestamp"]).sort_values("timestamp")
        df = df.reset_index(drop=True)
        
        print(f"[DOWNLOAD] Complete: {len(df)} candles")
        print(f"[DOWNLOAD] Date range: {df['timestamp'].min()} to {df['timestamp'].max()}")
        
        return df
    
    def save_parquet(self, df: pd.DataFrame, name: str) -> Path:
        """Save DataFrame to Parquet file."""
        path = self.data_dir / f"{name}.parquet"
        df.to_parquet(path, index=False)
        print(f"[SAVE] Saved to {path}")
        return path
    
    def save_csv(self, df: pd.DataFrame, name: str) -> Path:
        """Save DataFrame to CSV file (for backtest compatibility)."""
        # Convert to backtest format: timestamp, symbol, price
        df_out = df[["timestamp", "close"]].copy()
        df_out["symbol"] = name.split("_")[0] + "/USDT:USDT"
        df_out = df_out.rename(columns={"close": "price"})
        df_out = df_out[["timestamp", "symbol", "price"]]
        
        path = self.data_dir / f"{name}.csv"
        df_out.to_csv(path, index=False)
        print(f"[SAVE] Saved to {path}")
        return path
    
    def load_parquet(self, name: str) -> pd.DataFrame:
        """Load DataFrame from Parquet file."""
        path = self.data_dir / f"{name}.parquet"
        if not path.exists():
            raise FileNotFoundError(f"Data file not found: {path}")
        return pd.read_parquet(path)
    
    def list_available(self) -> List[str]:
        """List available historical data files."""
        files = []
        for ext in ["parquet", "csv"]:
            files.extend([f.stem for f in self.data_dir.glob(f"*.{ext}")])
        return sorted(set(files))


async def main():
    """CLI entry point."""
    parser = argparse.ArgumentParser(description="GODBRAIN Historical Data Downloader")
    parser.add_argument("--symbol", default="DOGE/USDT:USDT", help="Trading pair")
    parser.add_argument("--timeframe", default="1h", help="Timeframe (1m,5m,15m,1h,4h,1d)")
    parser.add_argument("--days", type=int, default=365, help="Days of history")
    parser.add_argument("--format", default="both", choices=["parquet", "csv", "both"])
    
    args = parser.parse_args()
    
    downloader = HistoricalDownloader()
    
    # Extract name from symbol
    name = args.symbol.split("/")[0] + "_" + args.timeframe
    
    df = await downloader.download(
        symbol=args.symbol,
        timeframe=args.timeframe,
        days=args.days
    )
    
    if not df.empty:
        if args.format in ["parquet", "both"]:
            downloader.save_parquet(df, name)
        if args.format in ["csv", "both"]:
            downloader.save_csv(df, name)


if __name__ == "__main__":
    asyncio.run(main())
