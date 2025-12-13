import pandas as pd
from datetime import datetime
from abc import ABC, abstractmethod
from typing import Dict

class PriceProvider(ABC):
    @abstractmethod
    def get_price(self, symbol: str, timestamp: datetime) -> float:
        """Returns the price of symbol at (or nearest before) timestamp."""
        raise NotImplementedError

    @abstractmethod
    def load_data(self, source: str):
        raise NotImplementedError

class CsvPriceProvider(PriceProvider):
    def __init__(self):
        self.data: Dict[str, pd.DataFrame] = {}

    def load_data(self, source: str):
        """
        Expects a CSV with columns: timestamp, symbol, price
        """
        print(f"[PRICE] Loading market data from {source}...")
        try:
            df = pd.read_csv(source)
            required = {"timestamp", "symbol", "price"}
            if not required.issubset(df.columns):
                raise ValueError(f"CSV missing columns. Required: {required}")

            df["timestamp"] = pd.to_datetime(df["timestamp"])
            df = df.sort_values("timestamp")

            for sym, group in df.groupby("symbol"):
                self.data[sym] = group.set_index("timestamp").sort_index()

            print(f"[PRICE] Loaded {len(df)} rows for {len(self.data)} symbols.")
        except Exception as e:
            print(f"[PRICE] Error loading CSV: {e}")

    def get_price(self, symbol: str, timestamp: datetime) -> float:
        if symbol not in self.data or self.data[symbol].empty:
            return 0.0

        df = self.data[symbol]
        idx = df.index.asof(timestamp)
        if pd.isna(idx):
            # Çok erken timestamp isteğinde ilk değeri kullan
            return float(df.iloc[0]["price"])
        return float(df.loc[idx]["price"])
