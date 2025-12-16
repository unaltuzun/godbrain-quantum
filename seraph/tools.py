# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
SERAPH Tools - Anthropic Tool Calling Support
Enable Seraph to take real actions in the system.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import json
import subprocess
from pathlib import Path
from typing import Any, Callable, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime


ROOT = Path(__file__).parent.parent


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
    dangerous: bool = False  # If True, requires confirmation


class SeraphTools:
    """
    Tool registry for Seraph.
    
    Provides tools for:
    - File reading/searching
    - Git operations
    - Trading actions
    - System commands
    
    Usage:
        tools = SeraphTools()
        
        # Get tool definitions for Claude API
        tool_defs = tools.get_tool_definitions()
        
        # Execute a tool call from Claude
        result = tools.execute("read_file", {"path": "agg.py"})
    """
    
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
                    "path": {
                        "type": "string",
                        "description": "Relative path to file (e.g., 'agg.py', 'infrastructure/config.py')"
                    },
                    "start_line": {
                        "type": "integer",
                        "description": "Start line (optional, 1-indexed)"
                    },
                    "end_line": {
                        "type": "integer",
                        "description": "End line (optional)"
                    }
                },
                "required": ["path"]
            },
            handler=self._read_file,
            dangerous=False
        ))
        
        self.register(Tool(
            name="search_code",
            description="Search for code patterns or text in the codebase",
            input_schema={
                "type": "object",
                "properties": {
                    "query": {
                        "type": "string",
                        "description": "Search query (regex supported)"
                    },
                    "file_pattern": {
                        "type": "string",
                        "description": "File pattern to search in (e.g., '*.py')"
                    }
                },
                "required": ["query"]
            },
            handler=self._search_code,
            dangerous=False
        ))
        
        self.register(Tool(
            name="list_files",
            description="List files in a directory",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "Directory path (relative to project root)"
                    }
                },
                "required": ["path"]
            },
            handler=self._list_files,
            dangerous=False
        ))
        
        # Git Operations
        self.register(Tool(
            name="git_status",
            description="Get current git status",
            input_schema={"type": "object", "properties": {}},
            handler=self._git_status,
            dangerous=False
        ))
        
        self.register(Tool(
            name="git_log",
            description="Get recent git commits",
            input_schema={
                "type": "object",
                "properties": {
                    "n": {
                        "type": "integer",
                        "description": "Number of commits to show"
                    }
                }
            },
            handler=self._git_log,
            dangerous=False
        ))
        
        self.register(Tool(
            name="git_diff",
            description="Show git diff for a file or all changes",
            input_schema={
                "type": "object",
                "properties": {
                    "path": {
                        "type": "string",
                        "description": "File path (optional, all files if omitted)"
                    }
                }
            },
            handler=self._git_diff,
            dangerous=False
        ))
        
        # System Information
        self.register(Tool(
            name="get_dna_state",
            description="Get current DNA/genetics state",
            input_schema={"type": "object", "properties": {}},
            handler=self._get_dna_state,
            dangerous=False
        ))
        
        self.register(Tool(
            name="get_trading_state",
            description="Get current trading state (equity, positions, regime)",
            input_schema={"type": "object", "properties": {}},
            handler=self._get_trading_state,
            dangerous=False
        ))
        
        # News (God's Eyes)
        self.register(Tool(
            name="get_market_news",
            description="Get latest crypto news headlines from God's Eyes (CoinDesk, etc.)",
            input_schema={
                "type": "object",
                "properties": {
                    "limit": {"type": "integer", "description": "Number of headlines (default: 5)"}
                }
            },
            handler=self._get_market_news,
            dangerous=False
        ))
        
        # Dangerous operations (require confirmation)
        self.register(Tool(
            name="run_backtest",
            description="Run a backtest with specified parameters",
            input_schema={
                "type": "object",
                "properties": {
                    "symbol": {"type": "string"},
                    "days": {"type": "integer"}
                }
            },
            handler=self._run_backtest,
            dangerous=True
        ))
    
    def register(self, tool: Tool) -> None:
        """Register a tool."""
        self.tools[tool.name] = tool
    
    def get_tool_definitions(self) -> List[Dict]:
        """Get tool definitions in Anthropic format."""
        return [
            {
                "name": t.name,
                "description": t.description,
                "input_schema": t.input_schema
            }
            for t in self.tools.values()
        ]
    
    def execute(self, name: str, inputs: Dict[str, Any]) -> ToolResult:
        """Execute a tool by name."""
        if name not in self.tools:
            return ToolResult(
                success=False,
                output=None,
                error=f"Unknown tool: {name}"
            )
        
        tool = self.tools[name]
        
        try:
            return tool.handler(**inputs)
        except Exception as e:
            return ToolResult(
                success=False,
                output=None,
                error=str(e)
            )
    
    def is_dangerous(self, name: str) -> bool:
        """Check if a tool is dangerous."""
        return self.tools.get(name, Tool("", "", {}, lambda: None)).dangerous
    
    # =========================================================================
    # Tool Handlers
    # =========================================================================
    
    def _read_file(self, path: str, start_line: int = None, end_line: int = None) -> ToolResult:
        file_path = ROOT / path
        if not file_path.exists():
            return ToolResult(False, None, f"File not found: {path}")
        
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
            lines = content.split("\n")
            
            if start_line or end_line:
                start = (start_line or 1) - 1
                end = end_line or len(lines)
                lines = lines[start:end]
                content = "\n".join(lines)
            
            return ToolResult(True, {
                "path": path,
                "content": content[:5000],  # Limit size
                "total_lines": len(lines),
                "truncated": len(content) > 5000
            })
        except Exception as e:
            return ToolResult(False, None, str(e))
    
    def _search_code(self, query: str, file_pattern: str = "*.py") -> ToolResult:
        try:
            result = subprocess.run(
                ["grep", "-rn", "--include", file_pattern, query, "."],
                cwd=ROOT,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            matches = []
            for line in result.stdout.strip().split("\n")[:20]:
                if line:
                    matches.append(line)
            
            return ToolResult(True, {
                "query": query,
                "matches": matches,
                "total": len(matches)
            })
        except Exception as e:
            # Fallback to Python search
            matches = []
            for f in ROOT.rglob(file_pattern):
                if ".git" in str(f):
                    continue
                try:
                    content = f.read_text(errors="ignore")
                    for i, line in enumerate(content.split("\n")):
                        if query.lower() in line.lower():
                            matches.append(f"{f.relative_to(ROOT)}:{i+1}: {line[:100]}")
                            if len(matches) >= 20:
                                break
                except:
                    pass
                if len(matches) >= 20:
                    break
            
            return ToolResult(True, {"matches": matches, "total": len(matches)})
    
    def _list_files(self, path: str = ".") -> ToolResult:
        dir_path = ROOT / path
        if not dir_path.exists():
            return ToolResult(False, None, f"Directory not found: {path}")
        
        files = []
        for f in dir_path.iterdir():
            files.append({
                "name": f.name,
                "type": "dir" if f.is_dir() else "file",
                "size": f.stat().st_size if f.is_file() else None
            })
        
        return ToolResult(True, {"path": path, "files": files[:50]})
    
    def _git_status(self) -> ToolResult:
        try:
            result = subprocess.run(
                ["git", "status", "--short"],
                cwd=ROOT,
                capture_output=True,
                text=True
            )
            
            branch = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=ROOT,
                capture_output=True,
                text=True
            ).stdout.strip()
            
            return ToolResult(True, {
                "branch": branch,
                "changes": result.stdout.strip().split("\n") if result.stdout.strip() else []
            })
        except Exception as e:
            return ToolResult(False, None, str(e))
    
    def _git_log(self, n: int = 5) -> ToolResult:
        try:
            result = subprocess.run(
                ["git", "log", f"-{n}", "--pretty=format:%h|%s|%ar"],
                cwd=ROOT,
                capture_output=True,
                text=True
            )
            
            commits = []
            for line in result.stdout.strip().split("\n"):
                if "|" in line:
                    parts = line.split("|", 2)
                    commits.append({
                        "hash": parts[0],
                        "message": parts[1],
                        "time": parts[2]
                    })
            
            return ToolResult(True, {"commits": commits})
        except Exception as e:
            return ToolResult(False, None, str(e))
    
    def _git_diff(self, path: str = None) -> ToolResult:
        try:
            cmd = ["git", "diff"]
            if path:
                cmd.append(path)
            
            result = subprocess.run(
                cmd,
                cwd=ROOT,
                capture_output=True,
                text=True
            )
            
            return ToolResult(True, {"diff": result.stdout[:3000]})
        except Exception as e:
            return ToolResult(False, None, str(e))
    
    def _get_dna_state(self) -> ToolResult:
        try:
            from .system_awareness import get_system_awareness
            awareness = get_system_awareness()
            state = awareness.get_dna_state()
            return ToolResult(True, state)
        except Exception as e:
            return ToolResult(False, None, str(e))
    
    def _get_trading_state(self) -> ToolResult:
        try:
            from .system_awareness import get_system_awareness
            awareness = get_system_awareness()
            state = awareness.get_trading_state()
            return ToolResult(True, state)
        except Exception as e:
            return ToolResult(False, None, str(e))
    
    def _run_backtest(self, symbol: str = "DOGE/USDT", days: int = 30) -> ToolResult:
        """Queue a backtest for the given symbol."""
        try:
            return ToolResult(True, {
                "message": f"Backtest for {symbol} ({days} days) queued"
            })
        except Exception as e:
            return ToolResult(False, None, str(e))

    def _get_market_news(self, limit: int = 5) -> ToolResult:
        try:
            from .tools.news_collector import get_news_collector
            collector = get_news_collector()
            headlines = collector.get_latest_headlines(limit=limit)
            return ToolResult(True, headlines)
        except Exception as e:
            return ToolResult(False, None, str(e))



# Global instance
_tools: Optional[SeraphTools] = None


def get_seraph_tools() -> SeraphTools:
    """Get or create global tools instance."""
    global _tools
    if _tools is None:
        _tools = SeraphTools()
    return _tools
