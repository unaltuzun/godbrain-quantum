# ==============================================================================
# SERAPH BRAIN - Multi-LLM Intelligence Layer
# ==============================================================================
"""
Hybrid AI Brain:
- Local LLM (Ollama) for unlimited free inference
- Cloud LLM (Claude) for premium decisions with cache
- Smart router for optimal cost/quality balance
"""

from .local_llm import LocalLLM
from .cloud_llm import CloudLLM  
from .router import BrainRouter

__all__ = ["LocalLLM", "CloudLLM", "BrainRouter"]

