# ==============================================================================
# SERAPH CORE - Autonomous Intelligence Engine
# ==============================================================================
"""
Kurumsal-grade AI Core with:
- Memory (short-term + long-term)
- Tool use (function calling)
- Context awareness
- Graceful degradation
"""

import json
import os
import time
import logging
from typing import Optional, Dict, List, Any, Callable
from dataclasses import dataclass

import requests

from .config import SeraphConfig
from .memory import ShortTermMemory

logger = logging.getLogger("seraph.core")


@dataclass
class SeraphResponse:
    """Structured response from Seraph"""
    content: str
    actions: List[Dict] = None
    tokens_used: int = 0
    model: str = ""
    latency_ms: float = 0
    from_cache: bool = False
    error: Optional[str] = None
    
    @property
    def success(self) -> bool:
        return self.error is None
    
    def to_dict(self) -> dict:
        return {
            "content": self.content,
            "actions": self.actions,
            "tokens_used": self.tokens_used,
            "model": self.model,
            "latency_ms": self.latency_ms,
            "success": self.success,
            "error": self.error
        }


class SeraphCore:
    """
    Seraph AI Core Engine
    
    Features:
    - Multi-turn conversation with memory
    - System context injection
    - Tool use (coming soon)
    - Structured responses
    - Error handling & retry
    """
    
    API_URL = "https://api.anthropic.com/v1/messages"
    
    def __init__(self, config: Optional[SeraphConfig] = None):
        """
        Initialize Seraph Core.
        
        Args:
            config: SeraphConfig instance (or loads from env)
        """
        self.config = config or SeraphConfig.from_env()
        self._validate_config()
        
        # Initialize memory if enabled
        self.memory: Optional[ShortTermMemory] = None
        if self.config.memory_enabled:
            self.memory = ShortTermMemory(
                redis_host=self.config.redis_host,
                redis_port=self.config.redis_port,
                redis_password=self.config.redis_password,
                max_messages=self.config.memory_max_messages,
                ttl_seconds=self.config.memory_ttl_seconds
            )
        
        # Tool registry (for future tool use)
        self._tools: Dict[str, Callable] = {}
        
        # Stats
        self.total_requests = 0
        self.total_tokens = 0
        
        logger.info(f"SeraphCore initialized | Model: {self.config.model} | Memory: {self.config.memory_enabled}")
    
    def _validate_config(self):
        """Validate configuration"""
        if not self.config.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set. Please set it in .env or environment.")
    
    def _build_system_prompt(self, context: Optional[Dict] = None) -> str:
        """
        Build dynamic system prompt with context.
        """
        base_prompt = """You are SERAPH, the Autonomous Core of GODBRAIN Trading System.

CAPABILITIES:
- Real-time market analysis
- Trading strategy optimization  
- Portfolio risk assessment
- DNA parameter evolution insights

PERSONALITY:
- Precise and data-driven
- Proactive risk awareness
- Clear and actionable insights

RESPONSE STYLE:
- Be concise but thorough
- Use technical terms when appropriate
- Provide actionable recommendations
- Include relevant metrics/numbers
"""
        
        # Add dynamic context
        if context:
            context_str = "\n\nCURRENT CONTEXT:\n"
            for key, value in context.items():
                context_str += f"- {key}: {value}\n"
            base_prompt += context_str
        
        # Add memory context if available
        if self.memory:
            memory_summary = self.memory.get_context_summary()
            if memory_summary and memory_summary != "No previous conversation.":
                base_prompt += f"\n\nRECENT CONVERSATION:\n{memory_summary}"
        
        return base_prompt
    
    def _build_messages(self, user_input: str, history_limit: int = 10) -> List[Dict]:
        """
        Build messages array with conversation history.
        """
        messages = []
        
        # Add history from memory
        if self.memory:
            history = self.memory.get_messages_for_api(limit=history_limit)
            messages.extend(history)
        
        # Add current user message
        messages.append({"role": "user", "content": user_input})
        
        return messages
    
    def ask(
        self,
        user_input: str,
        context: Optional[Dict] = None,
        include_history: bool = True,
        history_limit: int = 10,
        max_tokens: Optional[int] = None,
        temperature: Optional[float] = None
    ) -> SeraphResponse:
        """
        Send a message to Seraph and get a response.
        
        Args:
            user_input: User's message
            context: Dynamic context to inject (price, portfolio, etc.)
            include_history: Whether to include conversation history
            history_limit: Max history messages to include
            max_tokens: Override max tokens
            temperature: Override temperature
        
        Returns:
            SeraphResponse with content and metadata
        """
        start_time = time.time()
        
        # Build request
        system_prompt = self._build_system_prompt(context)
        
        if include_history and self.memory:
            messages = self._build_messages(user_input, history_limit)
        else:
            messages = [{"role": "user", "content": user_input}]
        
        headers = {
            "x-api-key": self.config.api_key,
            "anthropic-version": "2023-06-01",
            "content-type": "application/json"
        }
        
        payload = {
            "model": self.config.model,
            "max_tokens": max_tokens or self.config.max_tokens,
            "temperature": temperature or self.config.temperature,
            "system": system_prompt,
            "messages": messages
        }
        
        try:
            response = requests.post(
                self.API_URL,
                headers=headers,
                json=payload,
                timeout=30
            )
            
            latency_ms = (time.time() - start_time) * 1000
            
            if response.status_code == 200:
                data = response.json()
                content = data["content"][0]["text"]
                tokens_used = data.get("usage", {}).get("input_tokens", 0) + data.get("usage", {}).get("output_tokens", 0)
                
                # Save to memory
                if self.memory:
                    self.memory.add_user_message(user_input)
                    self.memory.add_assistant_message(content)
                
                # Update stats
                self.total_requests += 1
                self.total_tokens += tokens_used
                
                # Parse actions if present
                actions = self._parse_actions(content)
                
                return SeraphResponse(
                    content=content,
                    actions=actions,
                    tokens_used=tokens_used,
                    model=self.config.model,
                    latency_ms=latency_ms
                )
            else:
                error_msg = f"API Error ({response.status_code}): {response.text[:200]}"
                logger.error(error_msg)
                return SeraphResponse(
                    content="",
                    error=error_msg,
                    latency_ms=latency_ms
                )
                
        except requests.Timeout:
            return SeraphResponse(content="", error="Request timeout")
        except Exception as e:
            logger.exception("Seraph API error")
            return SeraphResponse(content="", error=str(e))
    
    def _parse_actions(self, content: str) -> Optional[List[Dict]]:
        """Parse action commands from response"""
        if '{"actions":' not in content:
            return None
        
        try:
            json_start = content.find('{"actions":')
            json_end = content.rfind('}') + 1
            json_part = content[json_start:json_end]
            data = json.loads(json_part)
            return data.get("actions", [])
        except (json.JSONDecodeError, ValueError):
            return None
    
    def clear_memory(self):
        """Clear conversation memory"""
        if self.memory:
            self.memory.clear()
            logger.info("Memory cleared")
    
    def get_stats(self) -> Dict:
        """Get usage statistics"""
        return {
            "total_requests": self.total_requests,
            "total_tokens": self.total_tokens,
            "model": self.config.model,
            "memory_enabled": self.config.memory_enabled
        }


# ==============================================================================
# BACKWARD COMPATIBLE WRAPPER
# ==============================================================================

_seraph_instance: Optional[SeraphCore] = None

def get_seraph() -> SeraphCore:
    """Get or create singleton Seraph instance"""
    global _seraph_instance
    if _seraph_instance is None:
        _seraph_instance = SeraphCore()
    return _seraph_instance


def ask_seraph_v2(user_input: str, context: Optional[Dict] = None) -> str:
    """
    Backward-compatible wrapper for SeraphCore.
    
    Use this as a drop-in replacement for the old ask_seraph() function.
    Returns just the content string for compatibility.
    """
    try:
        seraph = get_seraph()
        response = seraph.ask(user_input, context=context)
        
        if response.success:
            return response.content
        else:
            return f"API ERROR: {response.error}"
    except Exception as e:
        logger.exception("ask_seraph_v2 error")
        return f"ERROR: {str(e)}"

