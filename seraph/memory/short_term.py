# ==============================================================================
# SHORT-TERM MEMORY (Redis-based conversation history)
# ==============================================================================
"""
Kısa dönem hafıza sistemi - Son N konuşmayı Redis'te saklar.
Thread-safe, TTL destekli, graceful degradation.
"""

import json
import time
from typing import List, Dict, Optional, Any
from dataclasses import dataclass, asdict
import logging

logger = logging.getLogger("seraph.memory")


@dataclass
class MemoryEntry:
    """Tek bir hafıza girişi"""
    role: str  # "user" | "assistant" | "system"
    content: str
    timestamp: float
    metadata: Optional[Dict[str, Any]] = None
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "MemoryEntry":
        return cls(**data)
    
    def to_message(self) -> dict:
        """Claude API format"""
        return {"role": self.role, "content": self.content}


class ShortTermMemory:
    """
    Redis-tabanlı kısa dönem hafıza.
    
    Features:
    - Son N mesajı saklar
    - TTL ile otomatik expire
    - Graceful degradation (Redis yoksa sessizce çalışır)
    - Thread-safe
    """
    
    MEMORY_KEY_PREFIX = "seraph:memory:"
    
    def __init__(
        self,
        redis_host: str = "127.0.0.1",
        redis_port: int = 16379,
        redis_password: str = "voltran2024",
        max_messages: int = 50,
        ttl_seconds: int = 86400,  # 24 hours
        session_id: str = "default"
    ):
        self.redis_host = redis_host
        self.redis_port = redis_port
        self.redis_password = redis_password
        self.max_messages = max_messages
        self.ttl_seconds = ttl_seconds
        self.session_id = session_id
        self._redis = None
        self._fallback_memory: List[MemoryEntry] = []  # In-memory fallback
        
    @property
    def memory_key(self) -> str:
        return f"{self.MEMORY_KEY_PREFIX}{self.session_id}"
    
    def _get_redis(self):
        """Lazy Redis connection with graceful fallback"""
        if self._redis is not None:
            return self._redis
        
        try:
            import redis
            self._redis = redis.Redis(
                host=self.redis_host,
                port=self.redis_port,
                password=self.redis_password,
                decode_responses=True,
                socket_timeout=2,
                socket_connect_timeout=2
            )
            # Test connection
            self._redis.ping()
            logger.info(f"Memory connected to Redis at {self.redis_host}:{self.redis_port}")
            return self._redis
        except Exception as e:
            logger.warning(f"Redis unavailable, using in-memory fallback: {e}")
            self._redis = None
            return None
    
    def add(self, role: str, content: str, metadata: Optional[Dict] = None) -> bool:
        """
        Hafızaya yeni mesaj ekle.
        
        Args:
            role: "user" | "assistant" | "system"
            content: Mesaj içeriği
            metadata: Opsiyonel metadata (context, tokens, etc.)
        
        Returns:
            bool: Başarılı mı
        """
        entry = MemoryEntry(
            role=role,
            content=content,
            timestamp=time.time(),
            metadata=metadata
        )
        
        redis_client = self._get_redis()
        
        if redis_client:
            try:
                # LPUSH ile başa ekle (en yeni önce)
                redis_client.lpush(self.memory_key, json.dumps(entry.to_dict()))
                # Max size'ı koru
                redis_client.ltrim(self.memory_key, 0, self.max_messages - 1)
                # TTL ayarla
                redis_client.expire(self.memory_key, self.ttl_seconds)
                return True
            except Exception as e:
                logger.error(f"Redis write error: {e}")
        
        # Fallback to in-memory
        self._fallback_memory.insert(0, entry)
        if len(self._fallback_memory) > self.max_messages:
            self._fallback_memory = self._fallback_memory[:self.max_messages]
        return True
    
    def get_history(self, limit: Optional[int] = None) -> List[MemoryEntry]:
        """
        Konuşma geçmişini al.
        
        Args:
            limit: Maksimum mesaj sayısı (None = tümü)
        
        Returns:
            List[MemoryEntry]: En yeniden eskiye sıralı mesajlar
        """
        limit = limit or self.max_messages
        redis_client = self._get_redis()
        
        if redis_client:
            try:
                raw_entries = redis_client.lrange(self.memory_key, 0, limit - 1)
                entries = []
                for raw in raw_entries:
                    try:
                        data = json.loads(raw)
                        entries.append(MemoryEntry.from_dict(data))
                    except json.JSONDecodeError:
                        continue
                return entries
            except Exception as e:
                logger.error(f"Redis read error: {e}")
        
        # Fallback
        return self._fallback_memory[:limit]
    
    def get_messages_for_api(self, limit: int = 10) -> List[Dict]:
        """
        Claude API formatında mesajları döndür.
        En eskiden en yeniye sıralı (API gereksinimi).
        """
        history = self.get_history(limit)
        # Reverse to get oldest first (API expects chronological order)
        messages = [entry.to_message() for entry in reversed(history)]
        return messages
    
    def clear(self) -> bool:
        """Hafızayı temizle"""
        redis_client = self._get_redis()
        
        if redis_client:
            try:
                redis_client.delete(self.memory_key)
                return True
            except Exception as e:
                logger.error(f"Redis clear error: {e}")
        
        self._fallback_memory.clear()
        return True
    
    def get_context_summary(self) -> str:
        """
        Son konuşmaların özeti - prompt'a eklenebilir.
        """
        history = self.get_history(5)  # Son 5 mesaj
        if not history:
            return "No previous conversation."
        
        summary_parts = []
        for entry in reversed(history):
            role_icon = "👤" if entry.role == "user" else "🤖"
            # Truncate long messages
            content = entry.content[:100] + "..." if len(entry.content) > 100 else entry.content
            summary_parts.append(f"{role_icon} {content}")
        
        return "\n".join(summary_parts)
    
    def add_user_message(self, content: str, **metadata) -> bool:
        """Shorthand for adding user message"""
        return self.add("user", content, metadata)
    
    def add_assistant_message(self, content: str, **metadata) -> bool:
        """Shorthand for adding assistant message"""
        return self.add("assistant", content, metadata)

