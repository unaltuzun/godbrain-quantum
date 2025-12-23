"""
MATRIKS IQ SIMULATOR
Simulates Matriks IQ sending tick data for testing GODBRAIN receiver.
Use this while waiting for actual Matriks license to activate.

Usage: python matriks/simulator.py
"""

import socket
import json
import time
import random
from datetime import datetime


# Simulated BIST stocks with realistic price ranges
STOCKS = {
    "GARAN": {"base": 112.50, "volatility": 0.5},
    "THYAO": {"base": 285.00, "volatility": 1.2},
    "SISE": {"base": 58.30, "volatility": 0.3},
    "AKBNK": {"base": 65.20, "volatility": 0.4},
    "EREGL": {"base": 52.10, "volatility": 0.25},
    "KCHOL": {"base": 178.50, "volatility": 0.8},
    "TUPRS": {"base": 165.00, "volatility": 0.7},
    "SAHOL": {"base": 82.40, "volatility": 0.35},
}


class MatriksSimulator:
    """Simulates Matriks IQ terminal sending tick data."""
    
    def __init__(self, host: str = "127.0.0.1", port: int = 5000):
        self.host = host
        self.port = port
        self.socket = None
        self.prices = {sym: data["base"] for sym, data in STOCKS.items()}
    
    def connect(self) -> bool:
        """Connect to GODBRAIN receiver."""
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((self.host, self.port))
            print(f"[SIM] Connected to GODBRAIN at {self.host}:{self.port}")
            return True
        except Exception as e:
            print(f"[SIM] Connection failed: {e}")
            print("[SIM] Make sure receiver.py is running first!")
            return False
    
    def disconnect(self):
        """Disconnect from receiver."""
        if self.socket:
            self.socket.close()
            print("[SIM] Disconnected.")
    
    def generate_tick(self, symbol: str) -> dict:
        """Generate a realistic price tick."""
        stock = STOCKS.get(symbol, {"base": 100, "volatility": 0.5})
        
        # Random walk price movement
        change = random.gauss(0, stock["volatility"])
        self.prices[symbol] = max(0.01, self.prices[symbol] + change)
        
        # Simulate volume
        volume = random.randint(100, 10000)
        
        return {
            "symbol": symbol,
            "price": round(self.prices[symbol], 2),
            "time": datetime.now().strftime("%H:%M:%S"),
            "volume": volume
        }
    
    def send_tick(self, tick: dict) -> bool:
        """Send a tick to the receiver."""
        try:
            payload = json.dumps(tick)
            self.socket.send(payload.encode('utf-8'))
            return True
        except Exception as e:
            print(f"[SIM] Send error: {e}")
            return False
    
    def run(self, interval: float = 0.5, symbols: list = None):
        """
        Run the simulator, sending ticks at specified interval.
        
        Args:
            interval: Seconds between ticks
            symbols: List of symbols to simulate (default: all)
        """
        if not self.connect():
            return
        
        symbols = symbols or list(STOCKS.keys())
        print(f"[SIM] Simulating: {', '.join(symbols)}")
        print(f"[SIM] Tick interval: {interval}s")
        print("[SIM] Press Ctrl+C to stop\n")
        
        try:
            tick_count = 0
            while True:
                # Pick a random symbol for this tick
                symbol = random.choice(symbols)
                tick = self.generate_tick(symbol)
                
                if self.send_tick(tick):
                    tick_count += 1
                    if tick_count % 10 == 0:  # Log every 10 ticks
                        print(f"[SIM] Sent {tick_count} ticks... Last: {tick['symbol']} = {tick['price']}")
                else:
                    break
                
                time.sleep(interval)
                
        except KeyboardInterrupt:
            print(f"\n[SIM] Stopped. Total ticks sent: {tick_count}")
        finally:
            self.disconnect()


def main():
    """Run simulator with default settings."""
    print("=" * 50)
    print("MATRIKS IQ SIMULATOR - GODBRAIN TEST MODE")
    print("=" * 50)
    print()
    print("This simulates Matriks IQ sending real-time data.")
    print("Use this to test GODBRAIN without actual Matriks license.")
    print()
    
    sim = MatriksSimulator()
    sim.run(
        interval=0.3,  # Fast for testing
        symbols=["GARAN", "THYAO", "AKBNK", "EREGL"]  # Subset for testing
    )


if __name__ == "__main__":
    main()
