# -*- coding: utf-8 -*-
"""
GODBRAIN LLM Router
===================
Smart routing of LLM tasks based on criticality and cost.

Routes tasks to the most appropriate LLM:
- Critical tasks → Claude (best quality)
- Medium tasks → GPT-4 (good balance)
- Simple tasks → Gemini (cost-efficient)
- Local tasks → Llama (free)

Usage:
    from infrastructure.llm_router import LLMRouter
    
    router = LLMRouter()
    response = await router.complete("simple_query", "What is 2+2?")
"""

import os
import asyncio
import json
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field
from datetime import datetime, timedelta
from pathlib import Path
from collections import defaultdict

from infrastructure.llm_providers import (
    LLMProvider,
    LLMResponse,
    get_provider,
    list_available_providers,
    ClaudeProvider,
    OpenAIProvider,
    GeminiProvider,
    LlamaProvider,
)

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class CostTracker:
    """Track LLM usage costs."""
    
    total_cost_usd: float = 0.0
    total_requests: int = 0
    total_input_tokens: int = 0
    total_output_tokens: int = 0
    costs_by_provider: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    requests_by_provider: Dict[str, int] = field(default_factory=lambda: defaultdict(int))
    costs_by_task: Dict[str, float] = field(default_factory=lambda: defaultdict(float))
    daily_costs: Dict[str, float] = field(default_factory=dict)  # date -> cost
    
    def record(self, response: LLMResponse, task_type: str):
        """Record a completed request."""
        self.total_cost_usd += response.cost_usd
        self.total_requests += 1
        self.total_input_tokens += response.input_tokens
        self.total_output_tokens += response.output_tokens
        self.costs_by_provider[response.provider] += response.cost_usd
        self.requests_by_provider[response.provider] += 1
        self.costs_by_task[task_type] += response.cost_usd
        
        today = datetime.now().strftime("%Y-%m-%d")
        self.daily_costs[today] = self.daily_costs.get(today, 0.0) + response.cost_usd
    
    def get_stats(self) -> Dict:
        """Get cost statistics."""
        return {
            "total_cost_usd": round(self.total_cost_usd, 4),
            "total_requests": self.total_requests,
            "total_tokens": self.total_input_tokens + self.total_output_tokens,
            "by_provider": dict(self.costs_by_provider),
            "requests_by_provider": dict(self.requests_by_provider),
            "by_task": dict(self.costs_by_task),
            "today_cost": self.daily_costs.get(datetime.now().strftime("%Y-%m-%d"), 0.0),
        }
    
    def to_dict(self) -> Dict:
        return self.get_stats()


