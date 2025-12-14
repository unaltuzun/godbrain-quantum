# ==============================================================================
# PATTERN DB - Learned Response Patterns
# ==============================================================================
"""
Database of learned response patterns.

Seraph learns from successful interactions:
- Which responses led to good outcomes
- Common query patterns and best responses
- Trading strategy patterns that worked

This enables pattern-based responses without AI inference.
"""

import json
import time
import logging
from typing import Optional, Dict, List, Any
from dataclasses import dataclass, asdict
from pathlib import Path
from collections import defaultdict

logger = logging.getLogger("seraph.cache.patterns")


@dataclass
class Pattern:
    """A learned pattern"""
    id: str
    trigger: str  # Regex or keyword trigger
    response_template: str
    category: str  # "greeting", "analysis", "trading", "system"
    success_count: int = 0
    fail_count: int = 0
    last_used: float = 0
    metadata: Optional[Dict] = None
    
    @property
    def success_rate(self) -> float:
        total = self.success_count + self.fail_count
        return self.success_count / max(1, total)
    
    def to_dict(self) -> dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: dict) -> "Pattern":
        return cls(**data)


class PatternDB:
    """
    Database of learned response patterns.
    
    Use cases:
    1. Fast responses for common queries
    2. Consistent responses for system queries
    3. Template-based responses with variable substitution
    
    Patterns can be:
    - Manually defined (core patterns)
    - Learned from successful interactions
    - Evolved through feedback
    """
    
    # Core patterns (always available)
    CORE_PATTERNS = [
        Pattern(
            id="greeting_hello",
            trigger=r"^(hi|hello|hey|merhaba|selam)",
            response_template="Hello! I'm Seraph, the autonomous core of GodBrain. How can I assist you with trading today?",
            category="greeting"
        ),
        Pattern(
            id="status_check",
            trigger=r"(status|durum|nasıl|how are)",
            response_template="System Status:\n- Redis: {redis_status}\n- Market Feed: {market_status}\n- Voltran: {voltran_status}\n\nAll systems operational.",
            category="system"
        ),
        Pattern(
            id="price_query",
            trigger=r"(price|fiyat|btc|bitcoin)",
            response_template="Current BTC Price: ${price}\nChange 24h: {change}%\nRegime: {regime}",
            category="market"
        ),
        Pattern(
            id="help",
            trigger=r"(help|yardım|ne yapabil)",
            response_template="""I can help you with:
            
🔍 **Analysis**: Ask about market conditions, trends, signals
📊 **Portfolio**: Check positions, P&L, risk exposure  
🧬 **DNA**: View genetic algorithm parameters
⚡ **Trading**: Execute strategies (requires confirmation)
🔧 **System**: Check service status, logs

What would you like to know?""",
            category="system"
        )
    ]
    
    def __init__(self, db_path: Optional[Path] = None):
        self.db_path = db_path or Path(__file__).parent.parent.parent / "logs" / "patterns.json"
        self.db_path.parent.mkdir(parents=True, exist_ok=True)
        
        # Patterns indexed by category
        self._patterns: Dict[str, Pattern] = {}
        self._by_category: Dict[str, List[str]] = defaultdict(list)
        
        # Load core patterns
        for p in self.CORE_PATTERNS:
            self._add_pattern(p)
        
        # Load learned patterns
        self._load()
    
    def _add_pattern(self, pattern: Pattern):
        """Add pattern to database"""
        self._patterns[pattern.id] = pattern
        if pattern.id not in self._by_category[pattern.category]:
            self._by_category[pattern.category].append(pattern.id)
    
    def match(self, query: str) -> Optional[Pattern]:
        """
        Find matching pattern for query.
        
        Args:
            query: User query
        
        Returns:
            Best matching pattern or None
        """
        import re
        
        query_lower = query.lower().strip()
        best_match: Optional[Pattern] = None
        best_score = 0
        
        for pattern in self._patterns.values():
            try:
                if re.search(pattern.trigger, query_lower, re.IGNORECASE):
                    # Score based on success rate and specificity
                    score = pattern.success_rate + (1 / len(pattern.trigger))
                    if score > best_score:
                        best_score = score
                        best_match = pattern
            except re.error:
                continue
        
        if best_match:
            best_match.last_used = time.time()
        
        return best_match
    
    def render(self, pattern: Pattern, context: Dict[str, Any]) -> str:
        """
        Render pattern template with context.
        
        Args:
            pattern: Pattern to render
            context: Variable values
        
        Returns:
            Rendered response
        """
        try:
            return pattern.response_template.format(**context)
        except KeyError as e:
            # Missing variable, return template with placeholders
            logger.warning(f"Missing context variable: {e}")
            return pattern.response_template
    
    def record_feedback(self, pattern_id: str, success: bool):
        """Record feedback for pattern"""
        if pattern_id in self._patterns:
            pattern = self._patterns[pattern_id]
            if success:
                pattern.success_count += 1
            else:
                pattern.fail_count += 1
            self._save()
    
    def add_learned_pattern(
        self,
        trigger: str,
        response: str,
        category: str = "learned"
    ) -> Pattern:
        """Add a new learned pattern"""
        pattern_id = f"learned_{len(self._patterns)}_{int(time.time())}"
        pattern = Pattern(
            id=pattern_id,
            trigger=trigger,
            response_template=response,
            category=category,
            success_count=1
        )
        self._add_pattern(pattern)
        self._save()
        return pattern
    
    def _load(self):
        """Load learned patterns from disk"""
        if self.db_path.exists():
            try:
                with open(self.db_path, 'r', encoding='utf-8') as f:
                    data = json.load(f)
                    for pattern_data in data.get("patterns", []):
                        pattern = Pattern.from_dict(pattern_data)
                        self._add_pattern(pattern)
                logger.info(f"Loaded {len(self._patterns)} patterns")
            except Exception as e:
                logger.warning(f"Failed to load patterns: {e}")
    
    def _save(self):
        """Save patterns to disk"""
        try:
            # Only save non-core patterns
            learned = [p.to_dict() for p in self._patterns.values() 
                      if not p.id.startswith(("greeting_", "status_", "price_", "help"))]
            with open(self.db_path, 'w', encoding='utf-8') as f:
                json.dump({"patterns": learned}, f, indent=2)
        except Exception as e:
            logger.error(f"Failed to save patterns: {e}")
    
    def get_stats(self) -> Dict[str, Any]:
        """Get pattern statistics"""
        return {
            "total_patterns": len(self._patterns),
            "categories": dict(self._by_category),
            "top_patterns": sorted(
                [(p.id, p.success_count) for p in self._patterns.values()],
                key=lambda x: x[1],
                reverse=True
            )[:10]
        }

