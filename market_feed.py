import time
import json
import socket
import urllib.request
import sys

REDIS_HOST = '127.0.0.1'
REDIS_PORT = 16379
REDIS_PASS = 'voltran2024'
KEY_TICKER = 'godbrain:market:ticker'

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
