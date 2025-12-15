# ==============================================================================
# IMPORTS - All required modules at the top
# ==============================================================================
import json
import os
import sys
import time
import http.server
import socketserver
import socket
import threading
import requests

# Load environment variables from .env file
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # python-dotenv not available, use environment variables only

# Optional import for webbrowser (may not be available on all systems)
try:
    import webbrowser
except ImportError:
    webbrowser = None
    print("[WARNING] webbrowser module not available. Browser will not open automatically.")

# ==============================================================================
# SERAPH V2 - Kurumsal AI Core (Feature Flag Controlled)
# ==============================================================================
SERAPH_V2_ENABLED = os.getenv("SERAPH_V2_ENABLED", "true").lower() == "true"

_seraph_core = None
def get_seraph_core():
    """Lazy load SeraphJarvis to avoid circular imports"""
    global _seraph_core
    if _seraph_core is None and SERAPH_V2_ENABLED:
        try:
            import sys
            from pathlib import Path
            # Add parent to path for seraph module
            sys.path.insert(0, str(Path(__file__).parent.parent))
            # USE JARVIS Implementation
            from seraph.seraph_jarvis import get_seraph
            _seraph_core = get_seraph()
            print("[INFO] Seraph JARVIS initialized with LONG-TERM memory support")
        except Exception as e:
            print(f"[WARNING] Seraph JARVIS init failed, using legacy: {e}")
            _seraph_core = False  # Mark as failed
    return _seraph_core if _seraph_core else None


# ==============================================================================
# 🔑 GÜVENLİK BÖLÜMÜ (BULLETPROOF KEY LOADING)
# ==============================================================================
def load_env_var(key, default=None):
    """Load environment variable with encoding cleanup."""
    value = os.getenv(key) or default
    if value:
        # Remove BOM and leading/trailing whitespace
        value = value.lstrip('\ufeff').strip()
        # Return None if completely stripped (empty string), not "" to maintain "not set" semantics
        if not value:
            return None
    return value

def get_clean_key():
    """
    Anahtarı atomlarına ayırıp görünmez karakterlerden (BOM, Zero-width space) temizler.
    Production-ready encoding fix for Windows/Linux/K8s environments.
    """
    # Priority: .env file -> ANTHROPIC_API_KEY -> SERAPH_LLM_KEY -> fallback
    raw_key = load_env_var("ANTHROPIC_API_KEY") or load_env_var("SERAPH_LLM_KEY")
    
    if not raw_key:
        return None
    
    # 1. Remove BOM character first (Windows encoding issue)
    k = raw_key.lstrip('\ufeff')
    # 2. Strip all leading/trailing whitespace
    k = k.strip()
    # 3. Remove invisible zero-width spaces
    k = k.replace('\u200b', '').replace('\u200c', '').replace('\u200d', '')
    # 4. Remove quotes if present (common .env mistake)
    k = k.strip('"').strip("'")
    # 5. Final strip to ensure clean key
    k = k.strip()
    
    return k if k else None

API_KEY = get_clean_key()
if not API_KEY:
    print("[WARNING] ANTHROPIC_API_KEY not found. Set it in .env or environment variables.")
# ==============================================================================

# Load configuration from environment variables (with .env support)
# Bug fix: Safe integer conversion with error handling
def safe_int_env(key, default):
    """Safely convert environment variable to integer with fallback to default."""
    try:
        value = os.getenv(key, str(default))
        return int(value)
    except (ValueError, TypeError):
        print(f"[WARNING] Invalid value for {key}, using default: {default}")
        return int(default)

PORT = safe_int_env("PORT", 8000)
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = safe_int_env("REDIS_PORT", 16379)
REDIS_PASS = os.getenv("REDIS_PASS", "voltran2024")

