# ==============================================================================
# BRAIN ROUTER - Intelligent LLM Selection
# ==============================================================================
"""
Smart routing between Local and Cloud LLMs.

Strategy:
1. Simple queries → Local LLM (free)
2. Complex/critical queries → Cloud LLM (cached)
3. Fallback chain: Local → Cloud → Error

Cost savings: ~95% by using local for routine queries
"""

import re
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass
from enum import Enum

from .local_llm import LocalLLM, LocalResponse
from .cloud_llm import CloudLLM, CloudResponse

logger = logging.getLogger("seraph.brain.router")


class QueryComplexity(Enum):
    """Query complexity levels"""
    SIMPLE = "simple"      # Local LLM sufficient
    MODERATE = "moderate"  # Local preferred, cloud fallback
    COMPLEX = "complex"    # Cloud required
    CRITICAL = "critical"  # Cloud only, no cache


@dataclass
class RouterResponse:
    """Unified response from router"""
    content: str
    source: str  # "local" | "cloud" | "cache"
    model: str
    tokens: int
    latency_ms: float
    cost_usd: float
    success: bool
    error: Optional[str] = None


class BrainRouter:
    """
    Intelligent router between Local and Cloud LLMs.
    
    Routing rules:
    - Greetings, simple Q&A → Local
    - Analysis, summaries → Local (with cloud fallback)
    - Trading decisions, code changes → Cloud
    - Emergency/panic → Cloud (no cache)
    """
    
    # Keywords that require cloud processing
    CLOUD_KEYWORDS = [
        "trade", "buy", "sell", "position", "leverage",
        "execute", "activate", "deploy", "panic", "stop",
        "critical", "emergency", "urgent", "important",
        "code", "modify", "change", "update", "fix"
    ]
    
    # Simple queries that local can handle
    SIMPLE_PATTERNS = [
        r"^(hi|hello|hey|merhaba|selam)",
        r"^what (is|are) ",
        r"^how (do|does|can|to) ",
        r"^(explain|describe|tell me about)",
        r"\?$"  # Questions often simpler
    ]
    
    def __init__(
        self,
        local_llm: Optional[LocalLLM] = None,
        cloud_llm: Optional[CloudLLM] = None,
        prefer_local: bool = True
    ):
        self.local = local_llm
        self.cloud = cloud_llm
        self.prefer_local = prefer_local
        
        # Stats
        self.local_calls = 0
        self.cloud_calls = 0
        self.fallback_count = 0
        
    def classify_complexity(self, query: str) -> QueryComplexity:
        """
        Classify query complexity to decide routing.
        """
        query_lower = query.lower().strip()
        
        # Check for critical/cloud keywords
        for keyword in self.CLOUD_KEYWORDS:
            if keyword in query_lower:
                if keyword in ["panic", "emergency", "urgent", "critical"]:
                    return QueryComplexity.CRITICAL
                return QueryComplexity.COMPLEX
        
        # Check for simple patterns
        for pattern in self.SIMPLE_PATTERNS:
            if re.search(pattern, query_lower, re.IGNORECASE):
                return QueryComplexity.SIMPLE
        
        # Default to moderate
        return QueryComplexity.MODERATE
    
    def route(
        self,
        query: str,
        system: Optional[str] = None,
        context: Optional[Dict] = None,
        force_cloud: bool = False,
        force_local: bool = False
    ) -> RouterResponse:
        """
        Route query to appropriate LLM.
        
        Args:
            query: User query
            system: System prompt
            context: Additional context
            force_cloud: Force cloud LLM
            force_local: Force local LLM
        
        Returns:
            RouterResponse with content and routing info
        """
        complexity = self.classify_complexity(query)
        logger.info(f"Query complexity: {complexity.value}")
        
        # Build enhanced system prompt with context
        if context:
            context_str = "\n".join([f"- {k}: {v}" for k, v in context.items()])
            system = f"{system or ''}\n\nCurrent Context:\n{context_str}"
        
        # Forced routing
        if force_cloud:
            return self._call_cloud(query, system, use_cache=True)
        if force_local:
            return self._call_local(query, system)
        
        # Smart routing based on complexity
        if complexity == QueryComplexity.CRITICAL:
            # Critical: Cloud only, no cache
            return self._call_cloud(query, system, use_cache=False)
        
        elif complexity == QueryComplexity.COMPLEX:
            # Complex: Cloud with cache
            return self._call_cloud(query, system, use_cache=True)
        
        elif complexity == QueryComplexity.MODERATE:
            # Moderate: Try local, fallback to cloud
            if self.local and self.local.is_available():
                response = self._call_local(query, system)
                if response.success:
                    return response
                # Fallback to cloud
                logger.info("Local failed, falling back to cloud")
                self.fallback_count += 1
            return self._call_cloud(query, system, use_cache=True)
        
        else:  # SIMPLE
            # Simple: Local only (cloud fallback if unavailable)
            if self.local and self.local.is_available():
                return self._call_local(query, system)
            return self._call_cloud(query, system, use_cache=True)
    
    def _call_local(self, query: str, system: Optional[str]) -> RouterResponse:
        """Call local LLM"""
        if not self.local:
            return RouterResponse(
                content="",
                source="local",
                model="none",
                tokens=0,
                latency_ms=0,
                cost_usd=0,
                success=False,
                error="Local LLM not configured"
            )
        
        self.local_calls += 1
        response = self.local.generate(query, system=system)
        
        return RouterResponse(
            content=response.content,
            source="local",
            model=response.model,
            tokens=response.tokens,
            latency_ms=response.latency_ms,
            cost_usd=0,  # Local is free!
            success=response.success,
            error=response.error
        )
    
    def _call_cloud(self, query: str, system: Optional[str], use_cache: bool) -> RouterResponse:
        """Call cloud LLM"""
        if not self.cloud:
            return RouterResponse(
                content="",
                source="cloud",
                model="none",
                tokens=0,
                latency_ms=0,
                cost_usd=0,
                success=False,
                error="Cloud LLM not configured (API key missing)"
            )
        
        self.cloud_calls += 1
        response = self.cloud.generate(query, system=system, use_cache=use_cache)
        
        source = "cache" if response.from_cache else "cloud"
        
        return RouterResponse(
            content=response.content,
            source=source,
            model=response.model,
            tokens=response.input_tokens + response.output_tokens,
            latency_ms=response.latency_ms,
            cost_usd=response.cost_usd,
            success=response.success,
            error=response.error
        )
    
    def get_stats(self) -> Dict[str, Any]:
        """Get routing statistics"""
        total = self.local_calls + self.cloud_calls
        return {
            "total_calls": total,
            "local_calls": self.local_calls,
            "cloud_calls": self.cloud_calls,
            "local_ratio": self.local_calls / max(1, total),
            "fallback_count": self.fallback_count,
            "cloud_stats": self.cloud.get_stats() if self.cloud else {},
            "estimated_savings": self.local_calls * 0.01  # ~$0.01 per cloud call saved
        }

