# -*- coding: utf-8 -*-
"""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                        SERAPH v2.0 - CODE ARCHITECT                           ║
║                                                                               ║
║  AI-Powered Self-Modifying Code Agent for GODBRAIN Trading System             ║
║                                                                               ║
║  Capabilities:                                                                ║
║    • Natural language → Code modifications                                    ║
║    • Safe backup & rollback mechanism                                         ║
║    • Syntax validation before deploy                                          ║
║    • Config updates (legacy mode)                                             ║
║    • Strategy injection                                                       ║
║    • Module hot-patching                                                      ║
║                                                                               ║
║  Author: GODBRAIN Systems                                                     ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"""

import os
import sys
import json
import ast
import shutil
import hashlib
import subprocess
from pathlib import Path
from datetime import datetime
from typing import Optional, Dict, Any, List, Tuple
from dataclasses import dataclass, field
from enum import Enum

import requests
from dotenv import load_dotenv

# =============================================================================
# PATHS & CONFIGURATION
# =============================================================================

UNIVERSE_ROOT = Path(r"C:\godbrain-universe")
QUANTUM_ROOT = Path(r"C:\godbrain-quantum")
ULTIMATE_PACK = QUANTUM_ROOT / "ultimate_pack"

# Config files (legacy)
HUMAN_BIAS_PATH = QUANTUM_ROOT / "human_bias.json"
HUMAN_CONTROL_PATH = QUANTUM_ROOT / "human_control.json"

# Seraph workspace
SERAPH_DIR = QUANTUM_ROOT / "seraph"
BACKUP_DIR = SERAPH_DIR / "backups"
PATCH_HISTORY = SERAPH_DIR / "patch_history.json"
SERAPH_LOG = SERAPH_DIR / "seraph.log"

# Load environment
load_dotenv(UNIVERSE_ROOT / ".env")
load_dotenv(QUANTUM_ROOT / ".env")


# =============================================================================
# ENUMS & DATA CLASSES
# =============================================================================

class CommandType(Enum):
    CONFIG_UPDATE = "config_update"       # Legacy: JSON config changes
    CODE_MODIFY = "code_modify"           # Modify existing code
    CODE_INJECT = "code_inject"           # Add new code/function
    FILE_CREATE = "file_create"           # Create new file
    STRATEGY_UPDATE = "strategy_update"   # Update trading strategy
    MODULE_PATCH = "module_patch"         # Patch ultimate pack module
    SYSTEM_COMMAND = "system_command"     # PM2 restart etc
    QUERY = "query"                       # Just asking question
    UNKNOWN = "unknown"


@dataclass
class SeraphCommand:
    """Parsed command from Claude."""
    command_type: CommandType
    target_file: Optional[str] = None
    target_function: Optional[str] = None
    action: Optional[str] = None
    code_changes: Optional[str] = None
    parameters: Dict[str, Any] = field(default_factory=dict)
    explanation: str = ""
    confidence: float = 0.0
    requires_restart: bool = False


@dataclass
class PatchResult:
    """Result of a code patch operation."""
    success: bool
    message: str
    backup_path: Optional[str] = None
    changes_made: List[str] = field(default_factory=list)
    rollback_available: bool = False


# =============================================================================
# UTILITY FUNCTIONS
# =============================================================================

def log(message: str, level: str = "INFO"):
    """Log to file and console."""
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    log_line = f"[{timestamp}] [{level}] {message}"
    print(log_line)
    
    SERAPH_DIR.mkdir(parents=True, exist_ok=True)
    with open(SERAPH_LOG, "a", encoding="utf-8") as f:
        f.write(log_line + "\n")


def load_json(path: Path, default: Any) -> Any:
    """Load JSON file with default fallback."""
    try:
        if path.exists():
            with open(path, "r", encoding="utf-8") as f:
                return json.load(f)
    except Exception as e:
        log(f"JSON load error {path}: {e}", "WARN")
    return default


def save_json(path: Path, data: Any) -> None:
    """Save JSON file."""
    path.parent.mkdir(parents=True, exist_ok=True)
    with open(path, "w", encoding="utf-8") as f:
        json.dump(data, f, indent=2, ensure_ascii=False)


def file_hash(path: Path) -> str:
    """Get MD5 hash of file."""
    if not path.exists():
        return ""
    return hashlib.md5(path.read_bytes()).hexdigest()


