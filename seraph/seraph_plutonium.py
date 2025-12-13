# -*- coding: utf-8 -*-
"""
SERAPH v3.2 - PLUTONIUM EDITION (DYNAMIC CONFIG)
"""
import os
import json
import socket
import sys
import time
from datetime import datetime
from typing import Optional, Dict, Any
from dataclasses import dataclass
from enum import Enum

try:
    import requests
except ImportError:
    pass

# --- CONFIG LOADER ---
# (Environment variables are loaded by the Dashboard/Launcher before this script runs)
REDIS_HOST = '127.0.0.1'
REDIS_PORT = 16379
REDIS_PASS = 'voltran2024'
KEY_MODEL = 'godbrain:model:linear'
KEY_TICKER = 'godbrain:market:ticker'

class CommandType(Enum):
    STRATEGY_OVERRIDE = "strategy_override"
    PANIC_PROTOCOL = "panic_protocol"
    QUERY = "query"
    UNKNOWN = "unknown"

@dataclass
class SeraphCommand:
    command_type: CommandType
    payload: Any = None
    explanation: str = ""
    confidence: float = 0.0

# --- NEURAL LINK (REDIS) ---
class NeuralLink:
    def _send_cmd(self, command_str: str) -> str:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.settimeout(1.0)
            s.connect((REDIS_HOST, REDIS_PORT))
            s.sendall(f'AUTH {REDIS_PASS}\r\n'.encode())
            s.recv(1024)
            s.sendall(f"{command_str}\r\n".encode())
            resp = s.recv(4096).decode('utf-8', errors='ignore')
            s.close()
            return resp.strip()
        except:
            return "DISCONNECTED"

    def get_brain_state(self) -> str:
        model = self._send_cmd(f"GET {KEY_MODEL}")
        price = self._send_cmd(f"GET {KEY_TICKER}")
        return f"BRAIN_MODEL: {model} | MARKET_PRICE: {price}"

    def inject_strategy(self, strategy_json: Dict) -> bool:
        payload = json.dumps(strategy_json)
        resp = self._send_cmd(f"SET {KEY_MODEL} '{payload}'")
        return "+OK" in resp

# --- CLAUDE ARCHITECT ---
class ClaudePlutonium:
    SYSTEM_PROMPT = r"""
    YOU ARE SERAPH (GODBRAIN CONTROLLER).
    You control a High-Frequency Trading System.
    
    OUTPUT FORMAT (JSON ONLY):
    {
      "command_type": "strategy_override | panic_protocol | query",
      "payload": {},
      "explanation": "Short reasoning",
      "confidence": 1.0
    }
    """

    def __init__(self):
        self.api_key = os.getenv("ANTHROPIC_API_KEY")
        self.model = os.getenv("SERAPH_MODEL", "claude-3-5-sonnet-20240620")
        
    def decide(self, user_input: str, system_context: str) -> SeraphCommand:
        if not self.api_key:
            return SeraphCommand(CommandType.UNKNOWN, explanation="API KEY MISSING in .env")

        try:
            headers = {"x-api-key": self.api_key, "anthropic-version": "2023-06-01"}
            data = {
                "model": self.model,
                "max_tokens": 512,
                "system": self.SYSTEM_PROMPT,
                "messages": [{"role": "user", "content": f"CTX: {system_context}\nCMD: {user_input}"}]
            }
            
            resp = requests.post("https://api.anthropic.com/v1/messages", headers=headers, json=data, timeout=10)
            
            if resp.status_code != 200:
                return SeraphCommand(CommandType.UNKNOWN, explanation=f"API ERROR: {resp.text}")
            
            raw_text = resp.json()['content'][0]['text']
            
            # JSON PARSE
            json_str = raw_text
            if "```json" in raw_text:
                json_str = raw_text.split("```json")[1].split("```")[0]
            elif "{" in raw_text:
                start = raw_text.find('{')
                end = raw_text.rfind('}') + 1
                json_str = raw_text[start:end]
            
            parsed = json.loads(json_str)
            
            return SeraphCommand(
                command_type=CommandType(parsed.get("command_type", "unknown")),
                payload=parsed.get("payload"),
                explanation=parsed.get("explanation"),
                confidence=float(parsed.get("confidence", 0.5))
            )
        except Exception as e:
            return SeraphCommand(CommandType.UNKNOWN, explanation=f"INTERNAL ERROR: {e}")

# --- ENGINE INTERFACE ---
class SeraphEngine:
    def __init__(self):
        self.claude = ClaudePlutonium()
        self.neural = NeuralLink()

    def execute(self, user_input: str):
        # 1. READ CONTEXT
        context = self.neural.get_brain_state()
        
        # 2. ASK CLAUDE
        cmd = self.claude.decide(user_input, context)
        
        print(f"🤖 {cmd.explanation}")
        
        # 3. EXECUTE
        if cmd.command_type == CommandType.STRATEGY_OVERRIDE:
            if self.neural.inject_strategy(cmd.payload):
                print(">> STRATEGY UPDATED [OK]")
            else:
                print(">> UPDATE FAILED [ERR]")
        
        elif cmd.command_type == CommandType.PANIC_PROTOCOL:
            print(">> !!! PANIC PROTOCOL EXECUTED !!!")
            # Logic to kill python would go here or handled by dashboard
            
if __name__ == "__main__":
    print("Seraph Engine Loaded.")