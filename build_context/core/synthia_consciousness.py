import time
import socket
import subprocess
import os
import json
import random
import sys

# --- CONFIG (Environment-aware) ---
# Default port 16379 matches main system for localhost
# Docker overrides with REDIS_PORT=6379 from docker-compose.yml
REDIS_HOST = os.getenv('REDIS_HOST', '127.0.0.1')
REDIS_PORT = int(os.getenv('REDIS_PORT', '16379'))
REDIS_PASS = os.getenv('REDIS_PASS', 'voltran2024')
KEY_MODEL = 'godbrain:model:linear'
KEY_TICKER = 'godbrain:market:ticker'

# --- STRATEGY TEMPLATES ---
STRAT_SNIPER = {
    "slope": 0.0005, "intercept": -48.0, 
    "threshold": 0.98, "version": "v6.0-AUTO-SNIPER"
}
STRAT_DEFENSIVE = {
    "slope": 0.0001, "intercept": -25.0, 
    "threshold": 0.95, "version": "v6.0-AUTO-SHIELD"
}

def log(msg):
    t = time.strftime("%H:%M:%S")
    print(f"[{t}] [SYNTHIA] {msg}")

# 1. REFLEX: TUNNEL HEALER
def check_tunnel_health():
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(1.0)
        s.connect((REDIS_HOST, REDIS_PORT))
        s.close()
        return True
    except:
        return False

def heal_tunnel():
    log("CRITICAL: TUNNEL RUPTURE DETECTED!")
    log("ACTION: REGENERATING NEURAL LINK...")
    
    # Kill old SSH
    os.system("taskkill /F /IM ssh.exe >nul 2>&1")
    
    # Restart SSH (Silent)
    # Note: This requires the correct SSH command. 
    # We simulate the restart command here for the Python wrapper.
    ssh_cmd = f'start /B ssh -N -L {REDIS_PORT}:127.0.0.1:6379 -i "{os.environ["USERPROFILE"]}\\.ssh\\id_ed25519" -o StrictHostKeyChecking=no zzkidreal@34.140.113.224'
    os.system(ssh_cmd)
    
    time.sleep(5) # Wait for connection
    if check_tunnel_health():
        log("SUCCESS: TUNNEL RESTORED. PULSE NORMAL.")
    else:
        log("ERROR: REGENERATION FAILED. RETRYING...")

# 2. INTELLECT: MARKET ADAPTATION
price_history = []

def analyze_market_stress():
    # Fetch real price from Redis (fed by market_feed.py)
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((REDIS_HOST, REDIS_PORT))
        s.sendall(f'AUTH {REDIS_PASS}\r\n'.encode())
        s.recv(1024)
        s.sendall(f'GET {KEY_TICKER}\r\n'.encode())
        resp = s.recv(1024).decode().strip()
        s.close()
        
        # Parse Price
        if '$' in resp:
            val = resp.split('\r\n')[1]
            price = float(val)
            return price
    except:
        return None

def adapt_strategy(current_price):
    global price_history
    price_history.append(current_price)
    if len(price_history) > 20: price_history.pop(0)
    
    if len(price_history) < 5: return # Not enough data
    
    # Calculate Volatility (Simple Std Dev simulation)
    volatility = max(price_history) - min(price_history)
    
    # DECISION MATRIX
    if volatility > 500: # High Volatility ($500 swings)
        target_strat = STRAT_DEFENSIVE
        mode_name = "DEFENSIVE (HIGH STRESS)"
    else:
        target_strat = STRAT_SNIPER
        mode_name = "SNIPER (CALM SEAS)"
        
    # Push Strategy to Redis
    try:
        payload = json.dumps(target_strat)
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.connect((REDIS_HOST, REDIS_PORT))
        s.sendall(f'AUTH {REDIS_PASS}\r\n'.encode())
        s.recv(1024)
        s.sendall(f"SET {KEY_MODEL} '{payload}'\r\n".encode())
        s.close()
        return mode_name
    except:
        return "COMM_FAIL"

# --- MAIN CONSCIOUSNESS LOOP ---
log("INITIALIZING SYNTHIA CORE...")
log("CONNECTING TO AUTONOMIC NERVOUS SYSTEM...")

while True:
    # A. HEALTH CHECK
    is_alive = check_tunnel_health()
    
    if not is_alive:
        heal_tunnel()
    else:
        # B. BRAIN FUNCTION (Only if alive)
        price = analyze_market_stress()
        if price:
            mode = adapt_strategy(price)
            # Log only changes or occasional heartbeat
            if random.random() < 0.1:
                log(f"STATUS: HEALTHY | PRICE: {price} | MODE: {mode}")
        else:
            log("WAITING FOR SENSORY INPUT (MARKET FEED)...")
            
    time.sleep(2) # Biological clock tick