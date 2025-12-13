import time
import json
import socket
import urllib.request
import sys
import os

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not available, use environment variables only

# Load configuration from environment variables (with .env support)
# Bug fix: Safe integer conversion with error handling (consistent with god_dashboard.py)
def safe_int_env(key, default):
    """Safely convert environment variable to integer with fallback to default."""
    try:
        value = os.getenv(key, str(default))
        return int(value)
    except (ValueError, TypeError):
        print(f"[WARNING] Invalid value for {key}, using default: {default}")
        return int(default)

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = safe_int_env("REDIS_PORT", 16379)
REDIS_PASS = os.getenv("REDIS_PASS", "voltran2024")
KEY_TICKER = os.getenv("REDIS_KEY_TICKER", "godbrain:market:ticker")

# OKX API ENDPOINT (PUBLIC)
API_URL = "https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT"

def get_okx_price():
    try:
        with urllib.request.urlopen(API_URL, timeout=2) as url:
            data = json.loads(url.read().decode())
            # Parse Price from OKX JSON structure
            price = data['data'][0]['last']
            return float(price)
    except Exception as e:
        # print(f"API Error: {e}")
        return None

def push_to_redis(price):
    if price is None: return
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect((REDIS_HOST, REDIS_PORT))
        s.sendall(f'AUTH {REDIS_PASS}\r\n'.encode())
        s.recv(1024)
        
        # Write Price to Redis
        cmd = f"SET {KEY_TICKER} {price}\r\n"
        s.sendall(cmd.encode())
        s.close()
        return True
    except:
        return False

print(">> OKX REAL-TIME FEED: STARTED")
print(f">> TARGET: {API_URL}")

while True:
    real_price = get_okx_price()
    
    if real_price:
        success = push_to_redis(real_price)
        timestamp = time.strftime("%H:%M:%S")
        status = "OK" if success else "REDIS FAIL"
        print(f"[{timestamp}] OKX PRICE:  | SYNC: {status}", end='\r')
    else:
        print("Waiting for OKX...", end='\r')
        
    time.sleep(1.0)