def validate_python_syntax(code: str) -> Tuple[bool, str]:
    """Validate Python syntax."""
    try:
        ast.parse(code)
        return True, "Syntax OK"
    except SyntaxError as e:
        return False, f"Syntax Error at line {e.lineno}: {e.msg}"


def validate_python_file(path: Path) -> Tuple[bool, str]:
    """Validate a Python file's syntax."""
    if not path.exists():
        return False, "File does not exist"
    try:
        code = path.read_text(encoding="utf-8")
        return validate_python_syntax(code)
    except Exception as e:
        return False, str(e)


# =============================================================================
# BACKUP & ROLLBACK SYSTEM
# =============================================================================

class BackupManager:
    """Manages file backups and rollback."""
    
    def __init__(self):
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        self.history = load_json(PATCH_HISTORY, {"patches": []})
    
    def create_backup(self, file_path: Path, patch_id: str) -> Optional[Path]:
        """Create backup of a file before modification."""
        if not file_path.exists():
            return None
        
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        backup_name = f"{file_path.stem}_{timestamp}_{patch_id}{file_path.suffix}"
        backup_path = BACKUP_DIR / backup_name
        
        shutil.copy2(file_path, backup_path)
        log(f"Backup created: {backup_path}")
        
        return backup_path
    
    def record_patch(self, patch_id: str, target_file: str, backup_path: Optional[Path],
                     description: str, changes: List[str]) -> None:
        """Record a patch in history."""
        record = {
            "id": patch_id,
            "timestamp": datetime.now().isoformat(),
            "target_file": target_file,
            "backup_path": str(backup_path) if backup_path else None,
            "description": description,
            "changes": changes,
            "rolled_back": False
        }
        self.history["patches"].append(record)
        save_json(PATCH_HISTORY, self.history)
    
    def rollback(self, patch_id: str) -> Tuple[bool, str]:
        """Rollback a specific patch."""
        for patch in reversed(self.history["patches"]):
            if patch["id"] == patch_id and not patch["rolled_back"]:
                backup_path = Path(patch["backup_path"]) if patch["backup_path"] else None
                target_path = Path(patch["target_file"])
                
                if backup_path and backup_path.exists():
                    shutil.copy2(backup_path, target_path)
                    patch["rolled_back"] = True
                    save_json(PATCH_HISTORY, self.history)
                    return True, f"Rolled back {target_path.name} from {backup_path.name}"
                else:
                    return False, "Backup file not found"
        
        return False, f"Patch {patch_id} not found or already rolled back"
    
    def get_recent_patches(self, count: int = 10) -> List[dict]:
        """Get recent patches."""
        return self.history["patches"][-count:]


# =============================================================================
# CLAUDE API - CODE ARCHITECT
# =============================================================================

