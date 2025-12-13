# ==========================================
# SYNTHIA SRC-1: INJECTOR UPGRADE (RETRY LOGIC)
# ==========================================

$Docs = [Environment]::GetFolderPath("MyDocuments")
$Root = "$Docs\synthia-suite"

Write-Host ">> Injector'a sabırlı olması öğretiliyor..." -ForegroundColor Cyan

$SmartInjector = @"
import socket
import struct
import json
import time
import sys

HOST = '127.0.0.1'
PORT = 9000

def connect_with_retry(host, port, retries=30, delay=2):
    print(f"Connecting to Router at {host}:{port}...")
    for i in range(retries):
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, port))
            print(f"✅ Connected on attempt {i+1}")
            return s
        except ConnectionRefusedError:
            print(f"⏳ Router not ready yet... waiting ({i+1}/{retries})")
            time.sleep(delay)
    return None

def send_pulse():
    # Router'a baglan (Retry mekanizmasi ile)
    s = connect_with_retry(HOST, PORT)
    if not s:
        print("❌ Router is down or compiling too slow. Exiting.")
        sys.exit(1)

    # Payload hazirla
    header = {"msg_id": "test", "priority": 1}
    h_bytes = json.dumps(header).encode('utf-8')
    p_bytes = b'{"amplitude": 0.8}'
    
    total_len = 4 + len(h_bytes) + len(p_bytes)
    
    pkt = struct.pack('>I', total_len) + \
          struct.pack('>I', len(h_bytes)) + \
          h_bytes + \
          p_bytes
          
    print(f"Injecting 1000 pulses...")
    try:
        for i in range(1000):
            s.sendall(pkt)
            time.sleep(0.01) # 10ms delay
            if i % 50 == 0: print(".", end="", flush=True)
    except Exception as e:
        print(f"\nConnection lost: {e}")
    
    print("\nDone.")
    s.close()

if __name__ == "__main__":
    send_pulse()
"@

$SmartInjector | Out-File -Encoding UTF8 "$Root\injector.py"
Write-Host "✅ Injector güncellendi." -ForegroundColor Green
Write-Host "Şimdi '..\start_final.ps1' komutunu tekrar çalıştır." -ForegroundColor Yellow