class LLMRouter:
    """
    Smart LLM routing based on task type.
    
    Routes tasks to appropriate providers with automatic fallback.
    """
    
    # Task type → (primary_provider, fallback_provider)
    ROUTING_RULES: Dict[str, Tuple[str, str]] = {
        # Critical - Claude is best
        "code_change": ("claude", "openai"),
        "code_review": ("claude", "openai"),
        "sentinel": ("claude", "openai"),
        "seraph_chat": ("claude", "openai"),
        "critical": ("claude", "openai"),
        
        # Medium - GPT-4 good balance
        "market_analysis": ("openai", "gemini"),
        "trading_decision": ("openai", "claude"),
        "report": ("openai", "gemini"),
        
        # Cost-efficient - Gemini
        "news_summary": ("gemini", "openai"),
        "translation": ("gemini", "openai"),
        "formatting": ("gemini", "llama"),
        
        # Simple/Local - Gemini or Llama
        "simple_query": ("gemini", "llama"),
        "text_processing": ("gemini", "llama"),
        "local": ("llama", "gemini"),
        
        # Default
        "default": ("gemini", "openai"),
    }
    
    def __init__(self):
        self.cost_tracker = CostTracker()
        self._providers: Dict[str, LLMProvider] = {}
        self._init_providers()
    
    def _init_providers(self):
        """Initialize available providers."""
        for name in ["claude", "openai", "gemini", "llama"]:
            try:
                provider = get_provider(name)
                if provider.is_available():
                    self._providers[name] = provider
            except Exception:
                pass
        
        if not self._providers:
            raise RuntimeError("No LLM providers available! Check API keys.")
    
    def get_available_providers(self) -> List[str]:
        """Get list of available provider names."""
        return list(self._providers.keys())
    
    def get_route(self, task_type: str) -> Tuple[str, str]:
        """Get primary and fallback provider for a task type."""
        task_type = task_type.lower()
        if task_type in self.ROUTING_RULES:
            return self.ROUTING_RULES[task_type]
        return self.ROUTING_RULES["default"]
    
    async def complete(
        self,
        task_type: str,
        content: str,
        messages: Optional[List[Dict[str, str]]] = None,
        system: Optional[str] = None,
        force_provider: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """
        Route and complete a task.
        
        Args:
            task_type: Type of task (determines routing)
            content: User message content
            messages: Optional full message history
            system: Optional system prompt
            force_provider: Override routing and use specific provider
            max_tokens: Maximum response tokens
            temperature: Sampling temperature
            
        Returns:
            LLMResponse with content and metadata
        """
        # Build messages
        if messages is None:
            messages = [{"role": "user", "content": content}]
        
        # Determine providers
        if force_provider:
            providers_to_try = [force_provider]
        else:
            primary, fallback = self.get_route(task_type)
            providers_to_try = [primary, fallback]
        
        # Filter to available providers
        providers_to_try = [p for p in providers_to_try if p in self._providers]
        
        if not providers_to_try:
            raise RuntimeError(f"No available providers for task: {task_type}")
        
        last_error = None
        
        for provider_name in providers_to_try:
            try:
                provider = self._providers[provider_name]
                response = await provider.complete(
                    messages=messages,
                    system=system,
                    max_tokens=max_tokens,
                    temperature=temperature,
                    **kwargs
                )
                
                # Track costs
                self.cost_tracker.record(response, task_type)
                
                return response
                
            except Exception as e:
                last_error = e
                # Log and try fallback
                print(f"[LLMRouter] {provider_name} failed: {e}, trying fallback...")
                continue
        
        # All providers failed
        raise RuntimeError(f"All providers failed for {task_type}: {last_error}")
    
    async def chat(
        self,
        task_type: str,
        messages: List[Dict[str, str]],
        system: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        """Convenience method for chat-style completion."""
        return await self.complete(
            task_type=task_type,
            content=messages[-1]["content"] if messages else "",
            messages=messages,
            system=system,
            **kwargs
        )
    
    def get_stats(self) -> Dict:
        """Get routing and cost statistics."""
        return {
            "available_providers": self.get_available_providers(),
            "routing_rules": {k: list(v) for k, v in self.ROUTING_RULES.items()},
            "costs": self.cost_tracker.get_stats(),
        }
    
    def get_cost_today(self) -> float:
        """Get today's total cost."""
        return self.cost_tracker.daily_costs.get(
            datetime.now().strftime("%Y-%m-%d"), 0.0
        )


# =============================================================================
# Global Router Instance
# =============================================================================

_router: Optional[LLMRouter] = None


def get_router() -> LLMRouter:
    """Get or create global router instance."""
    global _router
    if _router is None:
        _router = LLMRouter()
    return _router


# =============================================================================
# Quick Test
# =============================================================================

if __name__ == "__main__":
    print("LLM Router Test")
    print("=" * 60)
    
    router = get_router()
    print(f"\nAvailable providers: {router.get_available_providers()}")
    
    async def test_routing():
        test_cases = [
            ("simple_query", "What is 2+2?"),
            ("news_summary", "Summarize: Bitcoin hit $100k today."),
        ]
        
        for task_type, content in test_cases:
            print(f"\n--- Task: {task_type} ---")
            primary, fallback = router.get_route(task_type)
            print(f"Route: {primary} → {fallback}")
            
            try:
                response = await router.complete(task_type, content, max_tokens=50)
                print(f"Provider: {response.provider}")
                print(f"Response: {response.content[:80]}...")
                print(f"Cost: ${response.cost_usd:.6f}")
            except Exception as e:
                print(f"Error: {e}")
        
        print("\n--- Cost Stats ---")
        print(json.dumps(router.get_stats()["costs"], indent=2))
    
    asyncio.run(test_routing())
