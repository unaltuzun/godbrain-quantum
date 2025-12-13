import http.server
import socketserver
import json
import socket
import os
import sys
import threading
import time
import requests

# ==============================================================================
# 🔑 GÜVENLİK BÖLÜMÜ (BULLETPROOF KEY LOADING)
# ==============================================================================
RAW_KEY = "sk-ant-api03-tJhQHJe5qFk2oi5f2RkoJRikkcNEjOWj6S9tPYgvF26f87LcCCcIJAX-Sz_1kFpKBJkya5M9u"

def get_clean_key():
    """
    Anahtarı atomlarına ayırıp görünmez karakterlerden (BOM, Zero-width space) temizler.
    """
    k = RAW_KEY
    # 1. Standart boşlukları sil
    k = k.strip()
    # 2. Windows BOM karakterini sil (\ufeff)
    k = k.replace('\ufeff', '')
    # 3. Görünmez boşlukları sil
    k = k.replace('\u200b', '')
    # 4. Tırnak işaretlerini sil (varsa)
    k = k.replace('"', '').replace("'", "")
    return k

API_KEY = get_clean_key()
# ==============================================================================

PORT = 8000
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 16379
REDIS_PASS = 'voltran2024'

# --- REDIS CLIENT ---
def redis_cmd(cmd):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect((REDIS_HOST, REDIS_PORT))
        s.sendall(f'AUTH {REDIS_PASS}\r\n'.encode())
        s.recv(1024)
        s.sendall(f"{cmd}\r\n".encode())
        resp = s.recv(4096).decode('utf-8', errors='ignore')
        s.close()
        return resp.strip()
    except:
        return None

def get_system_state():
    price = redis_cmd("GET godbrain:market:ticker")
    model = redis_cmd("GET godbrain:model:linear")
    
    p_val = "0"
    if price and '$' in price: 
        try: p_val = price.split('\r\n')[1]
        except: pass
        
    m_val = "OFFLINE"
    if model and '{' in model:
        start = model.find('{')
        end = model.rfind('}') + 1
        m_val = model[start:end]
        
    return {"price": float(p_val) if p_val != "0" else 0, "strategy": m_val}

# --- SERAPH BRAIN (EVOLVED) ---
def ask_seraph(user_input):
    state = get_system_state()
    context = f"PRICE: ${state['price']} | STRATEGY: {state['strategy']}"
    
    headers = {
        "x-api-key": API_KEY,
        "anthropic-version": "2023-06-01",
        "content-type": "application/json"
    }
    
    # SYSTEM PROMPT (MASTER CONTROL)
    sys_msg = """You are SERAPH, the Autonomous Core of GODBRAIN.
    You have DIRECT WRITE ACCESS to the trading engine.
    
    Current Context:
    """ + context + """
    
    INSTRUCTIONS:
    1. If user asks for analysis, provide brief technical insight.
    2. If user commands a strategy change (e.g., "Activate Sniper"), output JSON:
       {"actions": [{"cmd": "SET", "key": "godbrain:model:linear", "value": "{\"version\": \"SERAPH-SNIPER\", \"threshold\": 0.98}"}]}
    3. If panic requested, output JSON to stop system.
    """
    
    data = {
        "model": "claude-3-5-sonnet-20240620",
        "max_tokens": 512,
        "system": sys_msg,
        "messages": [{"role": "user", "content": user_input}]
    }
    
    try:
        r = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=data, timeout=15)
        
        if r.status_code == 200:
            content = r.json()['content'][0]['text']
            
            # --- CEREBRO: ACTION EXECUTOR ---
            if '{"actions":' in content:
                try:
                    # Basit JSON ayıklama
                    json_part = content[content.find('{'):content.rfind('}')+1]
                    cmd_data = json.loads(json_part)
                    actions = cmd_data.get('actions', [])
                    
                    logs = []
                    for action in actions:
                        if action['cmd'] == 'SET':
                            res = redis_cmd(f"SET {action['key']} '{action['value']}'")
                            logs.append(f"EXEC: {action['key']} -> OK")
                    
                    return f"{content}\n\n[SYSTEM LOG]: {', '.join(logs)}"
                except Exception as e:
                    return f"{content}\n\n[EXEC ERROR]: {e}"
            
            return content
        else:
            return f"API ERROR ({r.status_code}): {r.text}"
    except Exception as e:
        return f"CONNECTION ERROR: {e}"

