# ==============================================================================
# SEMANTIC CACHE - Embedding-based Response Cache
# ==============================================================================
"""
Semantic cache for similar queries.

Instead of exact match, uses embeddings to find similar queries.
If a query is semantically similar to a cached one, return cached response.

This dramatically reduces API costs for:
- Repeated questions with different wording
- Similar market analysis requests
- Common trading queries
"""

import json
import hashlib
import time
import logging
from typing import Optional, Dict, List, Tuple, Any
from dataclasses import dataclass, asdict
from pathlib import Path

logger = logging.getLogger("seraph.cache.semantic")


@dataclass
class CacheEntry:
    """Cached response entry"""
    query: str
    response: str
    embedding: Optional[List[float]] = None
    timestamp: float = 0
    hits: int = 0
    context_hash: str = ""
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "CacheEntry":
        return cls(**data)


class SemanticCache:
    """
    Semantic similarity cache.
    
    Features:
    - Exact match cache (fast)
    - Semantic similarity cache (coming with embeddings)
    - LRU eviction
    - Persistence to disk
    
    For now: Uses simple hash-based cache.
    Future: Add sentence embeddings for semantic matching.
    """
    
    def __init__(
        self,
        cache_dir: Optional[Path] = None,
        max_entries: int = 10000,
        similarity_threshold: float = 0.85
    ):
        self.cache_dir = cache_dir or Path(__file__).parent.parent.parent / "logs" / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)
        
        self.max_entries = max_entries
        self.similarity_threshold = similarity_threshold
        
        # In-memory cache
        self._cache: Dict[str, CacheEntry] = {}
        
        # Stats
        self.hits = 0
        self.misses = 0
        
        # Load from disk
        self._load_cache()
    
    def _normalize_query(self, query: str) -> str:
        """Normalize query for comparison"""
        # Lowercase, strip whitespace, normalize spaces
        normalized = " ".join(query.lower().strip().split())
        return normalized
    
    def _hash_query(self, query: str, context: Optional[Dict] = None) -> str:
        """Create hash key for query"""
        normalized = self._normalize_query(query)
        context_str = json.dumps(context or {}, sort_keys=True)
        combined = f"{normalized}::{context_str}"
        return hashlib.sha256(combined.encode()).hexdigest()[:32]
    
    def get(
        self,
        query: str,
        context: Optional[Dict] = None
    ) -> Optional[str]:
        """
        Get cached response for query.
        
        Args:
            query: User query
            context: Optional context (affects cache key)
        
        Returns:
            Cached response or None
        """
        cache_key = self._hash_query(query, context)
        
        if cache_key in self._cache:
            entry = self._cache[cache_key]
            entry.hits += 1
            self.hits += 1
            logger.debug(f"Cache hit for query (hits: {entry.hits})")
            return entry.response
        
        self.misses += 1
        return None
    
    def set(
        self,
        query: str,
        response: str,
        context: Optional[Dict] = None
    ) -> bool:
        """
        Cache a response.
        
        Args:
            query: User query
            response: Response to cache
            context: Optional context
        
        Returns:
            True if cached successfully
        """
        cache_key = self._hash_query(query, context)
        
        entry = CacheEntry(
            query=query,
            response=response,
            timestamp=time.time(),
            hits=0,
            context_hash=hashlib.sha256(json.dumps(context or {}).encode()).hexdigest()[:16]
        )
        
        self._cache[cache_key] = entry
        
        # Evict old entries if over limit
        if len(self._cache) > self.max_entries:
            self._evict_lru()
        
        return True
    
    def _evict_lru(self):
        """Evict least recently used entries"""
        # Sort by hits (keep most popular) and timestamp (keep recent)
        sorted_entries = sorted(
            self._cache.items(),
            key=lambda x: (x[1].hits, x[1].timestamp)
        )
        
        # Remove bottom 10%
        to_remove = len(sorted_entries) // 10
        for key, _ in sorted_entries[:to_remove]:
            del self._cache[key]
        
        logger.info(f"Evicted {to_remove} cache entries")
    
    def _load_cache(self):
        """Load cache from disk"""
        cache_file = self.cache_dir / "semantic_cache.json"
        if cache_file.exists():
            try:
                with open(cache_file, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for key, entry_data in data.items():
                        self._cache[key] = CacheEntry.from_dict(entry_data)
                logger.info(f"Loaded {len(self._cache)} cached entries")
            except Exception as e:
                logger.warning(f"Failed to load cache: {e}")
    
    def save(self):
        """Save cache to disk"""
        cache_file = self.cache_dir / "semantic_cache.json"
        try:
            data = {k: v.to_dict() for k, v in self._cache.items()}
            with open(cache_file, 'w', encoding='utf-8') as f:
                json.dump(data, f, indent=2)
            logger.info(f"Saved {len(self._cache)} cache entries")
        except Exception as e:
            logger.error(f"Failed to save cache: {e}")
    
    def clear(self):
        """Clear all cache"""
        self._cache.clear()
        self.hits = 0
        self.misses = 0
    
    def get_stats(self) -> Dict[str, Any]:
        """Get cache statistics"""
        total = self.hits + self.misses
        return {
            "entries": len(self._cache),
            "hits": self.hits,
            "misses": self.misses,
            "hit_rate": self.hits / max(1, total),
            "size_bytes": sum(len(e.response) for e in self._cache.values())
        }

