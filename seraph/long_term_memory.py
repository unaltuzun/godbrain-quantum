# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
SERAPH Long-Term Memory
Persistent memory with Redis backend for context across sessions.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import json
import hashlib
import time
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional, Tuple
from dataclasses import dataclass, field, asdict
from collections import deque


ROOT = Path(__file__).parent.parent


@dataclass
class Memory:
    """A single memory entry."""
    id: str
    content: str
    memory_type: str  # "conversation", "fact", "preference", "decision", "error"
    timestamp: float
    importance: float = 0.5  # 0-1, higher = more important
    access_count: int = 0
    last_access: float = 0
    metadata: Dict[str, Any] = field(default_factory=dict)
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "Memory":
        return cls(**data)
    
    @property
    def age_hours(self) -> float:
        return (time.time() - self.timestamp) / 3600


class LongTermMemory:
    """
    Long-term memory system for Seraph.
    
    Features:
    - Redis backend (persistent across restarts)
    - Memory types (facts, preferences, decisions, errors)
    - Importance-based retrieval
    - Automatic decay and forgetting
    - Summarization of old memories
    
    Usage:
        memory = LongTermMemory()
        
        # Store a memory
        memory.remember("User prefers conservative trading", "preference", importance=0.8)
        
        # Recall relevant memories
        memories = memory.recall("trading preferences", top_k=5)
        
        # Get context for LLM
        context = memory.get_context_for_llm()
    """
    
    REDIS_KEY_PREFIX = "seraph:memory:"
    MAX_MEMORIES = 1000
    DECAY_RATE = 0.01  # Per hour
    
    def __init__(self, redis_client=None):
        self._redis = redis_client
        self._local_cache: Dict[str, Memory] = {}
        self._cache_file = ROOT / "seraph" / "memory" / "long_term.json"
        self._load_cache()
    
    def _get_redis(self):
        """Lazy load Redis connection."""
        if self._redis is None:
            try:
                import redis
                self._redis = redis.Redis(
                    host=os.getenv("REDIS_HOST", "127.0.0.1"),
                    port=int(os.getenv("REDIS_PORT", 6379)),
                    password=os.getenv("REDIS_PASS"),
                    decode_responses=True
                )
                self._redis.ping()
            except Exception:
                self._redis = None
        return self._redis
    
    def _load_cache(self) -> None:
        """Load memories from local cache."""
        if self._cache_file.exists():
            try:
                with open(self._cache_file, "r") as f:
                    data = json.load(f)
                self._local_cache = {
                    k: Memory.from_dict(v) for k, v in data.items()
                }
            except Exception:
                pass
    
    def _save_cache(self) -> None:
        """Save memories to local cache."""
        try:
            self._cache_file.parent.mkdir(parents=True, exist_ok=True)
            with open(self._cache_file, "w") as f:
                json.dump(
                    {k: v.to_dict() for k, v in self._local_cache.items()},
                    f, indent=2
                )
        except Exception:
            pass
    
    def _generate_id(self, content: str) -> str:
        """Generate unique ID for memory."""
        return hashlib.md5(f"{content}{time.time()}".encode()).hexdigest()[:12]
    
    def remember(
        self,
        content: str,
        memory_type: str = "fact",
        importance: float = 0.5,
        metadata: Optional[Dict] = None
    ) -> str:
        """
        Store a new memory.
        
        Args:
            content: The memory content
            memory_type: Type classification
            importance: 0-1 importance score
            metadata: Additional metadata
        
        Returns:
            Memory ID
        """
        memory_id = self._generate_id(content)
        
        memory = Memory(
            id=memory_id,
            content=content,
            memory_type=memory_type,
            timestamp=time.time(),
            importance=importance,
            metadata=metadata or {}
        )
        
        # Store locally
        self._local_cache[memory_id] = memory
        self._save_cache()
        
        # Store in Redis if available
        redis = self._get_redis()
        if redis:
            try:
                key = f"{self.REDIS_KEY_PREFIX}{memory_id}"
                redis.set(key, json.dumps(memory.to_dict()))
                redis.sadd(f"{self.REDIS_KEY_PREFIX}all", memory_id)
            except Exception:
                pass
        
        # Prune if too many
        self._prune_if_needed()
        
        return memory_id
    
    def recall(
        self,
        query: Optional[str] = None,
        memory_type: Optional[str] = None,
        top_k: int = 10,
        min_importance: float = 0.0
    ) -> List[Memory]:
        """
        Recall relevant memories.
        
        Args:
            query: Optional search query
            memory_type: Filter by type
            top_k: Max number to return
            min_importance: Minimum importance threshold
        
        Returns:
            List of relevant memories
        """
        memories = list(self._local_cache.values())
        
        # Filter by type
        if memory_type:
            memories = [m for m in memories if m.memory_type == memory_type]
        
        # Filter by importance
        memories = [m for m in memories if m.importance >= min_importance]
        
        # Score by relevance
        if query:
            query_words = set(query.lower().split())
            
            def score(m: Memory) -> float:
                content_words = set(m.content.lower().split())
                overlap = len(query_words & content_words)
                recency = 1.0 / (1.0 + m.age_hours * self.DECAY_RATE)
                return overlap * m.importance * recency
            
            memories.sort(key=score, reverse=True)
        else:
            # Sort by importance * recency
            memories.sort(
                key=lambda m: m.importance / (1 + m.age_hours * self.DECAY_RATE),
                reverse=True
            )
        
        # Update access stats
        for m in memories[:top_k]:
            m.access_count += 1
            m.last_access = time.time()
        
        self._save_cache()
        
        return memories[:top_k]
    
    def forget(self, memory_id: str) -> bool:
        """Remove a memory."""
        if memory_id in self._local_cache:
            del self._local_cache[memory_id]
            self._save_cache()
            
            redis = self._get_redis()
            if redis:
                try:
                    redis.delete(f"{self.REDIS_KEY_PREFIX}{memory_id}")
                    redis.srem(f"{self.REDIS_KEY_PREFIX}all", memory_id)
                except Exception:
                    pass
            
            return True
        return False
    
    def _prune_if_needed(self) -> None:
        """Remove old/unimportant memories if over limit."""
        if len(self._local_cache) <= self.MAX_MEMORIES:
            return
        
        # Score memories for pruning
        memories = list(self._local_cache.values())
        
        # Keep important and recent, remove old and unaccessed
        def keep_score(m: Memory) -> float:
            recency = 1.0 / (1.0 + m.age_hours * 0.1)
            access = 1.0 + m.access_count * 0.1
            return m.importance * recency * access
        
        memories.sort(key=keep_score)
        
        # Remove bottom 10%
        to_remove = memories[:len(memories) // 10]
        for m in to_remove:
            self.forget(m.id)
    
    def get_context_for_llm(self, max_memories: int = 10) -> str:
        """Get formatted memory context for LLM."""
        memories = self.recall(top_k=max_memories, min_importance=0.3)
        
        if not memories:
            return ""
        
        lines = ["=== LONG-TERM MEMORY ==="]
        
        # Group by type
        by_type: Dict[str, List[Memory]] = {}
        for m in memories:
            if m.memory_type not in by_type:
                by_type[m.memory_type] = []
            by_type[m.memory_type].append(m)
        
        type_emojis = {
            "preference": "⭐",
            "fact": "📌",
            "decision": "🎯",
            "error": "⚠️",
            "conversation": "💬"
        }
        
        for mtype, mems in by_type.items():
            emoji = type_emojis.get(mtype, "•")
            lines.append(f"\n{emoji} {mtype.upper()}:")
            for m in mems[:5]:
                lines.append(f"  • {m.content[:100]}")
        
        return "\n".join(lines)
    
    def remember_conversation(self, user_msg: str, assistant_msg: str) -> None:
        """Store a conversation exchange."""
        summary = f"User: {user_msg[:100]}... → Assistant: {assistant_msg[:100]}..."
        self.remember(
            summary,
            memory_type="conversation",
            importance=0.3,
            metadata={"user": user_msg, "assistant": assistant_msg}
        )
    
    def remember_preference(self, preference: str, importance: float = 0.7) -> None:
        """Store a user preference."""
        self.remember(preference, memory_type="preference", importance=importance)
    
    def remember_fact(self, fact: str, importance: float = 0.5) -> None:
        """Store a learned fact."""
        self.remember(fact, memory_type="fact", importance=importance)
    
    def remember_decision(self, decision: str, importance: float = 0.6) -> None:
        """Store a trading/system decision."""
        self.remember(decision, memory_type="decision", importance=importance)
    
    def remember_error(self, error: str, importance: float = 0.8) -> None:
        """Store an error for learning."""
        self.remember(error, memory_type="error", importance=importance)
    
    def get_stats(self) -> Dict[str, Any]:
        """Get memory statistics."""
        memories = list(self._local_cache.values())
        
        by_type: Dict[str, int] = {}
        for m in memories:
            by_type[m.memory_type] = by_type.get(m.memory_type, 0) + 1
        
        return {
            "total_memories": len(memories),
            "by_type": by_type,
            "avg_importance": sum(m.importance for m in memories) / max(1, len(memories)),
            "oldest_hours": max((m.age_hours for m in memories), default=0),
        }


# Global instance
_memory: Optional[LongTermMemory] = None


def get_long_term_memory() -> LongTermMemory:
    """Get or create global long-term memory."""
    global _memory
    if _memory is None:
        _memory = LongTermMemory()
    return _memory


if __name__ == "__main__":
    print("Long-Term Memory Demo")
    print("=" * 60)
    
    memory = LongTermMemory()
    
    # Store some test memories
    memory.remember_preference("User prefers conservative trading strategies")
    memory.remember_fact("DNA [10,10,242,331,354,500] performed best on DOGE")
    memory.remember_decision("Switched to TRENDING_UP regime at 14:30")
    memory.remember_error("OKX API rate limit hit - need to reduce frequency")
    
    print("\nStored memories:")
    print(memory.get_context_for_llm())
    
    print("\nStats:", memory.get_stats())