class ClaudeCodeArchitect:
    """Claude API interface for code modifications."""
    
    SYSTEM_PROMPT = '''You are SERAPH v2.0 - the Code Architect for GODBRAIN trading system.

## YOUR ROLE
You receive natural language commands (Turkish or English) and translate them into precise code modifications.

## SYSTEM STRUCTURE
```
C:\\godbrain-quantum\\
├── agg.py                          # Main aggregator (entry point)
├── human_bias.json                 # Risk mode config
├── human_control.json              # Kill switch, limits
├── ultimate_pack/
│   ├── regime/
│   │   └── regime_detector.py      # Market regime detection
│   ├── filters/
│   │   └── signal_filter.py        # Anti-whipsaw filter
│   ├── integration/
│   │   └── ultimate_aggregator.py  # Signal aggregation
│   ├── feeds/
│   │   └── data_feeds.py           # Data feed integrations
│   └── ultimate_connector.py       # Main connector
└── seraph/
    └── seraph_v2.py                # This file (you)
```

## RESPONSE FORMAT
You MUST respond with a SINGLE JSON object:

```json
{
  "command_type": "config_update|code_modify|code_inject|file_create|strategy_update|module_patch|system_command|query",
  "target_file": "relative/path/to/file.py or null",
  "target_function": "function_name or null",
  "action": "replace|insert_before|insert_after|append|delete|create",
  "code_changes": "the actual code to add/modify (properly escaped)",
  "parameters": {
    "search_pattern": "code to find (for replace)",
    "new_value": "replacement value",
    "line_number": 123,
    "any_other_params": "..."
  },
  "explanation": "What this change does",
  "confidence": 0.95,
  "requires_restart": true
}
```

## COMMAND TYPE MAPPING

### CONFIG_UPDATE (legacy)
For risk/control changes:
- "agresif moda geç" → bias_mode: AGGRESSIVE
- "kill switch aç" → kill_switch: true
- "günde max 100 dolar" → max_daily_loss_usd: 100

### CODE_MODIFY
For changing existing code:
- "ADX threshold'u 30 yap" → modify regime_detector.py
- "cooldown süresini 10 dakika yap" → modify constants

### CODE_INJECT
For adding new functions/classes:
- "yeni bir filtre ekle" → add function to existing file

### MODULE_PATCH
For updating ultimate pack modules:
- "VPIN bucket size'ı 50 yap" → patch vpin_analyzer.py
- "regime detector'a yeni state ekle" → patch regime_detector.py

### STRATEGY_UPDATE
For trading logic changes:
- "trend following yerine mean reversion kullan"
- "conviction threshold'u 0.6 yap"

### SYSTEM_COMMAND
For system operations:
- "sistemi yeniden başlat" → pm2 restart
- "logları göster" → show logs

### QUERY
For questions:
- "mevcut ayarlar ne?"
- "son 5 patch neydi?"

## IMPORTANT RULES
1. ALWAYS return valid JSON, nothing else
2. For code_changes, use proper Python syntax
3. Escape special characters in strings
4. Be precise with file paths
5. Set confidence based on how sure you are
6. requires_restart = true for any code changes

## EXAMPLES

User: "ADX threshold'u 30'a çıkar"
```json
{
  "command_type": "code_modify",
  "target_file": "ultimate_pack/regime/regime_detector.py",
  "target_function": null,
  "action": "replace",
  "code_changes": "ADX_TREND_ENTER = 30",
  "parameters": {
    "search_pattern": "ADX_TREND_ENTER = 28"
  },
  "explanation": "ADX trend entry threshold'u 28'den 30'a yükseltiliyor",
  "confidence": 0.95,
  "requires_restart": true
}
```

User: "regime cooldown süresini 10 dakika yap"
```json
{
  "command_type": "code_modify",
  "target_file": "ultimate_pack/regime/regime_detector.py",
  "target_function": null,
  "action": "replace",
  "code_changes": "REGIME_COOLDOWN_SECONDS = 600  # 10 minutes",
  "parameters": {
    "search_pattern": "REGIME_COOLDOWN_SECONDS = 300"
  },
  "explanation": "Regime değişim cooldown'u 5 dakikadan 10 dakikaya çıkarılıyor",
  "confidence": 0.95,
  "requires_restart": true
}
```

User: "agresif moda geç"
```json
{
  "command_type": "config_update",
  "target_file": "human_bias.json",
  "target_function": null,
  "action": "update",
  "code_changes": null,
  "parameters": {
    "bias_mode": "AGGRESSIVE",
    "risk_adjustment": 1.3
  },
  "explanation": "Sistem agresif moda geçiriliyor, risk çarpanı 1.3x",
  "confidence": 0.98,
  "requires_restart": false
}
```

User: "yeni bir trailing stop modülü ekle"
```json
{
  "command_type": "file_create",
  "target_file": "ultimate_pack/stops/trailing_stop.py",
  "target_function": null,
  "action": "create",
  "code_changes": "#!/usr/bin/env python3\\n\\"\\"\\"Trailing Stop Module\\"\\"\\"\\n\\nclass TrailingStop:\\n    def __init__(self, activation_pct=1.0, trail_pct=0.5):\\n        self.activation_pct = activation_pct\\n        self.trail_pct = trail_pct\\n        self.highest_price = None\\n        self.activated = False\\n\\n    def update(self, current_price, entry_price):\\n        pnl_pct = (current_price - entry_price) / entry_price * 100\\n        \\n        if pnl_pct >= self.activation_pct:\\n            self.activated = True\\n            \\n        if self.activated:\\n            if self.highest_price is None or current_price > self.highest_price:\\n                self.highest_price = current_price\\n            \\n            trail_level = self.highest_price * (1 - self.trail_pct / 100)\\n            if current_price <= trail_level:\\n                return True  # Trigger stop\\n        \\n        return False",
  "parameters": {},
  "explanation": "Trailing stop modülü oluşturuluyor - %1 aktivasyon, %0.5 trail",
  "confidence": 0.90,
  "requires_restart": true
}
```
'''

    def __init__(self):
        self.api_key = os.getenv("SERAPH_LLM_KEY") or os.getenv("ANTHROPIC_API_KEY")
        self.model = os.getenv("SERAPH_LLM_MODEL", "claude-sonnet-4-20250514")
        
        if not self.api_key:
            log("WARNING: No API key found (SERAPH_LLM_KEY or ANTHROPIC_API_KEY)", "WARN")
    
    def parse_command(self, user_input: str, context: str = "") -> SeraphCommand:
        """Send command to Claude and parse response."""
        
        if not self.api_key:
            return SeraphCommand(
                command_type=CommandType.UNKNOWN,
                explanation="API key not configured"
            )
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        # Add context about current state
        full_input = user_input
        if context:
            full_input = f"Current system context:\n{context}\n\nUser command: {user_input}"
        
        payload = {
            "model": self.model,
            "max_tokens": 2048,
            "system": self.SYSTEM_PROMPT,
            "messages": [
                {"role": "user", "content": full_input}
            ]
        }
        
        try:
            resp = requests.post(
                "https://api.anthropic.com/v1/messages",
                headers=headers,
                json=payload,
                timeout=30
            )
            resp.raise_for_status()
            
            data = resp.json()
            content = data.get("content", [])
            
            if not content:
                raise ValueError("Empty response from Claude")
            
            raw_text = content[0].get("text", "").strip()
            
            # Parse JSON from response
            # Handle potential markdown code blocks
            if "```json" in raw_text:
                raw_text = raw_text.split("```json")[1].split("```")[0].strip()
            elif "```" in raw_text:
                raw_text = raw_text.split("```")[1].split("```")[0].strip()
            
            parsed = json.loads(raw_text)
            
            return SeraphCommand(
                command_type=CommandType(parsed.get("command_type", "unknown")),
                target_file=parsed.get("target_file"),
                target_function=parsed.get("target_function"),
                action=parsed.get("action"),
                code_changes=parsed.get("code_changes"),
                parameters=parsed.get("parameters", {}),
                explanation=parsed.get("explanation", ""),
                confidence=parsed.get("confidence", 0.5),
                requires_restart=parsed.get("requires_restart", False)
            )
            
        except requests.exceptions.RequestException as e:
            log(f"API request failed: {e}", "ERROR")
            return SeraphCommand(
                command_type=CommandType.UNKNOWN,
                explanation=f"API error: {e}"
            )
        except json.JSONDecodeError as e:
            log(f"JSON parse error: {e}", "ERROR")
            return SeraphCommand(
                command_type=CommandType.UNKNOWN,
                explanation=f"Invalid JSON response: {e}"
            )
        except Exception as e:
            log(f"Unexpected error: {e}", "ERROR")
            return SeraphCommand(
                command_type=CommandType.UNKNOWN,
                explanation=str(e)
            )