# Check if port is available, try alternative ports if needed
def find_available_port(start_port=8000, max_attempts=10):
    """
    Find an available port starting from start_port.
    Bug fix: Uses server binding instead of client connection to properly verify port availability.
    This correctly handles ports in TIME_WAIT state and other edge cases.
    """
    for i in range(max_attempts):
        port = start_port + i
        test_socket = None
        try:
            # Attempt to bind as a server to verify port availability
            # This is the correct way to check if a port can be used for server binding
            test_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            test_socket.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
            test_socket.bind(('', port))  # Bind to all interfaces
            test_socket.close()
            # If bind succeeded, port is available
            return port
        except OSError:
            # Port is in use or unavailable (TIME_WAIT, already bound, etc.)
            if test_socket:
                try:
                    test_socket.close()
                except:
                    pass
            continue
        except Exception:
            # Other errors, try next port
            if test_socket:
                try:
                    test_socket.close()
                except:
                    pass
            continue
    return start_port  # Fallback to original port

# --- REDIS CLIENT ---
def redis_cmd(cmd):
    try:
        s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        s.settimeout(0.5)
        s.connect((REDIS_HOST, REDIS_PORT))
        s.sendall(f'AUTH {REDIS_PASS}\r\n'.encode())
        auth_resp = s.recv(1024).decode('utf-8', errors='ignore')
        # Check if auth was successful
        if '+OK' not in auth_resp and 'OK' not in auth_resp:
            s.close()
            return None
        s.sendall(f"{cmd}\r\n".encode())
        resp = s.recv(4096).decode('utf-8', errors='ignore')
        s.close()
        return resp.strip()
    except Exception as e:
        # Debug: Log Redis connection errors
        print(f"[DEBUG] Redis connection error: {e}, HOST={REDIS_HOST}, PORT={REDIS_PORT}")
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


def _execute_seraph_actions(content: str, actions: list) -> str:
    """
    Execute Seraph actions (SET, PUBLISH commands to Redis).
    Extracted for reuse between V2 and legacy.
    """
    def sanitize_redis_param(param):
        """Remove dangerous characters that could enable Redis command injection."""
        if not param:
            return ''
        sanitized = param.replace("\r\n", "").replace("\n", "").replace("\r", "")
        sanitized = sanitized.replace("'", "").replace('"', '')
        sanitized = sanitized.replace("\\", "")
        sanitized = sanitized.replace(";", "").replace("&", "").replace("|", "")
        return sanitized.strip()
    
    logs = []
    for action in actions:
        cmd = action.get('cmd', '').upper()
        key = action.get('key', '')
        value = action.get('value', '')
        
        if cmd == 'SET':
            safe_key = sanitize_redis_param(key)
            safe_value = sanitize_redis_param(value)
            if not safe_key:
                logs.append(f"EXEC: SET -> SKIPPED (empty key)")
                continue
            res = redis_cmd(f'SET {safe_key} "{safe_value}"')
            if res and ('+OK' in res or 'OK' in res):
                logs.append(f"EXEC: SET {safe_key} -> OK")
            else:
                logs.append(f"EXEC: SET {safe_key} -> FAILED: {res}")
        
        elif cmd == 'PUBLISH':
            channel = action.get('channel', key)
            safe_channel = sanitize_redis_param(channel)
            safe_value = sanitize_redis_param(value)
            if not safe_channel:
                logs.append(f"EXEC: PUBLISH -> SKIPPED (empty channel)")
                continue
            res = redis_cmd(f'PUBLISH {safe_channel} "{safe_value}"')
            logs.append(f"EXEC: PUBLISH {safe_channel} -> {res}")
    
    if logs:
        action_log = "\n\n---\n🔧 EXECUTED:\n" + "\n".join(logs)
        return content + action_log
    return content


