import socket
import sys
import json
import time

REDIS_HOST = '127.0.0.1'
REDIS_PORT = 16379
REDIS_PASS = 'voltran2024'
KEY_MODEL = 'godbrain:model:linear'
PAYLOAD = '{"slope": 0.002, "intercept": -10.0, "threshold": 0.95, "version": "v5.2-MOON-PUMP"}'

print(">> INITIATING ARTIFICIAL PUMP SIGNAL...")

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(5.0)
    s.connect((REDIS_HOST, REDIS_PORT))
    s.sendall(f'AUTH {REDIS_PASS}\r\n'.encode())
    s.recv(1024)

    cmd = f"SET {KEY_MODEL} '{PAYLOAD}'\r\n"
    s.sendall(cmd.encode())
    
    resp = s.recv(1024).decode()
    s.close()

    if "+OK" in resp:
        print(">> PUMP SIGNAL INJECTED!")
        print(">> WATCH THE SNIPER SCOPE NOW!")
        print(">> (Reverting to normal in 10 seconds...)")
    
    # COUNTDOWN
    for i in range(10, 0, -1):
        print(f"pump active: {i}s...", end='\r')
        time.sleep(1)
        
    # REVERT TO CALIBRATED (NORMAL)
    print("\n>> REVERTING TO CALIBRATED STATE...")
    normal_payload = '{"slope": 0.0005, "intercept": -48.0, "threshold": 0.95, "version": "v5.1-CALIBRATED"}'
    
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.connect((REDIS_HOST, REDIS_PORT))
    s.sendall(f'AUTH {REDIS_PASS}\r\n'.encode())
    s.recv(1024)
    s.sendall(f"SET {KEY_MODEL} '{normal_payload}'\r\n".encode())
    s.close()
    print(">> SYSTEM NORMALIZED.")

except Exception as e:
    print(f"xx ERROR: {e}")
