# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
SERAPH Enhanced Core
Integrated AI with System Awareness, RAG, Tools, and Long-Term Memory.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import time
import json
import logging
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field

import requests

from .system_awareness import get_system_awareness, SystemAwareness
from .codebase_rag import get_codebase_rag, CodebaseRAG
from .tools import get_seraph_tools, SeraphTools, ToolResult
from .long_term_memory import get_long_term_memory, LongTermMemory

logger = logging.getLogger("seraph.enhanced")


@dataclass
class EnhancedResponse:
    """Response from Enhanced Seraph."""
    content: str
    tool_calls: List[Dict] = field(default_factory=list)
    tool_results: List[Dict] = field(default_factory=list)
    context_used: Dict[str, bool] = field(default_factory=dict)
    tokens_used: int = 0
    latency_ms: float = 0
    model: str = ""
    success: bool = True
    error: Optional[str] = None


class SeraphEnhanced:
    """
    Enhanced Seraph with full system awareness.
    
    Capabilities:
    - System Awareness: Git, DNA, trading state
    - RAG: Intelligent codebase search
    - Tools: File, git, trading operations
    - Long-Term Memory: Persistent context
    
    Usage:
        seraph = SeraphEnhanced()
        response = seraph.ask("What changes were made today?")
        response = seraph.ask("Find the circuit breaker implementation")
        response = seraph.ask("What's the current DNA fitness?")
    """
    
    SYSTEM_PROMPT = """You are SERAPH, the intelligent assistant for GODBRAIN Quantum Trading System.

You have full awareness of:
- All code changes and git history
- Current DNA/genetics evolution state
- Trading activity and positions
- System infrastructure and modules
- Historical decisions and errors

You can:
- Search the codebase for relevant code
- Read and analyze files
- Execute git commands
- Query trading state
- Remember important information

Be concise, technical, and helpful. Use your tools when needed.
"""
    
    def __init__(
        self,
        api_key: Optional[str] = None,
        model: str = "claude-sonnet-4-20250514"
    ):
        self.api_key = api_key or os.getenv("ANTHROPIC_API_KEY")
        self.model = model
        
        # Initialize components
        self.awareness = get_system_awareness()
        self.rag = get_codebase_rag()
        self.tools = get_seraph_tools()
        self.memory = get_long_term_memory()
        
        # Conversation history
        self.history: List[Dict] = []
        self.max_history = 20
    
    def _build_context(self, query: str) -> str:
        """Build rich context for the query."""
        parts = []
        
        # System awareness
        system_context = self.awareness.get_context_for_llm()
        if system_context:
            parts.append(system_context)
        
        # RAG context
        rag_context = self.rag.get_context_for_query(query, max_tokens=1500)
        if rag_context and len(rag_context) > 50:
            parts.append(rag_context)
        
        # Long-term memory
        memory_context = self.memory.get_context_for_llm(max_memories=5)
        if memory_context:
            parts.append(memory_context)
        
        return "\n\n".join(parts)
    
    def ask(
        self,
        query: str,
        use_tools: bool = True,
        include_context: bool = True,
        include_history: bool = True
    ) -> EnhancedResponse:
        """
        Ask Seraph a question with full context.
        
        Args:
            query: User question
            use_tools: Whether to enable tool use
            include_context: Whether to include system context
            include_history: Whether to include conversation history
        
        Returns:
            EnhancedResponse with answer and metadata
        """
        start_time = time.time()
        
        # Build messages
        messages = []
        
        # Add history
        if include_history and self.history:
            messages.extend(self.history[-self.max_history:])
        
        # Build user message with context
        user_content = query
        context_used = {
            "system_awareness": False,
            "rag": False,
            "memory": False,
            "tools": use_tools
        }
        
        if include_context:
            context = self._build_context(query)
            if context:
                user_content = f"{context}\n\n---\n\nUser Question: {query}"
                context_used["system_awareness"] = True
                context_used["rag"] = True
                context_used["memory"] = True
        
        messages.append({"role": "user", "content": user_content})
        
        # Call Claude API
        try:
            response = self._call_claude(messages, use_tools)
        except Exception as e:
            return EnhancedResponse(
                content="",
                success=False,
                error=str(e),
                latency_ms=(time.time() - start_time) * 1000
            )
        
        # Handle tool calls
        tool_calls = []
        tool_results = []
        final_content = ""
        
        if response.get("stop_reason") == "tool_use":
            # Extract tool calls
            for block in response.get("content", []):
                if block.get("type") == "tool_use":
                    tool_name = block.get("name")
                    tool_input = block.get("input", {})
                    tool_id = block.get("id")
                    
                    tool_calls.append({
                        "name": tool_name,
                        "input": tool_input
                    })
                    
                    # Execute tool
                    result = self.tools.execute(tool_name, tool_input)
                    tool_results.append(result.to_dict())
                    
                    # Continue conversation with tool result
                    messages.append({"role": "assistant", "content": response["content"]})
                    messages.append({
                        "role": "user",
                        "content": [{
                            "type": "tool_result",
                            "tool_use_id": tool_id,
                            "content": json.dumps(result.to_dict())
                        }]
                    })
            
            # Get final response
            final_response = self._call_claude(messages, use_tools=False)
            final_content = self._extract_text(final_response)
        else:
            final_content = self._extract_text(response)
        
        # Update history
        self.history.append({"role": "user", "content": query})
        self.history.append({"role": "assistant", "content": final_content})
        
        # Store in long-term memory if significant
        if len(final_content) > 100:
            self.memory.remember_conversation(query, final_content[:200])
        
        latency = (time.time() - start_time) * 1000
        
        return EnhancedResponse(
            content=final_content,
            tool_calls=tool_calls,
            tool_results=tool_results,
            context_used=context_used,
            tokens_used=response.get("usage", {}).get("input_tokens", 0) + 
                       response.get("usage", {}).get("output_tokens", 0),
            latency_ms=latency,
            model=self.model,
            success=True
        )
    
    def _call_claude(self, messages: List[Dict], use_tools: bool = True) -> Dict:
        """Call Claude API."""
        if not self.api_key:
            raise ValueError("ANTHROPIC_API_KEY not set")
        
        headers = {
            "Content-Type": "application/json",
            "x-api-key": self.api_key,
            "anthropic-version": "2023-06-01"
        }
        
        payload = {
            "model": self.model,
            "max_tokens": 4096,
            "system": self.SYSTEM_PROMPT,
            "messages": messages
        }
        
        if use_tools:
            payload["tools"] = self.tools.get_tool_definitions()
        
        response = requests.post(
            "https://api.anthropic.com/v1/messages",
            headers=headers,
            json=payload,
            timeout=60
        )
        
        if response.status_code != 200:
            raise Exception(f"Claude API error: {response.status_code} - {response.text}")
        
        return response.json()
    
    def _extract_text(self, response: Dict) -> str:
        """Extract text content from Claude response."""
        content = response.get("content", [])
        text_parts = []
        
        for block in content:
            if block.get("type") == "text":
                text_parts.append(block.get("text", ""))
        
        return "\n".join(text_parts)
    
    def clear_history(self) -> None:
        """Clear conversation history."""
        self.history = []
    
    def get_status(self) -> Dict[str, Any]:
        """Get Seraph status and capabilities."""
        return {
            "model": self.model,
            "api_configured": bool(self.api_key),
            "rag_indexed": self.rag._indexed,
            "rag_chunks": len(self.rag.chunks),
            "memory_stats": self.memory.get_stats(),
            "tools_available": list(self.tools.tools.keys()),
            "history_length": len(self.history),
        }


# Global instance
_enhanced: Optional[SeraphEnhanced] = None


def get_seraph_enhanced() -> SeraphEnhanced:
    """Get or create enhanced Seraph instance."""
    global _enhanced
    if _enhanced is None:
        _enhanced = SeraphEnhanced()
    return _enhanced


def ask_seraph(query: str, **kwargs) -> str:
    """Convenience function to ask Seraph."""
    seraph = get_seraph_enhanced()
    response = seraph.ask(query, **kwargs)
    return response.content


if __name__ == "__main__":
    print("Seraph Enhanced Demo")
    print("=" * 60)
    
    seraph = SeraphEnhanced()
    print("Status:", json.dumps(seraph.get_status(), indent=2))
    
    # Test without API (will fail gracefully)
    if seraph.api_key:
        response = seraph.ask("What modules are in the infrastructure folder?")
        print("\nResponse:", response.content[:500])
    else:
        print("\nNo API key configured - set ANTHROPIC_API_KEY to test")
