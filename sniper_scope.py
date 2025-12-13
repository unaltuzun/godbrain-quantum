import socket
import json
import time
import random
import math

REDIS_HOST = '127.0.0.1'
REDIS_PORT = 16379
REDIS_PASS = 'voltran2024'
KEY_MODEL = 'godbrain:model:linear'

def get_strategy():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(2.0)
        s.connect((REDIS_HOST, REDIS_PORT))
        s.sendall(f'AUTH {REDIS_PASS}\r\n'.encode())
        s.recv(1024)
        s.sendall(f'GET {KEY_MODEL}\r\n'.encode())
        resp = s.recv(4096).decode('utf-8', errors='ignore')
        s.close()
        
        if '{' in resp:
            start = resp.find('{')
            end = resp.rfind('}') + 1
            return json.loads(resp[start:end])
    except:
        pass
    return {"threshold": 0.99, "version": "OFFLINE"}

def sigmoid(x):
    try: return 1 / (1 + math.exp(-x))
    except: return 0.0 if x < 0 else 1.0

print("----------------------------------------------------------------")
print("GODBRAIN SNIPER SCOPE: ACTIVE")
print("WAITING FOR PERFECT ENTRY SIGNAL...")
print("----------------------------------------------------------------")
print(f"{'TIME':<10} | {'PRICE':<10} | {'SCORE':<10} | {'CONF %':<8} | {'ACTION'}")
print("----------------------------------------------------------------")

btc_price = 98500.0

while True:
    strat = get_strategy()
    ver = strat.get('version', 'UNK')
    thr = strat.get('threshold', 0.99)
    m = strat.get('slope', 0.0)
    c = strat.get('intercept', 0.0)

    # SIMULATE MARKET BOTTOMING OUT
    # Price moves sideways, waiting for breakout
    change = random.uniform(-20, 25)
    btc_price += change
    
    # CALCULATE SCORE
    score = (btc_price * m) + c
    confidence = sigmoid(score)
    
    action = "WAIT..."
    
    # SNIPER LOGIC: ONLY FIRE IF CONFIDENCE > 98%
    if confidence > thr:
        action = "SNIPE! [BUY]"
    
    conf_pct = f"{confidence*100:.2f}%"
    timestamp = time.strftime("%H:%M:%S")

    # ONLY PRINT IF INTERESTING OR EVERY 10 TICKS
    if confidence > 0.6 or random.random() < 0.1:
         print(f"{timestamp:<10} | {btc_price:<10.2f} | {score:<10.4f} | {conf_pct:<8} | {action:<10} (v: {ver})")

    time.sleep(1.0)
