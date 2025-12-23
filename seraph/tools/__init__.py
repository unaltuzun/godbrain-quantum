# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
SERAPH Tools - Unified Package
Enable Seraph to take real actions in the system.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import json
import subprocess
import logging
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime

# Logging setup
logger = logging.getLogger("seraph.tools")

ROOT = Path(__file__).parent.parent.parent

@dataclass
class ToolResult:
    """Result from tool execution."""
    success: bool
    output: Any
    error: Optional[str] = None
    
    def to_dict(self) -> Dict:
        return {
            "success": self.success,
            "output": self.output,
            "error": self.error
        }

@dataclass
class Tool:
    """Tool definition for Claude."""
    name: str
    description: str
    input_schema: Dict[str, Any]
    handler: Callable[..., ToolResult]
    dangerous: bool = False

class SeraphTools:
    """Tool registry for Seraph."""
    
    def __init__(self):
        self.tools: Dict[str, Tool] = {}
        self._register_builtin_tools()
    
    def _register_builtin_tools(self) -> None:
        """Register built-in tools."""
        
        # File Operations
        self.register(Tool(
            name="read_file",
            description="Read contents of a file in the codebase",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {"type": "string", "description": "Relative path to file"},
                    "start_line": {"type": "integer"},
                    "end_line": {"type": "integer"}
                },
                "required": ["path"]
            },
            handler=self._read_file
        ))
        
        self.register(Tool(
            name="search_code",
            description="Search for code patterns",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"},
                    "file_pattern": {"type": "string"}
                },
                "required": ["query"]
            },
            handler=self._search_code
        ))

        self.register(Tool(
            name="get_current_time",
            description="Get the current local date and time",
            input_schema={"type": "object", "properties": {}},
            handler=self._get_current_time
        ))

        self.register(Tool(
            name="reflect",
            description="Reflect on a thought or plan",
            input_schema={
                "type": "object",
                "properties": {
                    "thought": {"type": "string"}
                },
                "required": ["thought"]
            },
            handler=self._reflect
        ))

        self.register(Tool(
            name="search_quantum_lab",
            description="Search quantum lab data",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {"type": "string"}
                },
                "required": ["query"]
            },
            handler=self._search_quantum_lab
        ))

        # ═══════════════════════════════════════════════════════════════════════════════
        # TRADING CONTROL TOOLS
        # ═══════════════════════════════════════════════════════════════════════════════
        
        self.register(Tool(
            name="start_trading",
            description="Start the VOLTRAN trading system. Use this when the user says 'başla', 'trade başlat', 'trading başlat' etc.",
            input_schema={
                "type": "object",
                "properties": {
                    "leverage": {"type": "integer", "description": "Trading leverage (1-50)"},
                    "position_size_pct": {"type": "integer", "description": "Position size as percentage of equity (1-100)"}
                }
            },
            handler=self._start_trading,
            dangerous=True
        ))

        self.register(Tool(
            name="stop_trading",
            description="Stop all trading activity immediately. Use this for 'dur', 'stop', 'kapat' commands.",
            input_schema={"type": "object", "properties": {}},
            handler=self._stop_trading,
            dangerous=True
        ))

        self.register(Tool(
            name="set_trading_params",
            description="Set trading parameters like leverage and position size",
            input_schema={
                "type": "object",
                "properties": {
                    "leverage": {"type": "integer"},
                    "position_size_pct": {"type": "integer"},
                    "max_positions": {"type": "integer"}
                }
            },
            handler=self._set_trading_params,
            dangerous=True
        ))

        self.register(Tool(
            name="get_okx_balance",
            description="Get current OKX account balance and equity",
            input_schema={"type": "object", "properties": {}},
            handler=self._get_okx_balance
        ))

        self.register(Tool(
            name="get_trading_status",
            description="Get current trading system status including positions and parameters",
            input_schema={"type": "object", "properties": {}},
            handler=self._get_trading_status
        ))

    
    def register(self, tool: Tool) -> None:
        self.tools[tool.name] = tool
    
    def get_tool_definitions(self) -> List[Dict]:
        return [
            {"name": t.name, "description": t.description, "input_schema": t.input_schema}
            for t in self.tools.values()
        ]
    
    def execute(self, name: str, inputs: Dict[str, Any]) -> ToolResult:
        if name not in self.tools:
            return ToolResult(False, None, f"Unknown tool: {name}")
        try:
            return self.tools[name].handler(**inputs)
        except Exception as e:
            return ToolResult(False, None, str(e))

    # Handlers
    def _read_file(self, path: str, start_line: int = None, end_line: int = None) -> ToolResult:
        file_path = ROOT / path
        if not file_path.exists(): return ToolResult(False, None, "File not found")
        try:
            lines = file_path.read_text(encoding="utf-8", errors="ignore").splitlines()
            if start_line or end_line:
                lines = lines[(start_line or 1)-1 : end_line or len(lines)]
            return ToolResult(True, {"content": "\n".join(lines)[:5000]})
        except Exception as e: return ToolResult(False, None, str(e))

    def _search_code(self, query: str, file_pattern: str = "*.py") -> ToolResult:
        matches = []
        for f in ROOT.rglob(file_pattern):
            if ".git" in str(f) or "node_modules" in str(f): continue
            try:
                for i, line in enumerate(f.read_text(errors="ignore").splitlines()):
                    if query.lower() in line.lower():
                        matches.append(f"{f.relative_to(ROOT)}:{i+1}: {line[:100]}")
                        if len(matches) >= 20: break
            except: pass
            if len(matches) >= 20: break
        return ToolResult(True, {"matches": matches})

    def _get_current_time(self) -> ToolResult:
        now = datetime.now()
        return ToolResult(True, {"datetime": now.strftime('%Y-%m-%d %H:%M:%S')})

    def _reflect(self, thought: str) -> ToolResult:
        logger.info(f"REFLECTION: {thought}")
        return ToolResult(True, {"status": "logged"})

    def _search_quantum_lab(self, query: str) -> ToolResult:
        wisdom_dir = ROOT / "quantum_lab" / "wisdom"
        results = []
        if wisdom_dir.exists():
            for f in wisdom_dir.glob("*.json"):
                if query.lower() in f.read_text().lower():
                    results.append(f.name)
        return ToolResult(True, {"files": results})

    # ═══════════════════════════════════════════════════════════════════════════════
    # TRADING CONTROL HANDLERS
    # ═══════════════════════════════════════════════════════════════════════════════

    def _get_redis(self):
        """Get Redis connection."""
        try:
            import redis as redis_lib
            return redis_lib.Redis(
                host=os.getenv("REDIS_HOST", "localhost"),
                port=int(os.getenv("REDIS_PORT", "16379")),
                password=os.getenv("REDIS_PASS", "voltran2024"),
                decode_responses=True
            )
        except:
            return None

    def _get_okx_client(self):
        """Get OKX CCXT client."""
        try:
            import ccxt
            return ccxt.okx({
                'apiKey': os.getenv('OKX_API_KEY'),
                'secret': os.getenv('OKX_SECRET') or os.getenv('OKX_API_SECRET'),
                'password': os.getenv('OKX_PASSWORD')
            })
        except Exception as e:
            logger.error(f"OKX client error: {e}")
            return None

    def _start_trading(self, leverage: int = 10, position_size_pct: int = 50) -> ToolResult:
        """Start the VOLTRAN trading system."""
        try:
            r = self._get_redis()
            if not r:
                return ToolResult(False, None, "Redis bağlantısı kurulamadı")
            
            # Set trading parameters
            r.set("godbrain:system:status", "ACTIVE")
            r.set("godbrain:risk:leverage", str(leverage))
            r.set("godbrain:risk:position_size_pct", str(position_size_pct))
            r.set("godbrain:trading:enabled", "true")
            r.set("godbrain:trading:started_at", datetime.now().isoformat())
            
            logger.info(f"TRADING STARTED: leverage={leverage}x, size={position_size_pct}%")
            
            return ToolResult(True, {
                "status": "ACTIVE",
                "leverage": leverage,
                "position_size_pct": position_size_pct,
                "message": f"Trading başlatıldı! Kaldıraç: {leverage}x, Pozisyon boyutu: %{position_size_pct}"
            })
        except Exception as e:
            return ToolResult(False, None, str(e))

    def _stop_trading(self) -> ToolResult:
        """Stop all trading activity."""
        try:
            r = self._get_redis()
            if not r:
                return ToolResult(False, None, "Redis bağlantısı kurulamadı")
            
            r.set("godbrain:system:status", "STOPPED")
            r.set("godbrain:trading:enabled", "false")
            r.set("godbrain:trading:stopped_at", datetime.now().isoformat())
            
            logger.info("TRADING STOPPED")
            
            return ToolResult(True, {
                "status": "STOPPED",
                "message": "Trading durduruldu. Yeni pozisyon açılmayacak."
            })
        except Exception as e:
            return ToolResult(False, None, str(e))

    def _set_trading_params(self, leverage: int = None, position_size_pct: int = None, max_positions: int = None) -> ToolResult:
        """Set trading parameters."""
        try:
            r = self._get_redis()
            if not r:
                return ToolResult(False, None, "Redis bağlantısı kurulamadı")
            
            updated = []
            if leverage is not None:
                r.set("godbrain:risk:leverage", str(leverage))
                updated.append(f"leverage={leverage}")
            if position_size_pct is not None:
                r.set("godbrain:risk:position_size_pct", str(position_size_pct))
                updated.append(f"position_size={position_size_pct}%")
            if max_positions is not None:
                r.set("godbrain:risk:max_positions", str(max_positions))
                updated.append(f"max_positions={max_positions}")
            
            return ToolResult(True, {
                "updated": updated,
                "message": f"Parametreler güncellendi: {', '.join(updated)}"
            })
        except Exception as e:
            return ToolResult(False, None, str(e))

    def _get_okx_balance(self) -> ToolResult:
        """Get OKX account balance."""
        try:
            okx = self._get_okx_client()
            if not okx:
                return ToolResult(False, None, "OKX bağlantısı kurulamadı")
            
            balance = okx.fetch_balance()
            equity = float(balance.get("total", {}).get("USDT", 0))
            
            # Store in Redis
            r = self._get_redis()
            if r:
                r.set("godbrain:trading:equity", str(equity))
            
            return ToolResult(True, {
                "equity_usdt": equity,
                "balances": {k: v for k, v in balance.get("total", {}).items() if float(v) > 0}
            })
        except Exception as e:
            return ToolResult(False, None, str(e))

    def _get_trading_status(self) -> ToolResult:
        """Get current trading system status."""
        try:
            r = self._get_redis()
            if not r:
                return ToolResult(False, None, "Redis bağlantısı kurulamadı")
            
            status = {
                "system_status": r.get("godbrain:system:status") or "UNKNOWN",
                "trading_enabled": r.get("godbrain:trading:enabled") == "true",
                "leverage": r.get("godbrain:risk:leverage") or "10",
                "position_size_pct": r.get("godbrain:risk:position_size_pct") or "50",
                "equity": r.get("godbrain:trading:equity") or "0",
                "started_at": r.get("godbrain:trading:started_at"),
            }
            
            return ToolResult(True, status)
        except Exception as e:
            return ToolResult(False, None, str(e))

# Global instance
_tools = None

def get_seraph_tools() -> SeraphTools:
    global _tools
    if _tools is None:
        _tools = SeraphTools()
    return _tools
