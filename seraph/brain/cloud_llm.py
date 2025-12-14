# ==============================================================================
# CLOUD LLM - Claude API with Smart Caching
# ==============================================================================
"""
Claude API wrapper with:
- Semantic caching (avoid duplicate API calls)
- Request deduplication
- Cost tracking
- Graceful degradation
"""

import json
import hashlib
import time
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
import requests

logger = logging.getLogger("seraph.brain.cloud")


@dataclass
class CloudResponse:
    """Response from cloud LLM"""
    content: str
    model: str
    input_tokens: int
    output_tokens: int
    latency_ms: float
    success: bool
    from_cache: bool = False
    cost_usd: float = 0.0
    error: Optional[str] = None


class CloudLLM:
    """
    Claude API with smart caching.
    
    Cost optimization:
    - Cache identical prompts
    - Track spending
    - Use cheaper models when possible
    """
    
    API_URL = "https://api.anthropic.com/v1/messages"
    
    # Pricing per 1M tokens (approximate)
    PRICING = {
        "claude-sonnet-4-5-20250929": {"input": 3.0, "output": 15.0},
        "claude-3-5-haiku-20241022": {"input": 0.25, "output": 1.25},
        "claude-3-opus-20240229": {"input": 15.0, "output": 75.0}
    }
    
    def __init__(
        self,
        api_key: str,
        model: str = "claude-sonnet-4-5-20250929",
        cache_enabled: bool = True
    ):
        self.api_key = api_key
        self.model = model
        self.cache_enabled = cache_enabled
        
        # Simple in-memory cache (will be replaced with Redis)
        self._cache: Dict[str, CloudResponse] = {}
        
        # Stats
        self.total_requests = 0
        self.cache_hits = 0
        self.total_cost = 0.0
        self.total_tokens = 0
        
    def _cache_key(self, messages: List[Dict], system: str) -> str:
        """Generate cache key from request"""
        content = json.dumps({"messages": messages, "system": system}, sort_keys=True)
        return hashlib.sha256(content.encode()).hexdigest()[:32]
    
    def _calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD"""
        pricing = self.PRICING.get(self.model, {"input": 3.0, "output": 15.0})
        cost = (input_tokens * pricing["input"] + output_tokens * pricing["output"]) / 1_000_000
        return cost
    
    def generate(
        self,
        prompt: str,
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        use_cache: bool = True
    ) -> CloudResponse:
        """
        Generate response from Claude.
        
        Args:
            prompt: User prompt
            system: System prompt
            temperature: Creativity (0-1)
            max_tokens: Max response tokens
            use_cache: Check cache first
        
        Returns:
            CloudResponse with content and cost info
        """
        messages = [{"role": "user", "content": prompt}]
        return self.chat(messages, system, temperature, max_tokens, use_cache)
    
    def chat(
        self,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        temperature: float = 0.7,
        max_tokens: int = 1024,
        use_cache: bool = True
    ) -> CloudResponse:
        """
        Chat completion with caching.
        """
        system = system or ""
        
        # Check cache
        if use_cache and self.cache_enabled:
            cache_key = self._cache_key(messages, system)
            if cache_key in self._cache:
                self.cache_hits += 1
                cached = self._cache[cache_key]
                logger.info(f"Cache hit! Saved ${cached.cost_usd:.4f}")
                return CloudResponse(
                    content=cached.content,
                    model=cached.model,
                    input_tokens=0,
                    output_tokens=0,
                    latency_ms=0,
                    success=True,
                    from_cache=True,
                    cost_usd=0
                )
        
        start_time = time.time()
        self.total_requests += 1
        
        headers = {
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        payload = {
            "model": self.model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages
        }
        
        if system:
            payload["system"] = system
        
        try:
            r = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                timeout=60
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if r.status_code == 200:
                data = r.json()
                content = data["content"][0]["text"]
                input_tokens = data.get("usage", {}).get("input_tokens", 0)
                output_tokens = data.get("usage", {}).get("output_tokens", 0)
                
                cost = self._calculate_cost(input_tokens, output_tokens)
                self.total_cost += cost
                self.total_tokens += input_tokens + output_tokens
                
                response = CloudResponse(
                    content=content,
                    model=self.model,
                    input_tokens=input_tokens,
                    output_tokens=output_tokens,
                    latency_ms=latency_ms,
                    success=True,
                    cost_usd=cost
                )
                
                # Cache the response
                if self.cache_enabled:
                    cache_key = self._cache_key(messages, system)
                    self._cache[cache_key] = response
                
                logger.info(f"Claude response: {output_tokens} tokens, ${cost:.4f}")
                return response
                
            else:
                return CloudResponse(
                    content="",
                    model=self.model,
                    input_tokens=0,
                    output_tokens=0,
                    latency_ms=latency_ms,
                    success=False,
                    error=f"HTTP {r.status_code}: {r.text[:200]}"
                )
                
        except Exception as e:
            return CloudResponse(
                content="",
                model=self.model,
                input_tokens=0,
                output_tokens=0,
                latency_ms=(time.time() - start_time) * 1000,
                success=False,
                error=str(e)
            )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get usage statistics"""
        return {
            "total_requests": self.total_requests,
            "cache_hits": self.cache_hits,
            "cache_hit_rate": self.cache_hits / max(1, self.total_requests),
            "total_cost_usd": self.total_cost,
            "total_tokens": self.total_tokens,
            "cached_responses": len(self._cache)
        }
    
    def clear_cache(self):
        """Clear response cache"""
        self._cache.clear()
        logger.info("Cache cleared")

