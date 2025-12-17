# -*- coding: utf-8 -*-
"""
GODBRAIN Multi-LLM Providers
============================
Unified interface for multiple LLM providers.

Providers:
- Claude (Anthropic) - Best for code, critical decisions
- GPT-4 (OpenAI) - Good all-rounder
- Gemini (Google) - Cost-efficient
- Llama (Ollama) - Free, local

Usage:
    from infrastructure.llm_providers import get_provider
    
    provider = get_provider("claude")
    response = await provider.complete([{"role": "user", "content": "Hello"}])
"""

import os
import asyncio
import httpx
from abc import ABC, abstractmethod
from typing import Any, AsyncIterator, Dict, List, Optional
from dataclasses import dataclass, field
from datetime import datetime
import json

# Load environment
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass


@dataclass
class LLMResponse:
    """Standardized response from any LLM provider."""
    content: str
    provider: str
    model: str
    input_tokens: int = 0
    output_tokens: int = 0
    cost_usd: float = 0.0
    latency_ms: float = 0.0
    timestamp: datetime = field(default_factory=datetime.now)
    
    def to_dict(self) -> Dict:
        return {
            "content": self.content,
            "provider": self.provider,
            "model": self.model,
            "input_tokens": self.input_tokens,
            "output_tokens": self.output_tokens,
            "cost_usd": self.cost_usd,
            "latency_ms": self.latency_ms,
            "timestamp": self.timestamp.isoformat(),
        }


class LLMProvider(ABC):
    """Abstract base class for LLM providers."""
    
    name: str = "base"
    
    # Cost per 1M tokens (input, output)
    COST_PER_1M_INPUT: float = 0.0
    COST_PER_1M_OUTPUT: float = 0.0
    
    @abstractmethod
    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        **kwargs
    ) -> LLMResponse:
        """Generate a completion."""
        pass
    
    async def stream(
        self,
        messages: List[Dict[str, str]],
        **kwargs
    ) -> AsyncIterator[str]:
        """Stream a completion. Default implementation uses complete()."""
        response = await self.complete(messages, **kwargs)
        yield response.content
    
    def calculate_cost(self, input_tokens: int, output_tokens: int) -> float:
        """Calculate cost in USD."""
        input_cost = (input_tokens / 1_000_000) * self.COST_PER_1M_INPUT
        output_cost = (output_tokens / 1_000_000) * self.COST_PER_1M_OUTPUT
        return input_cost + output_cost
    
    def is_available(self) -> bool:
        """Check if provider is configured and ready."""
        return True


class ClaudeProvider(LLMProvider):
    """Anthropic Claude provider."""
    
    name = "claude"
    COST_PER_1M_INPUT = 3.0   # Claude 3.5 Sonnet
    COST_PER_1M_OUTPUT = 15.0
    
    DEFAULT_MODEL = "claude-sonnet-4-20250514"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self._client = None
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        import anthropic
        
        if not self._client:
            self._client = anthropic.Anthropic(api_key=self.api_key)
        
        model = model or self.DEFAULT_MODEL
        start_time = datetime.now()
        
        # Build request
        request_kwargs = {
            "model": model,
            "max_tokens": max_tokens,
            "temperature": temperature,
            "messages": messages,
        }
        if system:
            request_kwargs["system"] = system
        
        response = self._client.messages.create(**request_kwargs)
        
        latency = (datetime.now() - start_time).total_seconds() * 1000
        
        input_tokens = response.usage.input_tokens
        output_tokens = response.usage.output_tokens
        
        return LLMResponse(
            content=response.content[0].text,
            provider=self.name,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=self.calculate_cost(input_tokens, output_tokens),
            latency_ms=latency,
        )


class OpenAIProvider(LLMProvider):
    """OpenAI GPT-4 provider."""
    
    name = "openai"
    COST_PER_1M_INPUT = 2.5   # GPT-4o
    COST_PER_1M_OUTPUT = 10.0
    
    DEFAULT_MODEL = "gpt-4o"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("OPENAI_API_KEY")
        self._client = None
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        from openai import OpenAI
        
        if not self._client:
            self._client = OpenAI(api_key=self.api_key)
        
        model = model or self.DEFAULT_MODEL
        start_time = datetime.now()
        
        # Add system message if provided
        full_messages = messages.copy()
        if system:
            full_messages.insert(0, {"role": "system", "content": system})
        
        response = self._client.chat.completions.create(
            model=model,
            messages=full_messages,
            max_tokens=max_tokens,
            temperature=temperature,
        )
        
        latency = (datetime.now() - start_time).total_seconds() * 1000
        
        input_tokens = response.usage.prompt_tokens
        output_tokens = response.usage.completion_tokens
        
        return LLMResponse(
            content=response.choices[0].message.content,
            provider=self.name,
            model=model,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=self.calculate_cost(input_tokens, output_tokens),
            latency_ms=latency,
        )


