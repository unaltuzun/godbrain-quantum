# ==============================================================================
# SERAPH AI - Autonomous Intelligence Core
# ==============================================================================
# Kurumsal modüler mimari - backward compatible
# ==============================================================================

from .core import SeraphCore, ask_seraph_v2
from .config import SeraphConfig

__version__ = "2.0.0"
__all__ = ["SeraphCore", "SeraphConfig", "ask_seraph_v2"]