# --- WEB SERVER ---
class ThreadedHTTPServer(socketserver.ThreadingMixIn, socketserver.TCPServer):
    daemon_threads = True

class RequestHandler(http.server.SimpleHTTPRequestHandler):
    def do_GET(self):
        if self.path == '/':
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>GODBRAIN QUANTUM</title>
    <style>
        body { background: #000; color: #0f0; font-family: 'Courier New', monospace; display: flex; height: 100vh; margin:0; overflow:hidden; }
        .sidebar { width: 300px; padding: 20px; border-right: 1px solid #333; background: #050505; }
        .metric { font-size: 24px; font-weight: bold; color: #fff; margin-bottom: 20px; }
        .main { flex: 1; display: flex; flex-direction: column; }
        .chat-box { flex: 1; padding: 20px; overflow-y: auto; display:flex; flex-direction:column; gap:10px; }
        .msg { padding:10px; border-radius:4px; max-width:85%; line-height: 1.4; }
        .msg.user { align-self:flex-end; background:#222; color:#ccc; border: 1px solid #444; }
        .msg.ai { align-self:flex-start; background:#001100; color:#0f0; border: 1px solid #004400; }
        .input-area { padding: 20px; border-top: 1px solid #333; background: #050505; }
        input { width: 100%; background: #000; border: 1px solid #333; color: #fff; padding: 12px; font-family: inherit; font-size: 16px; outline: none; }
        input:focus { border-color: #0f0; }
    </style>
</head>
<body>
    <div class="sidebar">
        <h2 style="border-bottom: 2px solid #0f0; padding-bottom:10px">GODBRAIN<br><span style="font-size:12px">QUANTUM CORE</span></h2>
        <br>
        <div style="color:#666; font-size:12px">MARKET PRICE</div>
        <div id="price" class="metric">LOADING...</div>
        <div style="color:#666; font-size:12px">ACTIVE STRATEGY</div>
        <div id="mode" class="metric" style="color:#f0f; font-size:14px">LOADING...</div>
        <br>
        <div style="font-size:11px; color:#444">
            ● NEURAL LINK: CONNECTED<br>
            ● SERAPH AI: ONLINE
        </div>
    </div>
    <div class="main">
        <div id="chat" class="chat-box">
            <div class="msg ai">SYSTEM: Seraph initialized. Connected to Cloud Brain.</div>
        </div>
        <div class="input-area">
            <form onsubmit="event.preventDefault(); send()">
                <input type="text" id="cmd" placeholder="Enter command..." autocomplete="off">
            </form>
        </div>
    </div>
    <script>
        setInterval(() => {
            fetch('/api/data').then(r=>r.json()).then(d=>{
                document.getElementById('price').innerText = '$' + d.price.toLocaleString();
                let strat = JSON.parse(d.strategy || '{}');
                document.getElementById('mode').innerText = strat.version || 'OFFLINE';
            });
        }, 1000);

        async function send() {
            let i = document.getElementById('cmd');
            let c = document.getElementById('chat');
            let txt = i.value; 
            if(!txt) return;
            i.value = '';
            c.innerHTML += `<div class="msg user">${txt}</div>`;
            c.scrollTop = c.scrollHeight;
            try {
                let r = await fetch('/api/chat', {method:'POST', body:JSON.stringify({command:txt})});
                let d = await r.json();
                // Format JSON nicely in chat
                let resp = d.response.replace(/\n/g, '<br>');
                c.innerHTML += `<div class="msg ai">${resp}</div>`;
            } catch(e) {
                c.innerHTML += `<div class="msg ai" style="color:red">CONNECTION LOST</div>`;
            }
            c.scrollTop = c.scrollHeight;
        }
        document.getElementById('cmd').focus();
    </script>
</body>
</html>
            """
            self.wfile.write(html.encode('utf-8'))
        elif self.path == '/api/data':
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps(get_system_state()).encode())

    def do_POST(self):
        if self.path == '/api/chat':
            l = int(self.headers['Content-Length'])
            d = json.loads(self.rfile.read(l))
            reply = ask_seraph(d.get('command', ''))
            self.send_response(200)
            self.end_headers()
            self.wfile.write(json.dumps({"response": reply}).encode())

print(f">> GODBRAIN SERVER ON PORT {PORT}")
def open_browser():
    time.sleep(2)
    webbrowser.open(f'http://localhost:{PORT}')
threading.Thread(target=open_browser).start()
with ThreadedHTTPServer(("", PORT), RequestHandler) as httpd:
    httpd.serve_forever()