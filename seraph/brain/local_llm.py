# ==============================================================================
# LOCAL LLM - Ollama Integration (Unlimited Free Inference)
# ==============================================================================
"""
Local LLM wrapper for Ollama.
Supports: Mistral, Llama3, Phi, Qwen, DeepSeek, etc.

Weridata deployment:
- curl -fsSL https://ollama.com/install.sh | sh
- ollama pull mistral (or llama3, qwen2.5)
"""

import json
import logging
import time
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
import requests

logger = logging.getLogger("seraph.brain.local")


@dataclass
class LocalResponse:
    """Response from local LLM"""
    content: str
    model: str
    tokens: int
    latency_ms: float
    success: bool
    error: Optional[str] = None


class LocalLLM:
    """
    Ollama-based local LLM.
    
    Benefits:
    - Unlimited free inference
    - No API costs
    - Privacy (data stays local)
    - Fast for simple queries
    
    Limitations:
    - Less capable than Claude
    - Needs GPU for best performance
    """
    
    DEFAULT_MODELS = ["mistral", "llama3", "qwen2.5", "phi3", "deepseek-coder"]
    
    def __init__(
        self,
        base_url: str = "http://localhost:11434",
        model: str = "mistral",
        timeout: int = 60
    ):
        self.base_url = base_url.rstrip("/")
        self.model = model
        self.timeout = timeout
        self._available_models: List[str] = []
        
    def is_available(self) -> bool:
        """Check if Ollama is running and accessible"""
        try:
            r = requests.get(f"{self.base_url}/api/tags", timeout=2)
            if r.status_code == 200:
                data = r.json()
                self._available_models = [m["name"] for m in data.get("models", [])]
                return True
        except Exception:
            pass
        return False
    
    def list_models(self) -> List[str]:
        """List available models"""
        if not self._available_models:
            self.is_available()
        return self._available_models
    
    def pull_model(self, model: str) -> bool:
        """Pull a model (download if not exists)"""
        try:
            r = requests.post(
                f"{self.base_url}/api/pull",
                json={"name": model},
                timeout=600  # 10 min for download
            )
            return r.status_code == 200
        except Exception as e:
            logger.error(f"Failed to pull model {model}: {e}")
            return False
    
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        stream: bool = False
    ) -> LocalResponse:
        """
        Generate response from local LLM.
        
        Args:
            prompt: User prompt
            system: System prompt (optional)
            temperature: Creativity (0-1)
            max_tokens: Max response tokens
            stream: Stream response (not implemented)
        
        Returns:
            LocalResponse with content and metadata
        """
        start_time = time.time()
        
        payload = {
            "model": self.model,
            "prompt": prompt,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        if system:
            payload["system"] = system
        
        try:
            r = requests.post(
                f"{self.base_url}/api/generate",
                json=payload,
                timeout=self.timeout
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if r.status_code == 200:
                data = r.json()
                return LocalResponse(
                    content=data.get("response", ""),
                    model=self.model,
                    tokens=data.get("eval_count", 0),
                    latency_ms=latency_ms,
                    success=True
                )
            else:
                return LocalResponse(
                    content="",
                    model=self.model,
                    tokens=0,
                    latency_ms=latency_ms,
                    success=False,
                    error=f"HTTP {r.status_code}: {r.text[:200]}"
                )
                
        except requests.Timeout:
            return LocalResponse(
                content="",
                model=self.model,
                tokens=0,
                latency_ms=self.timeout * 1000,
                success=False,
                error="Timeout"
            )
        except Exception as e:
            return LocalResponse(
                content="",
                model=self.model,
                tokens=0,
                latency_ms=(time.time() - start_time) * 1000,
                success=False,
                error=str(e)
            )
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        temperature: float = 0.7,
        max_tokens: int = 1024
    ) -> LocalResponse:
        """
        Chat completion (multi-turn conversation).
        
        Args:
            messages: List of {"role": "user/assistant", "content": "..."}
            temperature: Creativity
            max_tokens: Max response tokens
        
        Returns:
            LocalResponse
        """
        start_time = time.time()
        
        payload = {
            "model": self.model,
            "messages": messages,
            "stream": False,
            "options": {
                "temperature": temperature,
                "num_predict": max_tokens
            }
        }
        
        try:
            r = requests.post(
                f"{self.base_url}/api/chat",
                json=payload,
                timeout=self.timeout
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if r.status_code == 200:
                data = r.json()
                return LocalResponse(
                    content=data.get("message", {}).get("content", ""),
                    model=self.model,
                    tokens=data.get("eval_count", 0),
                    latency_ms=latency_ms,
                    success=True
                )
            else:
                return LocalResponse(
                    content="",
                    model=self.model,
                    tokens=0,
                    latency_ms=latency_ms,
                    success=False,
                    error=f"HTTP {r.status_code}"
                )
                
        except Exception as e:
            return LocalResponse(
                content="",
                model=self.model,
                tokens=0,
                latency_ms=(time.time() - start_time) * 1000,
                success=False,
                error=str(e)
            )


# Singleton for easy access
_local_llm: Optional[LocalLLM] = None

def get_local_llm() -> LocalLLM:
    """Get or create local LLM instance"""
    global _local_llm
    if _local_llm is None:
        _local_llm = LocalLLM()
    return _local_llm

