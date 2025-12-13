#!/usr/bin/env python3
import socket
import os

REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", 16379))
REDIS_PASS = os.getenv("REDIS_PASS", "voltran2024")

print(f"Testing Redis connection to {REDIS_HOST}:{REDIS_PORT}")

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(2)
    s.connect((REDIS_HOST, REDIS_PORT))
    print("Connected!")
    
    s.sendall(f'AUTH {REDIS_PASS}\r\n'.encode())
    auth_resp = s.recv(1024).decode()
    print(f"AUTH response: {auth_resp}")
    
    s.sendall(b'PING\r\n')
    ping_resp = s.recv(1024).decode()
    print(f"PING response: {ping_resp}")
    
    s.sendall(b'SET test_key test_value\r\n')
    set_resp = s.recv(1024).decode()
    print(f"SET response: {set_resp}")
    
    s.close()
    print("SUCCESS!")
except Exception as e:
    print(f"ERROR: {e}")