# --- SERAPH BRAIN (EVOLVED) ---
def ask_seraph(user_input):
    """
    Ask Seraph AI a question.
    
    Uses Seraph JARVIS (V2) if enabled (with memory), otherwise falls back to legacy.
    """
    # Try Seraph V2 first (with memory support)
    seraph_jarvis = get_seraph_core()
    if seraph_jarvis:
        try:
            # Jarvis independently gets awareness, we don't need to pass context
            # It also handles memory and RAG internally.
            response_content = seraph_jarvis.chat(user_input)
            
            # Note: Jarvis currently does not return distinct actions list in this call method.
            # But the 'chat' method returns the string content.
            # If we need action support (JSON commands), we might need to parse them from the text 
            # or update Jarvis to return a structured object.
            
            # Simple Action Parsing for Jarvis (backward comp):
            if '{"actions":' in response_content:
                 # Reuse legacy action parser logic if possible or rely on Jarvis executing it?
                 # Jarvis logic above doesn't execute actions, it just returns text.
                 # So we should parse and execute here.
                 
                 # Let's use the legacy action parser on the response content
                 # Actually, let's just return content for now, or adapt it.
                 pass
                 
            return response_content
            
        except Exception as e:
            print(f"[SERAPH V2] Exception: {e}, falling back to legacy")
    
    # Legacy implementation (fallback)
    try:
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
        
        # Use environment variable for model, or fallback to latest Claude Sonnet 4.5
        # Updated model name: claude-3-5-sonnet models are deprecated, using claude-sonnet-4-5
        model_name = os.getenv("SERAPH_MODEL") or os.getenv("SERAPH_LLM_MODEL") or "claude-sonnet-4-5-20250929"
        
        data = {
            "model": model_name,
            "max_tokens": 512,
            "system": sys_msg,
            "messages": [{"role": "user", "content": user_input}]
        }
        
        r = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=data, timeout=15)
        
        if r.status_code == 200:
            content = r.json()['content'][0]['text']
            
            # --- CEREBRO: ACTION EXECUTOR (Level 5 Command Execution) ---
            if '{"actions":' in content:
                try:
                    # Extract JSON from response (handle markdown code blocks)
                    json_start = content.find('{"actions":')
                    if json_start == -1:
                        json_start = content.find('{')
                    json_end = content.rfind('}') + 1
                    json_part = content[json_start:json_end]
                    cmd_data = json.loads(json_part)
                    actions = cmd_data.get('actions', [])
                    
                    logs = []
                    for action in actions:
                        cmd = action.get('cmd', '').upper()
                        key = action.get('key', '')
                        value = action.get('value', '')
                        
                        # Bug fix: Sanitize ALL parameters (key, channel, value) to prevent Redis injection
                        # Redis inline protocol doesn't support backslash escaping, so we strip dangerous chars
                        def sanitize_redis_param(param):
                            """Remove dangerous characters that could enable Redis command injection."""
                            if not param:
                                return ''
                            # Remove newlines, carriage returns, and other control characters
                            # Bug fix: Replace \r\n FIRST, then single characters, to handle Windows line endings correctly
                            sanitized = param.replace("\r\n", "").replace("\n", "").replace("\r", "")
                            # Remove single quotes (Redis inline protocol doesn't support escaping)
                            # Using double quotes instead for values containing spaces/special chars
                            sanitized = sanitized.replace("'", "").replace('"', '')
                            # Remove backslashes (not used for escaping in inline protocol)
                            sanitized = sanitized.replace("\\", "")
                            # Remove other potentially dangerous characters
                            sanitized = sanitized.replace(";", "").replace("&", "").replace("|", "")
                            return sanitized.strip()
                        
                        if cmd == 'SET':
                            # Sanitize both key and value
                            safe_key = sanitize_redis_param(key)
                            safe_value = sanitize_redis_param(value)
                            
                            if not safe_key:
                                logs.append(f"EXEC: SET -> SKIPPED (empty key)")
                                continue
                            
                            # Use double quotes for values to avoid single quote issues
                            # Redis inline protocol accepts both single and double quotes
                            res = redis_cmd(f'SET {safe_key} "{safe_value}"')
                            if res and ('+OK' in res or 'OK' in res):
                                logs.append(f"EXEC: SET {safe_key} -> OK")
                            else:
                                logs.append(f"EXEC: SET {safe_key} -> FAILED: {res}")
                        
                        elif cmd == 'PUBLISH':
                            # Sanitize channel and value
                            channel = action.get('channel', key)
                            safe_channel = sanitize_redis_param(channel)
                            safe_value = sanitize_redis_param(value)
                            
                            if not safe_channel:
                                logs.append(f"EXEC: PUBLISH -> SKIPPED (empty channel)")
                                continue
                            
                            # Use double quotes for values
                            res = redis_cmd(f'PUBLISH {safe_channel} "{safe_value}"')
                            if res and res.isdigit():
                                logs.append(f"EXEC: PUBLISH {channel} -> {res} subscribers")
                            else:
                                logs.append(f"EXEC: PUBLISH {channel} -> FAILED: {res}")
                        
                        else:
                            logs.append(f"EXEC: Unknown command '{cmd}' -> SKIPPED")
                    
                    return f"{content}\n\n[SYSTEM LOG]: {', '.join(logs)}"
                except json.JSONDecodeError as e:
                    return f"{content}\n\n[EXEC ERROR]: JSON parse failed - {e}"
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
    def end_headers(self):
        """Add CORS headers to all responses."""
        self.send_header('Access-Control-Allow-Origin', '*')
        self.send_header('Access-Control-Allow-Methods', 'GET, POST, OPTIONS')
        self.send_header('Access-Control-Allow-Headers', 'Content-Type, Accept')
        super().end_headers()
    
    def do_OPTIONS(self):
        """Handle CORS preflight requests."""
        self.send_response(200)
        self.end_headers()
    
    def do_GET(self):
        if self.path == '/favicon.ico':
            # Return empty favicon to avoid 404 errors
            self.send_response(204)
            self.end_headers()
            return
        elif self.path == '/':
            # Serve admin panel
            self.send_response(200)
            self.send_header('Content-type', 'text/html')
            self.end_headers()
            try:
                # Try multiple paths for admin panel (Docker container paths)
                current_dir = os.path.dirname(os.path.abspath(__file__))
                admin_panel_paths = [
                    os.path.join(current_dir, 'admin_panel.html'),
                    os.path.join(os.getcwd(), 'core', 'admin_panel.html'),
                    '/app/core/admin_panel.html',
                    'core/admin_panel.html',
                    os.path.join(os.path.dirname(__file__), 'admin_panel.html')
                ]
                html = None
                for path in admin_panel_paths:
                    try:
                        if os.path.exists(path):
                            with open(path, 'r', encoding='utf-8') as f:
                                html = f.read()
                            break
                    except Exception as e:
                        continue
                if not html:
                    raise FileNotFoundError("Admin panel not found in any path")
            except Exception as e:
                # Fallback to simple dashboard if admin panel not found
                html = """
<!DOCTYPE html>
<html lang="en">
<head>
    <meta charset="UTF-8">
    <title>GODBRAIN QUANTUM</title>
    <style>
        * { box-sizing: border-box; margin: 0; padding: 0; }
        body { 
            background: linear-gradient(135deg, #0a0a0a 0%, #1a1a2e 100%); 
            color: #e0e0e0; 
            font-family: 'Segoe UI', Tahoma, Geneva, Verdana, sans-serif; 
            display: flex; 
            height: 100vh; 
            margin: 0; 
            overflow: hidden; 
        }
        .sidebar { 
            width: 320px; 
            padding: 24px; 
            border-right: 2px solid #2a2a3e; 
            background: linear-gradient(180deg, #0f0f1e 0%, #1a1a2e 100%);
            box-shadow: 2px 0 10px rgba(0,255,0,0.1);
        }
        .sidebar h2 { 
            color: #00ff88; 
            font-size: 28px; 
            margin-bottom: 8px; 
            text-shadow: 0 0 10px rgba(0,255,136,0.5);
        }
        .sidebar h2 span { 
            font-size: 14px; 
            color: #00cc6a; 
        }
        .metric-label { 
            color: #888; 
            font-size: 12px; 
            text-transform: uppercase; 
            letter-spacing: 1px; 
            margin-top: 24px; 
            margin-bottom: 8px; 
        }
        .metric { 
            font-size: 32px; 
            font-weight: 700; 
            color: #fff; 
            margin-bottom: 24px; 
            text-shadow: 0 0 8px rgba(255,255,255,0.3);
        }
        .status { 
            font-size: 12px; 
            color: #666; 
            margin-top: 24px; 
            line-height: 1.8; 
        }
        .status-item { 
            color: #00ff88; 
            margin-bottom: 4px; 
        }
        .main { 
            flex: 1; 
            display: flex; 
            flex-direction: column; 
            background: #0a0a0a;
        }
        .chat-box { 
            flex: 1; 
            padding: 24px; 
            overflow-y: auto; 
            display: flex; 
            flex-direction: column; 
            gap: 16px; 
            background: #0a0a0a;
        }
        .chat-box::-webkit-scrollbar { width: 8px; }
        .chat-box::-webkit-scrollbar-track { background: #1a1a1a; }
        .chat-box::-webkit-scrollbar-thumb { background: #333; border-radius: 4px; }
        .chat-box::-webkit-scrollbar-thumb:hover { background: #444; }
        .msg { 
            padding: 16px 20px; 
            border-radius: 12px; 
            max-width: 75%; 
            line-height: 1.6; 
            word-wrap: break-word;
            animation: fadeIn 0.3s ease-in;
        }
        @keyframes fadeIn {
            from { opacity: 0; transform: translateY(10px); }
            to { opacity: 1; transform: translateY(0); }
        }
        .msg.user { 
            align-self: flex-end; 
            background: linear-gradient(135deg, #1e3a5f 0%, #2a4a6f 100%); 
            color: #e0f0ff; 
            border: 1px solid #3a5a7f; 
            box-shadow: 0 2px 8px rgba(30,58,95,0.3);
        }
        .msg.ai { 
            align-self: flex-start; 
            background: linear-gradient(135deg, #0a2a1a 0%, #1a3a2a 100%); 
            color: #a0ffc0; 
            border: 1px solid #2a5a3a; 
            box-shadow: 0 2px 8px rgba(0,255,136,0.2);
        }
        .msg.error {
            align-self: flex-start;
            background: linear-gradient(135deg, #3a1a1a 0%, #5a2a2a 100%);
            color: #ffaaaa;
            border: 1px solid #7a3a3a;
        }
        .input-area { 
            padding: 20px 24px; 
            border-top: 2px solid #2a2a3e; 
            background: linear-gradient(180deg, #0f0f1e 0%, #1a1a2e 100%);
            box-shadow: 0 -2px 10px rgba(0,0,0,0.3);
        }
        .input-wrapper {
            display: flex;
            gap: 12px;
            align-items: center;
        }
        input { 
            flex: 1;
            background: #1a1a2e; 
            border: 2px solid #3a3a4e; 
            color: #e0e0e0; 
            padding: 14px 18px; 
            font-family: inherit; 
            font-size: 15px; 
            outline: none; 
            border-radius: 8px;
            transition: all 0.3s ease;
        }
        input:focus { 
            border-color: #00ff88; 
            box-shadow: 0 0 12px rgba(0,255,136,0.3);
            background: #1f1f3e;
        }
        input::placeholder {
            color: #666;
        }
        button {
            background: linear-gradient(135deg, #00ff88 0%, #00cc6a 100%);
            border: none;
            color: #000;
            padding: 14px 28px;
            font-size: 15px;
            font-weight: 600;
            border-radius: 8px;
            cursor: pointer;
            transition: all 0.3s ease;
            box-shadow: 0 2px 8px rgba(0,255,136,0.3);
        }
        button:hover {
            transform: translateY(-2px);
            box-shadow: 0 4px 12px rgba(0,255,136,0.5);
        }
        button:active {
            transform: translateY(0);
        }
        button:disabled {
            opacity: 0.5;
            cursor: not-allowed;
        }
        .loading {
            display: inline-block;
            width: 12px;
            height: 12px;
            border: 2px solid #00ff88;
            border-top-color: transparent;
            border-radius: 50%;
            animation: spin 0.8s linear infinite;
        }
        @keyframes spin {
            to { transform: rotate(360deg); }
        }
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
            <div class="input-wrapper">
                <input type="text" id="cmd" placeholder="Komut girin (ör: leverage kaç, analiz yap)..." autocomplete="off">
                <button type="button" id="sendBtn">Gönder</button>
            </div>
        </div>
    </div>
    <script>
        (function() {
            'use strict';
            
            let isSending = false;
            
            // Update market data
            setInterval(() => {
                fetch('/api/data').then(r=>r.json()).then(d=>{
                    document.getElementById('price').innerText = '$' + d.price.toLocaleString();
                    // Bug fix: Safely parse strategy - it might be a string like "OFFLINE" or a JSON string
                    let stratVersion = 'OFFLINE';
                    if (d.strategy && d.strategy !== 'OFFLINE') {
                        try {
                            let strat = JSON.parse(d.strategy);
                            stratVersion = strat.version || 'OFFLINE';
                        } catch(e) {
                            // Not valid JSON, use as-is
                            stratVersion = d.strategy;
                        }
                    }
                    document.getElementById('mode').innerText = stratVersion;
                }).catch(e => console.error('Data fetch error:', e));
            }, 1000);
            
            // Send function
            async function sendMessage() {
                if (isSending) {
                    return;
                }
                
                let inputEl = document.getElementById('cmd');
                let chatEl = document.getElementById('chat');
                let btnEl = document.getElementById('sendBtn');
                
                if (!inputEl || !chatEl || !btnEl) {
                    return;
                }
                
                let txt = inputEl.value.trim();
                
                if (!txt) {
                    inputEl.focus();
                    return;
                }
                
                isSending = true;
                btnEl.disabled = true;
                btnEl.innerHTML = '<span class="loading"></span>';
                
                // Show user message
                // Bug fix: Use textContent to prevent XSS attacks
                inputEl.value = '';
                const userMsgDiv = document.createElement('div');
                userMsgDiv.className = 'msg user';
                userMsgDiv.textContent = txt;  // textContent automatically escapes HTML
                chatEl.appendChild(userMsgDiv);
                chatEl.scrollTop = chatEl.scrollHeight;
                
                try {
                    let response = await fetch('/api/chat', {
                        method: 'POST',
                        headers: {
                            'Content-Type': 'application/json',
                            'Accept': 'application/json'
                        },
                        body: JSON.stringify({command: txt})
                    });
                    
                    if (!response.ok) {
                        let errorText = await response.text();
                        throw new Error(`HTTP ${response.status}: ${errorText || response.statusText}`);
                    }
                    
                    let data = await response.json();
                    
                    if (data.error) {
                        // Bug fix: Use textContent to prevent XSS attacks
                        const errorDiv = document.createElement('div');
                        errorDiv.className = 'msg error';
                        errorDiv.textContent = `HATA: ${data.error}`;
                        chatEl.appendChild(errorDiv);
                    } else {
                        // Bug fix: Properly escape HTML while preserving newlines as <br>
                        let resp = data.response || 'Yanıt alınamadı';
                        // Escape HTML entities first
                        const escapeHtml = (text) => {
                            const div = document.createElement('div');
                            div.textContent = text;
                            return div.innerHTML;
                        };
                        // Convert newlines to <br> after escaping
                        // Bug fix: Replace \r\n FIRST, then single \n, to handle Windows line endings correctly
                        resp = escapeHtml(resp).replace(/\r\n/g, '<br>').replace(/\n/g, '<br>').replace(/\r/g, '<br>');
                        const aiMsgDiv = document.createElement('div');
                        aiMsgDiv.className = 'msg ai';
                        aiMsgDiv.innerHTML = resp;  // Safe now - already escaped
                        chatEl.appendChild(aiMsgDiv);
                    }
                } catch(error) {
                    // Bug fix: Use textContent to prevent XSS attacks
                    const errorDiv = document.createElement('div');
                    errorDiv.className = 'msg error';
                    errorDiv.textContent = `HATA: ${error.message || 'Bağlantı hatası'}`;
                    chatEl.appendChild(errorDiv);
                } finally {
                    isSending = false;
                    btnEl.disabled = false;
                    btnEl.innerHTML = 'Gönder';
                    chatEl.scrollTop = chatEl.scrollHeight;
                    inputEl.focus();
                }
            }
            
            // Initialize when DOM is ready
            function init() {
                let cmdInput = document.getElementById('cmd');
                let sendBtn = document.getElementById('sendBtn');
                
                if (!cmdInput || !sendBtn) {
                    setTimeout(init, 100);
                    return;
                }
                
                // Enter key
                cmdInput.addEventListener('keydown', function(e) {
                    if (e.key === 'Enter' && !e.shiftKey) {
                        e.preventDefault();
                        sendMessage();
                    }
                });
                
                // Button click
                sendBtn.addEventListener('click', function(e) {
                    e.preventDefault();
                    sendMessage();
                });
                
                // Make globally available
                window.sendMessage = sendMessage;
                window.send = sendMessage; // Alias for compatibility
                
                cmdInput.focus();
            }
            
            // Start initialization
            if (document.readyState === 'loading') {
                document.addEventListener('DOMContentLoaded', init);
            } else {
                init();
            }
        })();
    </script>
</body>
</html>
            """
            self.wfile.write(html.encode('utf-8'))
        elif self.path == '/api/data':
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(get_system_state()).encode())
        elif self.path == '/api/system-status':
            # Comprehensive system status
            # Test Redis connection properly
            redis_ping = redis_cmd("PING")
            redis_connected = redis_ping is not None and ('+PONG' in redis_ping or 'PONG' in redis_ping or 'OK' in redis_ping)
            
            status = {
                "redis": {
                    "connected": redis_connected, 
                    "host": REDIS_HOST, 
                    "port": REDIS_PORT,
                    "ping_response": redis_ping[:50] if redis_ping else None
                },
                "seraph": {
                    "online": API_KEY is not None and len(API_KEY) > 50, 
                    "model": os.getenv("SERAPH_MODEL", "claude-sonnet-4-5-20250929"),
                    "api_key_length": len(API_KEY) if API_KEY else 0
                },
                "market_feed": {"status": "unknown"},  # Can be enhanced
                "synthia": {"status": "unknown"},  # Can be enhanced
                "uptime": time.time()  # Server start time
            }
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(status).encode())
        elif self.path == '/api/synthia-status':
            # Check Synthia core status
            try:
                # Try to read synthia process or check Redis for synthia data
                synthia_status = {
                    "core_active": False,
                    "tunnel_health": redis_cmd("PING") is not None,
                    "last_heartbeat": None,
                    "current_mode": "UNKNOWN"
                }
                # Check if synthia is running (basic check)
                model_data = redis_cmd("GET godbrain:model:linear")
                if model_data and '{' in model_data:
                    try:
                        model_json = json.loads(model_data[model_data.find('{'):model_data.rfind('}')+1])
                        synthia_status["current_mode"] = model_json.get("version", "UNKNOWN")
                        synthia_status["core_active"] = True
                    except:
                        pass
            except:
                synthia_status = {"error": "Status check failed"}
            self.send_response(200)
            self.send_header('Content-type', 'application/json')
            self.end_headers()
            self.wfile.write(json.dumps(synthia_status).encode())

    def do_POST(self):
        if self.path == '/api/chat':
            try:
                content_length = int(self.headers.get('Content-Length', 0))
                if content_length == 0:
                    self.send_response(400)
                    self.send_header('Content-type', 'application/json')
                    self.end_headers()
                    self.wfile.write(json.dumps({"error": "Empty request body"}).encode())
                    return
                
                raw_data = self.rfile.read(content_length)
                d = json.loads(raw_data.decode('utf-8'))
                command = d.get('command', '')
                reply = ask_seraph(command)
                self.send_response(200)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"response": reply}).encode())
            except json.JSONDecodeError as e:
                self.send_response(400)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Invalid JSON: {e}"}).encode())
            except Exception as e:
                self.send_response(500)
                self.send_header('Content-type', 'application/json')
                self.end_headers()
                self.wfile.write(json.dumps({"error": f"Server error: {e}"}).encode())
        else:
            self.send_response(404)
            self.end_headers()