class GeminiProvider(LLMProvider):
    """Google Gemini provider."""
    
    name = "gemini"
    COST_PER_1M_INPUT = 0.075   # Gemini 1.5 Flash
    COST_PER_1M_OUTPUT = 0.30
    
    DEFAULT_MODEL = "gemini-2.0-flash"
    
    def __init__(self, api_key: Optional[str] = None):
        self.api_key = api_key or os.getenv("GEMINI_API_KEY")
        self._client = None
    
    def is_available(self) -> bool:
        return bool(self.api_key)
    
    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        import google.generativeai as genai
        
        genai.configure(api_key=self.api_key)
        
        model_name = model or self.DEFAULT_MODEL
        start_time = datetime.now()
        
        # Convert messages to Gemini format
        gemini_model = genai.GenerativeModel(
            model_name=model_name,
            system_instruction=system,
        )
        
        # Build history and current message
        history = []
        current_content = ""
        
        for msg in messages:
            role = "user" if msg["role"] == "user" else "model"
            if msg == messages[-1]:
                current_content = msg["content"]
            else:
                history.append({"role": role, "parts": [msg["content"]]})
        
        chat = gemini_model.start_chat(history=history)
        response = chat.send_message(
            current_content,
            generation_config=genai.types.GenerationConfig(
                max_output_tokens=max_tokens,
                temperature=temperature,
            ),
        )
        
        latency = (datetime.now() - start_time).total_seconds() * 1000
        
        # Gemini doesn't always return token counts
        input_tokens = getattr(response.usage_metadata, 'prompt_token_count', 0) if hasattr(response, 'usage_metadata') else 0
        output_tokens = getattr(response.usage_metadata, 'candidates_token_count', 0) if hasattr(response, 'usage_metadata') else 0
        
        return LLMResponse(
            content=response.text,
            provider=self.name,
            model=model_name,
            input_tokens=input_tokens,
            output_tokens=output_tokens,
            cost_usd=self.calculate_cost(input_tokens, output_tokens),
            latency_ms=latency,
        )


class LlamaProvider(LLMProvider):
    """Local Llama via Ollama provider."""
    
    name = "llama"
    COST_PER_1M_INPUT = 0.0   # Free!
    COST_PER_1M_OUTPUT = 0.0
    
    DEFAULT_MODEL = "llama3.2"
    
    def __init__(self, base_url: str = "http://localhost:11434"):
        self.base_url = base_url
    
    def is_available(self) -> bool:
        """Check if Ollama is running."""
        try:
            import httpx
            response = httpx.get(f"{self.base_url}/api/tags", timeout=2.0)
            return response.status_code == 200
        except Exception:
            return False
    
    async def complete(
        self,
        messages: List[Dict[str, str]],
        model: Optional[str] = None,
        max_tokens: int = 4096,
        temperature: float = 0.7,
        system: Optional[str] = None,
        **kwargs
    ) -> LLMResponse:
        model = model or self.DEFAULT_MODEL
        start_time = datetime.now()
        
        # Add system message if provided
        full_messages = messages.copy()
        if system:
            full_messages.insert(0, {"role": "system", "content": system})
        
        async with httpx.AsyncClient() as client:
            response = await client.post(
                f"{self.base_url}/api/chat",
                json={
                    "model": model,
                    "messages": full_messages,
                    "stream": False,
                    "options": {
                        "num_predict": max_tokens,
                        "temperature": temperature,
                    },
                },
                timeout=60.0,
            )
            response.raise_for_status()
            data = response.json()
        
        latency = (datetime.now() - start_time).total_seconds() * 1000
        
        return LLMResponse(
            content=data["message"]["content"],
            provider=self.name,
            model=model,
            input_tokens=data.get("prompt_eval_count", 0),
            output_tokens=data.get("eval_count", 0),
            cost_usd=0.0,  # Free!
            latency_ms=latency,
        )


# =============================================================================
# Provider Registry
# =============================================================================

PROVIDERS: Dict[str, type] = {
    "claude": ClaudeProvider,
    "openai": OpenAIProvider,
    "gpt4": OpenAIProvider,
    "gemini": GeminiProvider,
    "llama": LlamaProvider,
    "ollama": LlamaProvider,
}

_provider_instances: Dict[str, LLMProvider] = {}


def get_provider(name: str) -> LLMProvider:
    """Get a provider instance by name."""
    name = name.lower()
    
    if name not in PROVIDERS:
        raise ValueError(f"Unknown provider: {name}. Available: {list(PROVIDERS.keys())}")
    
    if name not in _provider_instances:
        _provider_instances[name] = PROVIDERS[name]()
    
    return _provider_instances[name]


def list_available_providers() -> List[str]:
    """List all providers that are configured and available."""
    available = []
    for name in PROVIDERS:
        try:
            provider = get_provider(name)
            if provider.is_available():
                available.append(name)
        except Exception:
            pass
    return list(set(available))  # Remove duplicates


# =============================================================================
# Quick Test
# =============================================================================

if __name__ == "__main__":
    print("LLM Providers Test")
    print("=" * 60)
    
    print("\nAvailable providers:", list_available_providers())
    
    async def test_providers():
        test_message = [{"role": "user", "content": "Say 'Hello GODBRAIN' in 5 words or less."}]
        
        for name in ["claude", "openai", "gemini"]:
            try:
                provider = get_provider(name)
                if not provider.is_available():
                    print(f"\n{name}: NOT CONFIGURED")
                    continue
                
                print(f"\n{name}: Testing...")
                response = await provider.complete(test_message, max_tokens=50)
                print(f"  Response: {response.content[:50]}...")
                print(f"  Cost: ${response.cost_usd:.6f}")
                print(f"  Latency: {response.latency_ms:.0f}ms")
            except Exception as e:
                print(f"\n{name}: ERROR - {e}")
    
    asyncio.run(test_providers())
