"""
GODBRAIN SENSORY INPUT SERVER
Listens for real-time data from Matriks IQ Terminal via TCP Socket

This is the Python side of the Neural Link.
Matriks IQ (C#) sends data -> This server receives and processes it.

Protocol: TCP/IP Socket on localhost:5000
Data Format: JSON {"symbol": "GARAN", "price": 112.5, "time": "14:20:01"}
"""

import socket
import json
import threading
from datetime import datetime
from typing import Callable, Optional
import redis


class MatriksReceiver:
    """
    Receives real-time tick data from Matriks IQ Terminal.
    Can forward data to Redis for GODBRAIN processing or call custom handlers.
    """
    
    def __init__(
        self, 
        host: str = "127.0.0.1", 
        port: int = 5000,
        redis_client: Optional[redis.Redis] = None,
        on_tick: Optional[Callable] = None
    ):
        self.host = host
        self.port = port
        self.redis = redis_client
        self.on_tick = on_tick  # Custom callback for each tick
        self.running = False
        self.socket = None
        self.stats = {
            "ticks_received": 0,
            "errors": 0,
            "start_time": None,
            "last_tick": None
        }
    
    def start(self):
        """Start the receiver server in a background thread."""
        self.running = True
        self.stats["start_time"] = datetime.now()
        
        thread = threading.Thread(target=self._listen, daemon=True)
        thread.start()
        print(f"[MATRIKS] GODBRAIN Cortex listening on {self.host}:{self.port}...")
        return thread
    
    def stop(self):
        """Stop the receiver."""
        self.running = False
        if self.socket:
            self.socket.close()
        print("[MATRIKS] Receiver stopped.")
    
    def _listen(self):
        """Main listening loop - runs in background thread."""
        try:
            with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
                s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
                s.bind((self.host, self.port))
                s.listen()
                s.settimeout(1.0)  # Allow periodic check of self.running
                
                self.socket = s
                
                while self.running:
                    try:
                        conn, addr = s.accept()
                        print(f"[MATRIKS] Connected to Matriks IQ Neural Link: {addr}")
                        self._handle_connection(conn)
                    except socket.timeout:
                        continue  # Check if still running
                    except Exception as e:
                        if self.running:
                            print(f"[MATRIKS] Accept error: {e}")
                            self.stats["errors"] += 1
                            
        except Exception as e:
            print(f"[MATRIKS] Server error: {e}")
            self.stats["errors"] += 1
    
    def _handle_connection(self, conn):
        """Handle incoming data from a connected Matriks client."""
        buffer = ""
        
        with conn:
            while self.running:
                try:
                    data = conn.recv(4096)
                    if not data:
                        break
                    
                    # Handle potential multiple JSON objects in one packet
                    buffer += data.decode('utf-8')
                    
                    # Process complete JSON objects
                    while buffer:
                        try:
                            # Try to parse JSON
                            tick_data = json.loads(buffer)
                            self._process_tick(tick_data)
                            buffer = ""  # Clear buffer after successful parse
                            break
                        except json.JSONDecodeError:
                            # Maybe incomplete data, wait for more
                            break
                            
                except Exception as e:
                    print(f"[MATRIKS] Receive error: {e}")
                    self.stats["errors"] += 1
                    break
    
    def _process_tick(self, tick_data: dict):
        """Process a single tick from Matriks."""
        self.stats["ticks_received"] += 1
        self.stats["last_tick"] = datetime.now()
        
        symbol = tick_data.get("symbol", "UNKNOWN")
        price = tick_data.get("price", 0)
        time = tick_data.get("time", "")
        
        print(f"[TICK] {symbol} = {price} @ {time}")
        
        # Store in Redis if available
        if self.redis:
            try:
                key = f"matriks:tick:{symbol}"
                self.redis.set(key, json.dumps(tick_data))
                self.redis.lpush(f"matriks:history:{symbol}", json.dumps(tick_data))
                self.redis.ltrim(f"matriks:history:{symbol}", 0, 999)  # Keep last 1000
            except Exception as e:
                print(f"[MATRIKS] Redis error: {e}")
        
        # Call custom handler if provided
        if self.on_tick:
            try:
                self.on_tick(tick_data)
            except Exception as e:
                print(f"[MATRIKS] Handler error: {e}")
    
    def get_stats(self) -> dict:
        """Get receiver statistics."""
        return self.stats.copy()


def start_godbrain_listener():
    """Simple standalone listener for testing."""
    print(f"[MATRIKS] GODBRAIN Cortex listening on 127.0.0.1:5000...")
    
    with socket.socket(socket.AF_INET, socket.SOCK_STREAM) as s:
        s.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        s.bind(("127.0.0.1", 5000))
        s.listen()
        
        conn, addr = s.accept()
        with conn:
            print(f"[MATRIKS] Connected to Matriks IQ Neural Link at: {addr}")
            while True:
                data = conn.recv(1024)
                if not data:
                    break
                
                try:
                    raw_msg = data.decode('utf-8')
                    print(f"[INPUT] {raw_msg}")
                except Exception as e:
                    print(f"[ERROR] Decoding error: {e}")


if __name__ == "__main__":
    # Simple test mode
    start_godbrain_listener()
