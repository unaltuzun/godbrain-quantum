import http.server
import socketserver
import json
import socket
import webbrowser
from threading import Thread
import time

PORT = 5000
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 16379
REDIS_PASS = 'voltran2024'

def get_redis_data():
    data = {"price": 0.0, "mode": "WAITING", "action": "LOADING", "confidence": 0}
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect((REDIS_HOST, REDIS_PORT))
        s.sendall(f'AUTH {REDIS_PASS}\r\n'.encode())
        s.recv(1024)
        
        # 1. GET REAL PRICE
        s.sendall(b'GET godbrain:market:ticker\r\n')
        price_resp = s.recv(1024).decode('utf-8', errors='ignore').strip()
        
        # Redis protocol parsing (\r\n90000...)
        if '$' in price_resp:
             lines = price_resp.split('\r\n')
             for i, line in enumerate(lines):
                 if line.startswith('$'):
                     try: data['price'] = float(lines[i+1])
                     except: pass
        
        # 2. GET STRATEGY
        s.sendall(b'GET godbrain:model:linear\r\n')
        strat_resp = s.recv(4096).decode('utf-8', errors='ignore')
        
        if '{' in strat_resp:
            start = strat_resp.find('{')
            end = strat_resp.rfind('}') + 1
            model = json.loads(strat_resp[start:end])
            data['mode'] = model.get('version', 'UNK')
            
            # Recalculate Logic based on REAL PRICE
            m = model.get('slope', 0)
            c = model.get('intercept', 0)
            thr = model.get('threshold', 0.99)
            
            import math
            score = (data['price'] * m) + c
            try: conf = 1 / (1 + math.exp(-score))
            except: conf = 1.0
            
            data['confidence'] = round(conf * 100, 2)
            
            if conf > thr: data['action'] = "SNIPE! [BUY]"
            else: data['action'] = "WAITING..."

        s.close()
    except:
        pass
    return data

# HTML (SAME AS BEFORE)
HTML_PAGE = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>GODBRAIN LIVE | OKX FEED</title>
    <style>
        body { background-color: #0b0c10; color: #66fcf1; font-family: 'Courier New', monospace; margin: 0; padding: 20px; }
        .container { max-width: 1000px; margin: 0 auto; }
        .header { display: flex; justify-content: space-between; border-bottom: 2px solid #45a29e; padding-bottom: 10px; margin-bottom: 20px; }
        .grid { display: grid; grid-template-columns: repeat(2, 1fr); gap: 20px; }
        .card { background: #1f2833; padding: 20px; border-radius: 5px; border: 1px solid #45a29e; }
        .big-text { font-size: 36px; font-weight: bold; color: #fff; }
        .sub-text { font-size: 14px; color: #888; }
        .live-dot { height: 10px; width: 10px; background-color: #f00; border-radius: 50%; display: inline-block; margin-right: 5px; animation: blink 1s infinite; }
        @keyframes blink { 0% { opacity: 1; } 50% { opacity: 0.5; } 100% { opacity: 1; } }
        .action-wait { color: #ebdb34; }
        .action-snipe { color: #f00; text-shadow: 0 0 5px #f00; }
    </style>
    <script>
        function refreshData() {
            fetch('/api/data')
                .then(response => response.json())
                .then(data => {
                    // Update Price
                    document.getElementById('price').innerText = '$' + data.price.toLocaleString('en-US', {minimumFractionDigits: 2});
                    
                    document.getElementById('mode').innerText = data.mode;
                    document.getElementById('confidence').innerText = data.confidence + '%';
                    
                    const actEl = document.getElementById('action');
                    actEl.innerText = data.action;
                    if(data.action.includes('SNIPE')) { actEl.className = 'big-text action-snipe'; } 
                    else { actEl.className = 'big-text action-wait'; }
                });
        }
        setInterval(refreshData, 1000);
    </script>
</head>
<body>
    <div class="container">
        <div class="header">
            <div class="brand">GODBRAIN <span style="color:#fff">LIVE</span></div>
            <div><span class="live-dot"></span>CONNECTED TO OKX</div>
        </div>
        <div class="grid">
            <div class="card">
                <h3>CLOUD STRATEGY</h3>
                <div id="mode" class="big-text">LOADING...</div>
            </div>
            <div class="card">
                <h3>DECISION</h3>
                <div id="action" class="big-text action-wait">...</div>
            </div>
            <div class="card">
                <h3>OKX PRICE (BTC)</h3>
                <div id="price" class="big-text">---</div>
                <div class="sub-text">REAL-TIME FEED</div>
            </div>
            <div class="card">
                <h3>CONFIDENCE</h3>
                <div id="confidence" class="big-text">0.00%</div>
            </div>
        </div>
    </div>
</body>
</html>
"""

class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            self.wfile.write(HTML_PAGE.encode())
        elif self.path == '/api/data':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            data = get_redis_data()
            self.wfile.write(json.dumps(data).encode())

print(f">> DASHBOARD STARTED ON PORT {PORT}")
def open_browser():
    time.sleep(2)
    webbrowser.open(f'http://localhost:{PORT}')
Thread(target=open_browser).start()
with socketserver.TCPServer(("", PORT), RequestHandler) as httpd:
    httpd.serve_forever()
