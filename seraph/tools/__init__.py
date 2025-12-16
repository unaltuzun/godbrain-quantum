# ==============================================================================
# SERAPH TOOLS - Function Calling Interface
# ==============================================================================
"""
Seraph'ın kullanabileceği araçlar.
Her araç belirli bir görevi yerine getirir ve Seraph'a veri sağlar.
"""

from .market import get_market_data, get_market_summary
from .system import get_system_state, get_dna_params, get_voltran_signals

# Import main SeraphTools class from the parent module
# This fixes the import conflict where Python loads this directory instead of tools.py
import sys
from pathlib import Path
_parent = Path(__file__).parent.parent / "tools.py"
if _parent.exists():
    import importlib.util
    spec = importlib.util.spec_from_file_location("seraph_tools_main", _parent)
    _module = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(_module)
    SeraphTools = _module.SeraphTools
    ToolResult = _module.ToolResult
    Tool = _module.Tool
else:
    SeraphTools = None
    ToolResult = None
    Tool = None

__all__ = [
    "get_market_data",
    "get_market_summary", 
    "get_system_state",
    "get_dna_params",
    "get_voltran_signals",
    "SeraphTools",
    "ToolResult",
    "Tool"
]