# =============================================================================
# CODE MODIFICATION ENGINE
# =============================================================================

class CodeModifier:
    """Handles actual code modifications."""
    
    def __init__(self):
        self.backup_manager = BackupManager()
    
    def generate_patch_id(self) -> str:
        """Generate unique patch ID."""
        return datetime.now().strftime("%Y%m%d%H%M%S") + "_" + hashlib.md5(
            str(datetime.now().timestamp()).encode()
        ).hexdigest()[:6]
    
    def modify_file(self, command: SeraphCommand) -> PatchResult:
        """Modify an existing file."""
        
        if not command.target_file:
            return PatchResult(False, "No target file specified")
        
        target_path = QUANTUM_ROOT / command.target_file
        
        if not target_path.exists():
            return PatchResult(False, f"File not found: {target_path}")
        
        patch_id = self.generate_patch_id()
        
        # Create backup
        backup_path = self.backup_manager.create_backup(target_path, patch_id)
        
        try:
            content = target_path.read_text(encoding="utf-8")
            original_content = content
            changes_made = []
            
            if command.action == "replace":
                search_pattern = command.parameters.get("search_pattern", "")
                if search_pattern and search_pattern in content:
                    content = content.replace(search_pattern, command.code_changes, 1)
                    changes_made.append(f"Replaced: {search_pattern[:50]}...")
                else:
                    return PatchResult(
                        False, 
                        f"Search pattern not found: {search_pattern[:100]}...",
                        str(backup_path) if backup_path else None
                    )
            
            elif command.action == "append":
                content = content + "\n\n" + command.code_changes
                changes_made.append("Appended new code")
            
            elif command.action == "insert_after":
                search_pattern = command.parameters.get("search_pattern", "")
                if search_pattern and search_pattern in content:
                    idx = content.find(search_pattern) + len(search_pattern)
                    # Find end of line
                    newline_idx = content.find("\n", idx)
                    if newline_idx == -1:
                        newline_idx = len(content)
                    content = content[:newline_idx] + "\n" + command.code_changes + content[newline_idx:]
                    changes_made.append(f"Inserted after: {search_pattern[:50]}...")
                else:
                    return PatchResult(False, f"Pattern not found for insert_after")
            
            elif command.action == "insert_before":
                search_pattern = command.parameters.get("search_pattern", "")
                if search_pattern and search_pattern in content:
                    idx = content.find(search_pattern)
                    content = content[:idx] + command.code_changes + "\n" + content[idx:]
                    changes_made.append(f"Inserted before: {search_pattern[:50]}...")
                else:
                    return PatchResult(False, f"Pattern not found for insert_before")
            
            # Validate syntax for Python files
            if target_path.suffix == ".py":
                valid, error = validate_python_syntax(content)
                if not valid:
                    return PatchResult(
                        False,
                        f"Syntax validation failed: {error}",
                        str(backup_path) if backup_path else None,
                        rollback_available=True
                    )
            
            # Write modified content
            target_path.write_text(content, encoding="utf-8")
            
            # Record patch
            self.backup_manager.record_patch(
                patch_id,
                str(target_path),
                backup_path,
                command.explanation,
                changes_made
            )
            
            return PatchResult(
                True,
                f"Successfully modified {target_path.name}",
                str(backup_path) if backup_path else None,
                changes_made,
                rollback_available=True
            )
            
        except Exception as e:
            log(f"Modification error: {e}", "ERROR")
            # Attempt restore from backup
            if backup_path and backup_path.exists():
                shutil.copy2(backup_path, target_path)
            return PatchResult(False, f"Error: {e}", rollback_available=False)
    
    def create_file(self, command: SeraphCommand) -> PatchResult:
        """Create a new file."""
        
        if not command.target_file:
            return PatchResult(False, "No target file specified")
        
        target_path = QUANTUM_ROOT / command.target_file
        
        if target_path.exists():
            return PatchResult(False, f"File already exists: {target_path}")
        
        patch_id = self.generate_patch_id()
        
        try:
            # Create parent directories
            target_path.parent.mkdir(parents=True, exist_ok=True)
            
            # Validate syntax for Python files
            if target_path.suffix == ".py" and command.code_changes:
                valid, error = validate_python_syntax(command.code_changes)
                if not valid:
                    return PatchResult(False, f"Syntax validation failed: {error}")
            
            # Write file
            target_path.write_text(command.code_changes or "", encoding="utf-8")
            
            # Create __init__.py if needed
            init_path = target_path.parent / "__init__.py"
            if not init_path.exists():
                init_path.touch()
            
            # Record patch
            self.backup_manager.record_patch(
                patch_id,
                str(target_path),
                None,  # No backup for new files
                command.explanation,
                [f"Created new file: {target_path.name}"]
            )
            
            return PatchResult(
                True,
                f"Successfully created {target_path}",
                changes_made=[f"Created: {target_path.name}"]
            )
            
        except Exception as e:
            log(f"File creation error: {e}", "ERROR")
            return PatchResult(False, f"Error: {e}")
    
    def update_config(self, command: SeraphCommand) -> PatchResult:
        """Update JSON config files (legacy mode)."""
        
        changes_made = []
        params = command.parameters
        
        # Load current configs
        bias = load_json(HUMAN_BIAS_PATH, {"bias_mode": "NEUTRAL", "risk_adjustment": 1.0})
        ctrl = load_json(HUMAN_CONTROL_PATH, {
            "kill_switch": False,
            "block_new_entries": False,
            "max_daily_loss_usd": 200.0,
            "max_open_positions": 2
        })
        
        # Update bias config
        if "bias_mode" in params:
            old_val = bias.get("bias_mode")
            bias["bias_mode"] = params["bias_mode"]
            changes_made.append(f"bias_mode: {old_val} → {params['bias_mode']}")
        
        if "risk_adjustment" in params:
            old_val = bias.get("risk_adjustment")
            bias["risk_adjustment"] = float(params["risk_adjustment"])
            changes_made.append(f"risk_adjustment: {old_val} → {params['risk_adjustment']}")
        
        # Update control config
        if "kill_switch" in params:
            old_val = ctrl.get("kill_switch")
            ctrl["kill_switch"] = bool(params["kill_switch"])
            changes_made.append(f"kill_switch: {old_val} → {params['kill_switch']}")
        
        if "block_new_entries" in params:
            old_val = ctrl.get("block_new_entries")
            ctrl["block_new_entries"] = bool(params["block_new_entries"])
            changes_made.append(f"block_new_entries: {old_val} → {params['block_new_entries']}")
        
        if "max_daily_loss_usd" in params:
            old_val = ctrl.get("max_daily_loss_usd")
            ctrl["max_daily_loss_usd"] = float(params["max_daily_loss_usd"])
            changes_made.append(f"max_daily_loss_usd: {old_val} → {params['max_daily_loss_usd']}")
        
        if "max_open_positions" in params:
            old_val = ctrl.get("max_open_positions")
            ctrl["max_open_positions"] = int(params["max_open_positions"])
            changes_made.append(f"max_open_positions: {old_val} → {params['max_open_positions']}")
        
        # Save configs
        save_json(HUMAN_BIAS_PATH, bias)
        save_json(HUMAN_CONTROL_PATH, ctrl)
        
        return PatchResult(
            True,
            "Config updated successfully",
            changes_made=changes_made
        )
    
    def execute_system_command(self, command: SeraphCommand) -> PatchResult:
        """Execute system commands (PM2, etc)."""
        
        action = command.action or command.parameters.get("action", "")
        
        if action in ["restart", "reload"]:
            try:
                result = subprocess.run(
                    ["pm2", "restart", "godbrain-quantum"],
                    capture_output=True,
                    text=True,
                    timeout=30
                )
                if result.returncode == 0:
                    return PatchResult(True, "System restarted via PM2", changes_made=["pm2 restart"])
                else:
                    return PatchResult(False, f"PM2 restart failed: {result.stderr}")
            except Exception as e:
                return PatchResult(False, f"Command execution failed: {e}")
        
        elif action == "status":
            try:
                result = subprocess.run(
                    ["pm2", "status"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                return PatchResult(True, f"PM2 Status:\n{result.stdout}")
            except Exception as e:
                return PatchResult(False, f"Status check failed: {e}")
        
        elif action == "logs":
            try:
                result = subprocess.run(
                    ["pm2", "logs", "godbrain-quantum", "--lines", "50", "--nostream"],
                    capture_output=True,
                    text=True,
                    timeout=10
                )
                return PatchResult(True, f"Recent logs:\n{result.stdout}")
            except Exception as e:
                return PatchResult(False, f"Log retrieval failed: {e}")
        
        return PatchResult(False, f"Unknown system action: {action}")


# =============================================================================
# MAIN SERAPH ENGINE
# =============================================================================

class SeraphEngine:
    """Main SERAPH v2.0 engine."""
    
    def __init__(self):
        # Ensure directories exist
        SERAPH_DIR.mkdir(parents=True, exist_ok=True)
        BACKUP_DIR.mkdir(parents=True, exist_ok=True)
        
        self.claude = ClaudeCodeArchitect()
        self.modifier = CodeModifier()
        
        log("SERAPH v2.0 Engine initialized", "INFO")
    
    def get_system_context(self) -> str:
        """Get current system context for Claude."""
        
        context_parts = []
        
        # Current configs
        bias = load_json(HUMAN_BIAS_PATH, {})
        ctrl = load_json(HUMAN_CONTROL_PATH, {})
        
        context_parts.append(f"Current bias config: {json.dumps(bias)}")
        context_parts.append(f"Current control config: {json.dumps(ctrl)}")
        
        # Recent patches
        patches = self.modifier.backup_manager.get_recent_patches(5)
        if patches:
            patch_summary = [f"- {p['timestamp']}: {p['description']}" for p in patches]
            context_parts.append(f"Recent patches:\n" + "\n".join(patch_summary))
        
        # Check if key files exist
        key_files = [
            "agg.py",
            "ultimate_pack/regime/regime_detector.py",
            "ultimate_pack/filters/signal_filter.py",
            "ultimate_pack/ultimate_connector.py"
        ]
        
        existing = [f for f in key_files if (QUANTUM_ROOT / f).exists()]
        context_parts.append(f"Existing key files: {existing}")
        
        return "\n".join(context_parts)
    
    def process_command(self, user_input: str) -> Tuple[bool, str]:
        """Process a user command."""
        
        log(f"Processing command: {user_input}", "INFO")
        
        # Get context
        context = self.get_system_context()
        
        # Parse command via Claude
        command = self.claude.parse_command(user_input, context)
        
        log(f"Parsed command type: {command.command_type.value}", "INFO")
        log(f"Explanation: {command.explanation}", "INFO")
        log(f"Confidence: {command.confidence}", "INFO")
        
        # Low confidence warning
        if command.confidence < 0.7:
            warning = f"⚠️ Low confidence ({command.confidence:.0%}). Proceed? (y/n): "
            confirm = input(warning).strip().lower()
            if confirm != 'y':
                return False, "Command cancelled by user"
        
        # Execute based on command type
        result: PatchResult
        
        if command.command_type == CommandType.CONFIG_UPDATE:
            result = self.modifier.update_config(command)
        
        elif command.command_type == CommandType.CODE_MODIFY:
            result = self.modifier.modify_file(command)
        
        elif command.command_type in [CommandType.FILE_CREATE, CommandType.CODE_INJECT]:
            result = self.modifier.create_file(command)
        
        elif command.command_type == CommandType.MODULE_PATCH:
            result = self.modifier.modify_file(command)
        
        elif command.command_type == CommandType.STRATEGY_UPDATE:
            result = self.modifier.modify_file(command)
        
        elif command.command_type == CommandType.SYSTEM_COMMAND:
            result = self.modifier.execute_system_command(command)
        
        elif command.command_type == CommandType.QUERY:
            # Just return explanation for queries
            return True, command.explanation
        
        else:
            return False, f"Unknown command type: {command.command_type.value}\n{command.explanation}"
        
        # Log result
        log(f"Result: {'SUCCESS' if result.success else 'FAILED'} - {result.message}", 
            "INFO" if result.success else "ERROR")
        
        # Handle restart requirement
        if result.success and command.requires_restart:
            print("\n⚠️ This change requires a system restart.")
            restart = input("Restart now? (y/n): ").strip().lower()
            if restart == 'y':
                restart_cmd = SeraphCommand(
                    command_type=CommandType.SYSTEM_COMMAND,
                    action="restart"
                )
                self.modifier.execute_system_command(restart_cmd)
        
        # Build response
        response_parts = [
            f"{'✅' if result.success else '❌'} {result.message}",
            f"📝 {command.explanation}"
        ]
        
        if result.changes_made:
            response_parts.append("Changes:")
            for change in result.changes_made:
                response_parts.append(f"  • {change}")
        
        if result.backup_path:
            response_parts.append(f"💾 Backup: {result.backup_path}")
        
        return result.success, "\n".join(response_parts)
    
    def rollback_last(self) -> Tuple[bool, str]:
        """Rollback the last patch."""
        patches = self.modifier.backup_manager.get_recent_patches(1)
        if not patches:
            return False, "No patches to rollback"
        
        last_patch = patches[-1]
        if last_patch["rolled_back"]:
            return False, "Last patch already rolled back"
        
        success, msg = self.modifier.backup_manager.rollback(last_patch["id"])
        return success, msg
    
    def show_status(self) -> str:
        """Show current system status."""
        
        lines = [
            "╔════════════════════════════════════════╗",
            "║         SERAPH v2.0 STATUS             ║",
            "╚════════════════════════════════════════╝",
            ""
        ]
        
        # Configs
        bias = load_json(HUMAN_BIAS_PATH, {})
        ctrl = load_json(HUMAN_CONTROL_PATH, {})
        
        lines.append("📊 Current Configuration:")
        lines.append(f"  • Bias Mode: {bias.get('bias_mode', 'N/A')}")
        lines.append(f"  • Risk Adjustment: {bias.get('risk_adjustment', 'N/A')}")
        lines.append(f"  • Kill Switch: {ctrl.get('kill_switch', 'N/A')}")
        lines.append(f"  • Max Daily Loss: ${ctrl.get('max_daily_loss_usd', 'N/A')}")
        lines.append(f"  • Max Positions: {ctrl.get('max_open_positions', 'N/A')}")
        lines.append("")
        
        # Recent patches
        patches = self.modifier.backup_manager.get_recent_patches(5)
        lines.append(f"📦 Recent Patches ({len(patches)}):")
        for p in patches:
            status = "🔄" if p.get("rolled_back") else "✅"
            lines.append(f"  {status} [{p['id']}] {p['description'][:50]}")
        
        return "\n".join(lines)


# =============================================================================
# INTERACTIVE CLI
# =============================================================================

def print_banner():
    """Print SERAPH banner."""
    print("""
╔═══════════════════════════════════════════════════════════════════════════════╗
║                                                                               ║
║   ███████╗███████╗██████╗  █████╗ ██████╗ ██╗  ██╗    ██╗   ██╗██████╗       ║
║   ██╔════╝██╔════╝██╔══██╗██╔══██╗██╔══██╗██║  ██║    ██║   ██║╚════██╗      ║
║   ███████╗█████╗  ██████╔╝███████║██████╔╝███████║    ██║   ██║ █████╔╝      ║
║   ╚════██║██╔══╝  ██╔══██╗██╔══██║██╔═══╝ ██╔══██║    ╚██╗ ██╔╝██╔═══╝       ║
║   ███████║███████╗██║  ██║██║  ██║██║     ██║  ██║     ╚████╔╝ ███████╗      ║
║   ╚══════╝╚══════╝╚═╝  ╚═╝╚═╝  ╚═╝╚═╝     ╚═╝  ╚═╝      ╚═══╝  ╚══════╝      ║
║                                                                               ║
║                    CODE ARCHITECT - AI Self-Modification Engine               ║
║                                                                               ║
╚═══════════════════════════════════════════════════════════════════════════════╝
    """)


def main():
    """Main entry point."""
    
    print_banner()
    
    engine = SeraphEngine()
    
    print(f"🌌 Universe Root : {UNIVERSE_ROOT}")
    print(f"⚛️  Quantum Root  : {QUANTUM_ROOT}")
    print(f"📁 Seraph Dir    : {SERAPH_DIR}")
    print()
    print("Commands:")
    print("  • Natural language commands for code/config changes")
    print("  • 'status' - Show current status")
    print("  • 'rollback' - Undo last patch")
    print("  • 'history' - Show patch history")
    print("  • 'exit/quit' - Exit SERAPH")
    print("─" * 60)
    
    while True:
        try:
            cmd = input("\n🧠 SERAPH> ").strip()
        except (EOFError, KeyboardInterrupt):
            print("\n👋 SERAPH signing off...")
            break
        
        if not cmd:
            continue
        
        cmd_lower = cmd.lower()
        
        # Built-in commands
        if cmd_lower in ("exit", "quit", "q", "çık"):
            print("👋 SERAPH signing off...")
            break
        
        elif cmd_lower == "status":
            print(engine.show_status())
            continue
        
        elif cmd_lower == "rollback":
            success, msg = engine.rollback_last()
            print(f"{'✅' if success else '❌'} {msg}")
            continue
        
        elif cmd_lower == "history":
            patches = engine.modifier.backup_manager.get_recent_patches(10)
            print("\n📜 Patch History:")
            for p in patches:
                status = "🔄 ROLLED BACK" if p.get("rolled_back") else "✅ APPLIED"
                print(f"  [{p['id']}] {status}")
                print(f"      📄 {p['target_file']}")
                print(f"      📝 {p['description']}")
                print()
            continue
        
        # Process natural language command
        print("⏳ Processing...")
        success, response = engine.process_command(cmd)
        print()
        print(response)


if __name__ == "__main__":
    main()