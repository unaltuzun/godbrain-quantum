# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
SENTINEL Memory - Pattern Learning & Error History
═══════════════════════════════════════════════════════════════════════════════

Features:
- Persistent memory of all detected issues
- Pattern recognition for similar errors
- Learning from successful fixes
- Evolution tracking over time
"""

import json
import hashlib
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from collections import defaultdict
import logging

logger = logging.getLogger("sentinel.memory")

# Memory file location
MEMORY_DIR = Path(__file__).parent.parent.parent / "seraph" / "memory"
SENTINEL_MEMORY_FILE = MEMORY_DIR / "sentinel_memory.json"


@dataclass
class ErrorPattern:
    """A learned error pattern."""
    pattern_id: str
    error_type: str
    message_pattern: str  # Simplified message pattern
    file_pattern: str  # File path pattern (e.g., "*.py", "config/*.json")
    fix_action: Optional[str]
    occurrences: int = 0
    fixes_applied: int = 0
    success_rate: float = 0.0
    first_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    last_seen: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return asdict(self)
    
    @classmethod
    def from_dict(cls, data: Dict) -> "ErrorPattern":
        return cls(**data)


@dataclass  
class FixRecord:
    """Record of a fix attempt."""
    issue_hash: str
    pattern_id: str
    file: str
    fix_action: str
    success: bool
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    duration_ms: float = 0.0
    
    def to_dict(self) -> Dict:
        return asdict(self)


@dataclass
class EvolutionStats:
    """SENTINEL evolution statistics."""
    total_scans: int = 0
    total_issues_found: int = 0
    total_fixes_applied: int = 0
    total_fixes_successful: int = 0
    patterns_learned: int = 0
    uptime_hours: float = 0.0
    start_time: str = field(default_factory=lambda: datetime.now().isoformat())
    last_evolution: str = field(default_factory=lambda: datetime.now().isoformat())
    
    @property
    def success_rate(self) -> float:
        if self.total_fixes_applied == 0:
            return 0.0
        return self.total_fixes_successful / self.total_fixes_applied
    
    @property
    def issues_per_scan(self) -> float:
        if self.total_scans == 0:
            return 0.0
        return self.total_issues_found / self.total_scans
    
    def to_dict(self) -> Dict:
        d = asdict(self)
        d["success_rate"] = self.success_rate
        d["issues_per_scan"] = self.issues_per_scan
        return d


class SentinelMemory:
    """
    SENTINEL's long-term memory system.
    
    Remembers:
    - All detected issues and their fixes
    - Learned error patterns
    - Fix success rates
    - Evolution statistics
    
    Usage:
        memory = SentinelMemory()
        
        # Record an issue
        memory.remember_issue(issue)
        
        # Find similar past issues
        similar = memory.find_similar(issue)
        
        # Record a fix
        memory.record_fix(issue, success=True)
        
        # Get evolution stats
        stats = memory.get_evolution_stats()
    """
    
    def __init__(self, memory_file: Path = None):
        self.memory_file = memory_file or SENTINEL_MEMORY_FILE
        self.memory_file.parent.mkdir(parents=True, exist_ok=True)
        
        # In-memory state
        self.patterns: Dict[str, ErrorPattern] = {}
        self.recent_issues: List[Dict] = []  # Last 1000 issues
        self.fix_records: List[FixRecord] = []  # Last 1000 fixes
        self.stats = EvolutionStats()
        
        # Load from disk
        self._load()
        
        logger.info(f"SENTINEL Memory loaded: {len(self.patterns)} patterns, {self.stats.total_scans} scans")
    
    def _load(self):
        """Load memory from disk."""
        if not self.memory_file.exists():
            return
        
        try:
            data = json.loads(self.memory_file.read_text(encoding='utf-8'))
            
            # Load patterns
            for p in data.get("patterns", []):
                pattern = ErrorPattern.from_dict(p)
                self.patterns[pattern.pattern_id] = pattern
            
            # Load recent issues
            self.recent_issues = data.get("recent_issues", [])[-1000:]
            
            # Load fix records
            self.fix_records = [
                FixRecord(**r) for r in data.get("fix_records", [])[-1000:]
            ]
            
            # Load stats
            if "stats" in data:
                self.stats = EvolutionStats(**data["stats"])
            
        except Exception as e:
            logger.error(f"Failed to load memory: {e}")
    
    def _save(self):
        """Save memory to disk."""
        try:
            data = {
                "patterns": [p.to_dict() for p in self.patterns.values()],
                "recent_issues": self.recent_issues[-1000:],
                "fix_records": [r.to_dict() for r in self.fix_records[-1000:]],
                "stats": asdict(self.stats),
                "last_saved": datetime.now().isoformat(),
            }
            
            self.memory_file.write_text(
                json.dumps(data, indent=2, ensure_ascii=False),
                encoding='utf-8'
            )
        except Exception as e:
            logger.error(f"Failed to save memory: {e}")
    
    def _generate_pattern_id(self, error_type: str, message: str, file: str) -> str:
        """Generate a unique pattern ID from error characteristics."""
        # Normalize message (remove line numbers, specific values)
        import re
        normalized_msg = re.sub(r'\d+', 'N', message)
        normalized_msg = re.sub(r'[a-f0-9]{8,}', 'HASH', normalized_msg)
        
        # Get file extension/type pattern
        file_ext = Path(file).suffix or "unknown"
        
        # Create hash
        pattern_str = f"{error_type}:{normalized_msg}:{file_ext}"
        return hashlib.md5(pattern_str.encode()).hexdigest()[:12]
    
    def _calculate_similarity(self, issue1: Dict, issue2: Dict) -> float:
        """Calculate similarity between two issues (0.0 - 1.0)."""
        score = 0.0
        
        # Same type: +0.4
        if issue1.get("type") == issue2.get("type"):
            score += 0.4
        
        # Same file extension: +0.2
        ext1 = Path(issue1.get("file", "")).suffix
        ext2 = Path(issue2.get("file", "")).suffix
        if ext1 and ext1 == ext2:
            score += 0.2
        
        # Similar message: +0.4
        msg1 = issue1.get("message", "").lower()
        msg2 = issue2.get("message", "").lower()
        
        # Simple word overlap
        words1 = set(msg1.split())
        words2 = set(msg2.split())
        if words1 and words2:
            overlap = len(words1 & words2) / max(len(words1), len(words2))
            score += 0.4 * overlap
        
        return score
    
    def remember_issue(self, issue: Dict) -> str:
        """
        Remember an issue and learn from it.
        Returns the pattern_id for this issue.
        """
        pattern_id = self._generate_pattern_id(
            issue.get("type", "unknown"),
            issue.get("message", ""),
            issue.get("file", "")
        )
        
        # Update or create pattern
        if pattern_id in self.patterns:
            pattern = self.patterns[pattern_id]
            pattern.occurrences += 1
            pattern.last_seen = datetime.now().isoformat()
        else:
            # New pattern - learn it
            pattern = ErrorPattern(
                pattern_id=pattern_id,
                error_type=issue.get("type", "unknown"),
                message_pattern=issue.get("message", "")[:100],
                file_pattern=f"*{Path(issue.get('file', '')).suffix}",
                fix_action=issue.get("fix_action"),
                occurrences=1,
            )
            self.patterns[pattern_id] = pattern
            self.stats.patterns_learned += 1
            logger.info(f"Learned new pattern: {pattern_id}")
        
        # Store in recent issues
        issue_record = {
            **issue,
            "pattern_id": pattern_id,
            "remembered_at": datetime.now().isoformat(),
        }
        self.recent_issues.append(issue_record)
        self.recent_issues = self.recent_issues[-1000:]  # Keep last 1000
        
        self.stats.total_issues_found += 1
        
        return pattern_id
    
    def record_fix(self, issue: Dict, success: bool, duration_ms: float = 0.0):
        """Record a fix attempt and update pattern success rate."""
        pattern_id = issue.get("pattern_id") or self._generate_pattern_id(
            issue.get("type", "unknown"),
            issue.get("message", ""),
            issue.get("file", "")
        )
        
        # Create fix record
        record = FixRecord(
            issue_hash=hashlib.md5(str(issue).encode()).hexdigest()[:8],
            pattern_id=pattern_id,
            file=issue.get("file", ""),
            fix_action=issue.get("fix_action", "unknown"),
            success=success,
            duration_ms=duration_ms,
        )
        self.fix_records.append(record)
        self.fix_records = self.fix_records[-1000:]
        
        # Update pattern stats
        if pattern_id in self.patterns:
            pattern = self.patterns[pattern_id]
            pattern.fixes_applied += 1
            if success:
                pattern.success_rate = (
                    (pattern.success_rate * (pattern.fixes_applied - 1) + 1.0) 
                    / pattern.fixes_applied
                )
            else:
                pattern.success_rate = (
                    (pattern.success_rate * (pattern.fixes_applied - 1)) 
                    / pattern.fixes_applied
                )
        
        # Update global stats
        self.stats.total_fixes_applied += 1
        if success:
            self.stats.total_fixes_successful += 1
    
    def find_similar(self, issue: Dict, min_similarity: float = 0.6) -> List[Tuple[Dict, float]]:
        """
        Find similar past issues.
        Returns list of (issue, similarity_score) tuples.
        """
        similar = []
        
        for past_issue in reversed(self.recent_issues[-100:]):
            similarity = self._calculate_similarity(issue, past_issue)
            if similarity >= min_similarity:
                similar.append((past_issue, similarity))
        
        # Sort by similarity (highest first)
        similar.sort(key=lambda x: x[1], reverse=True)
        
        return similar[:5]  # Top 5
    
    def get_fix_suggestion(self, issue: Dict) -> Optional[str]:
        """
        Get a fix suggestion based on past successful fixes.
        """
        pattern_id = self._generate_pattern_id(
            issue.get("type", "unknown"),
            issue.get("message", ""),
            issue.get("file", "")
        )
        
        if pattern_id in self.patterns:
            pattern = self.patterns[pattern_id]
            if pattern.success_rate > 0.5 and pattern.fix_action:
                return pattern.fix_action
        
        # Try finding similar issues
        similar = self.find_similar(issue)
        for past_issue, _ in similar:
            if past_issue.get("fixed") and past_issue.get("fix_action"):
                return past_issue["fix_action"]
        
        return None
    
    def record_scan(self, issues_count: int):
        """Record that a scan was performed."""
        self.stats.total_scans += 1
        self.stats.last_evolution = datetime.now().isoformat()
        
        # Calculate uptime
        start = datetime.fromisoformat(self.stats.start_time)
        self.stats.uptime_hours = (datetime.now() - start).total_seconds() / 3600
    
    def get_evolution_stats(self) -> Dict:
        """Get current evolution statistics."""
        return self.stats.to_dict()
    
    def get_top_patterns(self, n: int = 10) -> List[ErrorPattern]:
        """Get top N most frequent error patterns."""
        sorted_patterns = sorted(
            self.patterns.values(),
            key=lambda p: p.occurrences,
            reverse=True
        )
        return sorted_patterns[:n]
    
    def get_recent_fixes(self, n: int = 10) -> List[FixRecord]:
        """Get most recent fix records."""
        return self.fix_records[-n:]
    
    def evolve(self):
        """
        Perform evolution: analyze patterns and optimize strategies.
        Called periodically (e.g., every hour).
        """
        logger.info("🧬 SENTINEL Evolution cycle...")
        
        # 1. Prune old low-frequency patterns
        one_week_ago = (datetime.now() - timedelta(days=7)).isoformat()
        pruned = 0
        for pattern_id, pattern in list(self.patterns.items()):
            if pattern.last_seen < one_week_ago and pattern.occurrences < 3:
                del self.patterns[pattern_id]
                pruned += 1
        
        if pruned > 0:
            logger.info(f"  Pruned {pruned} inactive patterns")
        
        # 2. Log evolution stats
        stats = self.get_evolution_stats()
        logger.info(f"  Total patterns: {len(self.patterns)}")
        logger.info(f"  Fix success rate: {stats['success_rate']:.1%}")
        logger.info(f"  Issues per scan: {stats['issues_per_scan']:.2f}")
        logger.info(f"  Uptime: {stats['uptime_hours']:.1f} hours")
        
        # 3. Save state
        self._save()
        
        self.stats.last_evolution = datetime.now().isoformat()
    
    def save(self):
        """Explicitly save memory to disk."""
        self._save()
    
    def get_memory_summary(self) -> str:
        """Get a human-readable memory summary."""
        stats = self.get_evolution_stats()
        top_patterns = self.get_top_patterns(3)
        
        lines = [
            "🧠 SENTINEL Memory Summary",
            f"  Patterns learned: {len(self.patterns)}",
            f"  Total scans: {stats['total_scans']}",
            f"  Fix success rate: {stats['success_rate']:.1%}",
            f"  Uptime: {stats['uptime_hours']:.1f}h",
            "",
            "  Top error patterns:",
        ]
        
        for p in top_patterns:
            lines.append(f"    • {p.error_type}: {p.occurrences}x ({p.success_rate:.0%} fixed)")
        
        return "\n".join(lines)


# Global instance
_memory: Optional[SentinelMemory] = None


def get_sentinel_memory() -> SentinelMemory:
    """Get or create global SENTINEL memory instance."""
    global _memory
    if _memory is None:
        _memory = SentinelMemory()
    return _memory


if __name__ == "__main__":
    # Quick test
    memory = SentinelMemory()
    
    # Simulate some issues
    test_issue = {
        "type": "syntax_error",
        "file": "test.py",
        "message": "SyntaxError: invalid syntax at line 42",
        "fix_action": "fix_syntax",
    }
    
    pattern_id = memory.remember_issue(test_issue)
    print(f"Pattern ID: {pattern_id}")
    
    memory.record_fix(test_issue, success=True, duration_ms=50)
    memory.record_scan(1)
    
    print(memory.get_memory_summary())
    memory.save()
