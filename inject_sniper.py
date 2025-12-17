import socket
import sys
import json

REDIS_HOST = '127.0.0.1'
REDIS_PORT = 16379
REDIS_PASS = 'voltran2024'
KEY_MODEL = 'godbrain:model:linear'

# ESCAPE QUOTES FOR JSON
PAYLOAD = '{"slope": 0.00035, "intercept": -10.0, "threshold": 0.98, "version": "v5.0-SNIPER"}'

print(">> INITIATING STRATEGY UPDATE: SNIPER MODE")

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5.0)
    s.connect((REDIS_HOST, REDIS_PORT))
    
    s.sendall(f'AUTH {REDIS_PASS}\r\n'.encode())
    s.recv(1024)

    # SENDING NEW STRATEGY
    cmd = f"SET {KEY_MODEL} '{PAYLOAD}'\r\n"
    s.sendall(cmd.encode())
    
    resp = s.recv(1024).decode()
    s.close()

    if "+OK" in resp:
        print(">> SUCCESS: CLOUD BRAIN UPDATED.")
        print(">> MODE:    v5.0-SNIPER")
        print(">> STATUS:  READY TO HUNT.")
    else:
        print(f"xx ERROR: {resp}")

except Exception as e:
    print(f"xx CONNECTION ERROR: {e}")
