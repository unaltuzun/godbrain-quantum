import time
import json
import socket
import urllib.request

REDIS_HOST = '127.0.0.1'
REDIS_PORT = 16379
REDIS_PASS = 'voltran2024'

print(">> OKX MARKET FEEDER STARTED")

def push_price(price):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect((REDIS_HOST, REDIS_PORT))
        s.sendall(f'AUTH {REDIS_PASS}\r\n'.encode())
        s.recv(1024)
        s.sendall(f"SET godbrain:market:ticker {price}\r\n".encode())
        s.close()
    except:
        pass

while True:
    try:
        url = "https://www.okx.com/api/v5/market/ticker?instId=BTC-USDT"
        with urllib.request.urlopen(url, timeout=2) as u:
            data = json.loads(u.read().decode())
            price = data['data'][0]['last']
            push_price(price)
            print(f"BTC: ${price}    ", end='\r')
    except:
        pass
    time.sleep(1)