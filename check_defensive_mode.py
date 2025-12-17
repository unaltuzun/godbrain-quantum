import socket
import sys

# CONFIG
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 16379
REDIS_PASS = 'voltran2024'

print(">> CHECKING CLOUD STRATEGY STATUS...")

try:
    s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
    s.settimeout(3.0)
    s.connect((REDIS_HOST, REDIS_PORT))
    
    s.sendall(f'AUTH {REDIS_PASS}\r\n'.encode())
    if "+OK" not in s.recv(1024).decode():
        print("xx AUTH FAILED")
        sys.exit(1)

    s.sendall(b'GET godbrain:model:linear\r\n')
    response = s.recv(4096).decode('utf-8', errors='ignore')
    s.close()
    
    if "DEFENSIVE" in response:
        print(">> STATUS: [SECURE]")
        print(">> MODE:   DEFENSIVE (Confirmed)")
    else:
        print(">> STATUS: [RISK]")
        print(">> MODE:   AGGRESSIVE/UNKNOWN")

except Exception as e:
    print(f"xx CONNECTION ERROR: {e}")
