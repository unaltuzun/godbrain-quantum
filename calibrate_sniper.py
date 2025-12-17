import socket
import sys
import json

REDIS_HOST = '127.0.0.1'
REDIS_PORT = 16379
REDIS_PASS = 'voltran2024'
KEY_MODEL = 'godbrain:model:linear'
PAYLOAD = '{"slope": 0.0005, "intercept": -48.0, "threshold": 0.95, "version": "v5.1-CALIBRATED"}'

print(">> CALIBRATING SNIPER SCOPE...")

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
        print(">> CALIBRATION COMPLETE.")
        print(">> BIAS SHIFTED: -48.0 (Hard Filter)")
        print(">> STATUS: SNIPER IS NOW PATIENT.")
    else:
        print(f"xx ERROR: {resp}")

except Exception as e:
    print(f"xx CONNECTION ERROR: {e}")
