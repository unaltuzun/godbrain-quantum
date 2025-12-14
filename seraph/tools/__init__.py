# ==============================================================================
# SERAPH TOOLS - Function Calling Interface
# ==============================================================================
"""
Seraph'ın kullanabileceği araçlar.
Her araç belirli bir görevi yerine getirir ve Seraph'a veri sağlar.
"""

from .market import get_market_data, get_market_summary
from .system import get_system_state, get_dna_params, get_voltran_signals

__all__ = [
    "get_market_data",
    "get_market_summary", 
    "get_system_state",
    "get_dna_params",
    "get_voltran_signals"
]

