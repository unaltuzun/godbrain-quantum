import socket
import json
import time
import random
import sys

# CONFIGURATION
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 16379
REDIS_PASS = 'voltran2024'

# DEFINING THE BAGS (FROM AUDIT REPORT)
# [PAIR, ENTRY_PRICE, SIZE_HELD]
BAGS = [
    {"pair": "BTC/USDT",  "entry": 99500.0, "size": 0.5},
    {"pair": "ETH/USDT",  "entry": 2850.0,  "size": 10.0},
    {"pair": "SOL/USDT",  "entry": 145.0,   "size": 50.0},
    {"pair": "DOGE/USDT", "entry": 0.42,    "size": 10000.0}
]

def get_cloud_strategy():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect((REDIS_HOST, REDIS_PORT))
        s.sendall(f'AUTH {REDIS_PASS}\r\n'.encode())
        s.recv(1024)
        
        s.sendall(b'GET godbrain:model:linear\r\n')
        resp = s.recv(4096).decode('utf-8', errors='ignore')
        s.close()
        
        if 'DEFENSIVE' in resp:
            return 'DEFENSIVE'
        return 'AGGRESSIVE'
    except:
        return 'UNKNOWN'

def run_hedger():
    print(">> STARTING HEDGER CORE...")
    print(">> MODE CHECK: CONNECTING TO CLOUD...")
    
    mode = get_cloud_strategy()
    print(f">> CLOUD STRATEGY: {mode}")
    
    if mode != 'DEFENSIVE':
        print(">> ABORT: DEFENSIVE MODE NOT ACTIVE ON CLOUD.")
        return

    print("----------------------------------------------------------------")
    print(f"{'PAIR':<10} | {'CURRENT':<10} | {'TARGET':<10} | {'ACTION':<10}")
    print("----------------------------------------------------------------")

    # SIMULATION LOOP (STARTING PRICES)
    current_prices = {
        "BTC/USDT": 98450.0,
        "ETH/USDT": 2780.0,
        "SOL/USDT": 138.0,
        "DOGE/USDT": 0.38
    }

    print(">> MONITORING MARKET FOR REBOUNDS...")
    
    while True:
        for bag in BAGS:
            pair = bag['pair']
            entry = bag['entry']
            size = bag['size']
            
            if size <= 0.001:
                continue

            # SIMULATE PRICE MOVEMENT (RANDOM WALK)
            # Market is volatile but trending slightly up for recovery
            change_pct = random.uniform(-0.002, 0.005) 
            current_prices[pair] = current_prices[pair] * (1 + change_pct)
            price = current_prices[pair]

            # LOGIC: EXIT 10% OF BAG IF PRICE RECOVERS TO ENTRY * 0.99 (-1% LOSS)
            # We accept small loss to free up capital.
            target = entry * 0.99
            
            action = "HOLD"
            
            if price >= target:
                sell_amt = size * 0.10 # Sell 10%
                bag['size'] -= sell_amt
                action = f"SELL {sell_amt:.2f}"
                
                # LOG THE SALE
                print(f"{pair:<10} | {price:<10.2f} | {target:<10.2f} | {action:<10} [RECOVERING]")
            
            # UNCOMMENT TO SEE TICKS
            # else:
            #    print(f"{pair:<10} | {price:<10.2f} | {target:<10.2f} | HOLD")

        time.sleep(0.2)

if __name__ == "__main__":
    run_hedger()