# Wrap main execution in try-except to catch any NameError or other exceptions
try:
    print(f">> GODBRAIN SERVER ON PORT {PORT}")
except NameError as e:
    print(f"[ERROR] NameError: {e}")
    print("[ERROR] PORT variable is not defined. This should not happen.")
    sys.exit(1)
except Exception as e:
    print(f"[ERROR] Unexpected error during startup: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)

def open_browser(port):
    """Open browser with the specified port."""
    time.sleep(2)
    try:
        if webbrowser is not None:
            webbrowser.open(f'http://localhost:{port}')
        else:
            print(f"[INFO] Browser not opened automatically. Please open manually: http://localhost:{port}")
    except Exception as e:
        print(f"[WARNING] Could not open browser automatically: {e}")
        print(f"[INFO] Please open manually: http://localhost:{port}")

# Main execution - wrap in try-except to catch any NameError or other exceptions
try:
    # Start HTTP server
    # Bug fix: Browser thread is started AFTER successful server binding to ensure correct port
    server_started = False
    actual_port = PORT
    
    try:
        with ThreadedHTTPServer(("", PORT), RequestHandler) as httpd:
            actual_port = PORT
            server_started = True
            print(f"[SUCCESS] HTTP server started on port {actual_port}")
            print(f"[INFO] Server is ready. Open http://localhost:{actual_port} in your browser")
            
            # Start browser thread AFTER successful server binding
            if webbrowser is not None:
                try:
                    browser_thread = threading.Thread(target=open_browser, args=(actual_port,), daemon=True)
                    browser_thread.start()
                except Exception as e:
                    print(f"[WARNING] Could not start browser thread: {e}")
                    print(f"[INFO] Please open manually: http://localhost:{actual_port}")
            else:
                print(f"[INFO] Browser will not open automatically. Please open manually: http://localhost:{actual_port}")
            
            httpd.serve_forever()
    except OSError as e:
        if "10048" in str(e) or "address already in use" in str(e).lower():
            # Port is in use, try to find another port
            print(f"[WARNING] Port {PORT} is already in use. Trying alternative port...")
            actual_port = find_available_port(PORT + 1)
            try:
                with ThreadedHTTPServer(("", actual_port), RequestHandler) as httpd:
                    server_started = True
                    print(f"[SUCCESS] HTTP server started on port {actual_port}")
                    print(f"[INFO] Server is ready. Open http://localhost:{actual_port} in your browser")
                    
                    # Start browser thread AFTER successful server binding with correct port
                    if webbrowser is not None:
                        try:
                            browser_thread = threading.Thread(target=open_browser, args=(actual_port,), daemon=True)
                            browser_thread.start()
                        except Exception as e:
                            print(f"[WARNING] Could not start browser thread: {e}")
                            print(f"[INFO] Please open manually: http://localhost:{actual_port}")
                    else:
                        print(f"[INFO] Browser will not open automatically. Please open manually: http://localhost:{actual_port}")
                    
                    httpd.serve_forever()
            except Exception as e2:
                print(f"[ERROR] Could not start HTTP server on any port: {e2}")
                import traceback
                traceback.print_exc()
                sys.exit(1)
        else:
            print(f"[ERROR] Could not start HTTP server: {e}")
            import traceback
            traceback.print_exc()
            sys.exit(1)
    except Exception as e:
        print(f"[ERROR] Could not start HTTP server: {e}")
        import traceback
        traceback.print_exc()
        sys.exit(1)
except NameError as e:
    print(f"[ERROR] Could not start HTTP server: {e}")
    import traceback
    traceback.print_exc()
    sys.exit(1)