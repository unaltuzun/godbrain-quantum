# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
SERAPH System Awareness
Real-time awareness of all system changes, code updates, and trading state.
═══════════════════════════════════════════════════════════════════════════════
"""

import os
import json
import subprocess
from datetime import datetime, timedelta
from pathlib import Path
from typing import Any, Dict, List, Optional
from dataclasses import dataclass, field, asdict


ROOT = Path(__file__).parent.parent


@dataclass
class GitCommit:
    """Git commit info."""
    hash: str
    author: str
    date: str
    message: str
    files_changed: List[str] = field(default_factory=list)


@dataclass
class SystemState:
    """Current system state snapshot."""
    timestamp: str
    
    # Git state
    branch: str = ""
    last_commits: List[Dict] = field(default_factory=list)
    uncommitted_changes: List[str] = field(default_factory=list)
    
    # DNA state
    current_dna: List[int] = field(default_factory=list)
    dna_generation: int = 0
    dna_fitness: float = 0.0
    
    # Trading state
    equity_usd: float = 0.0
    open_positions: List[Dict] = field(default_factory=list)
    last_trades: List[Dict] = field(default_factory=list)
    current_regime: str = ""
    
    # Infrastructure state
    infra_modules: List[str] = field(default_factory=list)
    backtest_modules: List[str] = field(default_factory=list)
    
    # Recent activity
    recent_logs: List[str] = field(default_factory=list)
    recent_errors: List[str] = field(default_factory=list)
    
    def to_context_string(self) -> str:
        """Convert to context string for LLM."""
        lines = [
            f"=== SYSTEM STATE ({self.timestamp}) ===",
            "",
            f"📌 Git Branch: {self.branch}",
        ]
        
        if self.uncommitted_changes:
            lines.append(f"⚠️ Uncommitted changes: {len(self.uncommitted_changes)} files")
        
        if self.last_commits:
            lines.append(f"📝 Last commit: {self.last_commits[0].get('message', '')[:50]}")
        
        lines.append("")
        lines.append(f"🧬 DNA: {self.current_dna} (Gen {self.dna_generation}, Fit: {self.dna_fitness:.3f})")
        
        lines.append("")
        lines.append(f"💰 Equity: ${self.equity_usd:.2f}")
        lines.append(f"📊 Regime: {self.current_regime}")
        lines.append(f"📈 Open Positions: {len(self.open_positions)}")
        
        if self.recent_errors:
            lines.append("")
            lines.append(f"🚨 Recent Errors: {len(self.recent_errors)}")
        
        return "\n".join(lines)


class SystemAwareness:
    """
    System awareness for Seraph.
    
    Provides real-time context about:
    - Git history and changes
    - DNA evolution state
    - Trading activity
    - Infrastructure modules
    - Logs and errors
    
    Usage:
        awareness = SystemAwareness()
        state = awareness.get_current_state()
        context = awareness.get_context_for_llm()
    """
    
    def __init__(self, root_path: Optional[Path] = None):
        self.root = root_path or ROOT
        self._cache: Dict[str, Any] = {}
        self._cache_ttl = 60  # seconds
        self._last_update = 0
    
    # =========================================================================
    # Git Awareness
    # =========================================================================
    
    def get_git_branch(self) -> str:
        """Get current git branch."""
        try:
            result = subprocess.run(
                ["git", "branch", "--show-current"],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=5
            )
            return result.stdout.strip()
        except Exception:
            return "unknown"
    
    def get_recent_commits(self, n: int = 10) -> List[GitCommit]:
        """Get recent git commits."""
        try:
            result = subprocess.run(
                ["git", "log", f"-{n}", "--pretty=format:%H|%an|%ai|%s"],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            commits = []
            for line in result.stdout.strip().split("\n"):
                if "|" in line:
                    parts = line.split("|", 3)
                    if len(parts) >= 4:
                        commits.append(GitCommit(
                            hash=parts[0][:8],
                            author=parts[1],
                            date=parts[2],
                            message=parts[3]
                        ))
            return commits
        except Exception:
            return []
    
    def get_uncommitted_changes(self) -> List[str]:
        """Get list of uncommitted files."""
        try:
            result = subprocess.run(
                ["git", "status", "--porcelain"],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=5
            )
            
            files = []
            for line in result.stdout.strip().split("\n"):
                if line.strip():
                    files.append(line.strip())
            return files
        except Exception:
            return []
    
    def get_files_changed_today(self) -> List[str]:
        """Get files changed in last 24h."""
        try:
            result = subprocess.run(
                ["git", "log", "--since=24 hours ago", "--name-only", "--pretty=format:"],
                cwd=self.root,
                capture_output=True,
                text=True,
                timeout=10
            )
            
            files = set()
            for line in result.stdout.strip().split("\n"):
                if line.strip() and not line.startswith(" "):
                    files.add(line.strip())
            return list(files)
        except Exception:
            return []
    
    # =========================================================================
    # DNA Awareness
    # =========================================================================
    
    def get_dna_state(self) -> Dict[str, Any]:
        """Get current DNA state from tracker or Redis."""
        state = {
            "dna": [],
            "generation": 0,
            "fitness": 0.0,
        }
        
        # Try DNA tracker first
        try:
            from infrastructure.dna_tracker import get_dna_tracker
            tracker = get_dna_tracker()
            best = tracker.get_best_dna("fitness")
            if best:
                state["dna"] = best.dna
                state["generation"] = best.generation
                state["fitness"] = best.fitness
        except ImportError:
            pass
        
        # Fallback to Redis
        if not state["dna"]:
            try:
                import redis
                r = redis.Redis(
                    host=os.getenv("GENETICS_REDIS_HOST", "127.0.0.1"),
                    password=os.getenv("REDIS_PASS"),
                    decode_responses=True
                )
                dna_str = r.get("godbrain:genetics:best_dna")
                if dna_str:
                    state["dna"] = json.loads(dna_str)
            except Exception:
                pass
        
        return state
    
    # =========================================================================
    # Trading Awareness
    # =========================================================================
    
    def get_trading_state(self) -> Dict[str, Any]:
        """Get current trading state from logs/Redis."""
        state = {
            "equity_usd": 0.0,
            "regime": "",
            "open_positions": [],
            "last_trades": [],
        }
        
        # Read from agg decisions log
        log_file = self.root / "logs" / "agg_decisions.log"
        if log_file.exists():
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    lines = f.readlines()[-50:]
                
                for line in reversed(lines):
                    if "Eq:$" in line:
                        import re
                        match = re.search(r"Eq:\$(\d+)", line)
                        if match:
                            state["equity_usd"] = float(match.group(1))
                    
                    if "TRENDING_" in line:
                        if "TRENDING_UP" in line:
                            state["regime"] = "TRENDING_UP"
                        elif "TRENDING_DOWN" in line:
                            state["regime"] = "TRENDING_DOWN"
                        break
            except Exception:
                pass
        
        return state
    
    # =========================================================================
    # Infrastructure Awareness
    # =========================================================================
    
    def get_infrastructure_modules(self) -> List[str]:
        """List available infrastructure modules."""
        infra_dir = self.root / "infrastructure"
        modules = []
        
        if infra_dir.exists():
            for f in infra_dir.glob("*.py"):
                if not f.name.startswith("_"):
                    modules.append(f.stem)
        
        return sorted(modules)
    
    def get_backtest_modules(self) -> List[str]:
        """List available backtest modules."""
        bt_dir = self.root / "lab" / "backtest"
        modules = []
        
        if bt_dir.exists():
            for f in bt_dir.glob("*.py"):
                if not f.name.startswith("_"):
                    modules.append(f.stem)
        
        return sorted(modules)
    
    # =========================================================================
    # Log Awareness
    # =========================================================================
    
    def get_recent_logs(self, n: int = 20) -> List[str]:
        """Get recent log entries."""
        logs = []
        
        log_file = self.root / "logs" / "agg_decisions.log"
        if log_file.exists():
            try:
                with open(log_file, "r", encoding="utf-8", errors="ignore") as f:
                    logs = f.readlines()[-n:]
                logs = [l.strip() for l in logs if l.strip()]
            except Exception:
                pass
        
        return logs
    
    def get_recent_errors(self, n: int = 10) -> List[str]:
        """Get recent error entries."""
        errors = []
        
        # Check multiple error sources
        error_files = [
            self.root / "logs" / "error.log",
            self.root / "logs" / "seraph_error.log",
        ]
        
        for ef in error_files:
            if ef.exists():
                try:
                    with open(ef, "r", encoding="utf-8", errors="ignore") as f:
                        errors.extend(f.readlines()[-n:])
                except Exception:
                    pass
        
        return [e.strip() for e in errors if e.strip()][-n:]
    
    # =========================================================================
    # Main Interface
    # =========================================================================
    
    def get_current_state(self) -> SystemState:
        """Get complete current system state."""
        now = datetime.now()
        
        # Get git state
        branch = self.get_git_branch()
        commits = self.get_recent_commits(5)
        uncommitted = self.get_uncommitted_changes()
        
        # Get DNA state
        dna_state = self.get_dna_state()
        
        # Get trading state
        trading_state = self.get_trading_state()
        
        # Get infrastructure
        infra = self.get_infrastructure_modules()
        backtest = self.get_backtest_modules()
        
        # Get logs
        logs = self.get_recent_logs(10)
        errors = self.get_recent_errors(5)
        
        return SystemState(
            timestamp=now.isoformat(),
            branch=branch,
            last_commits=[asdict(c) for c in commits],
            uncommitted_changes=uncommitted,
            current_dna=dna_state["dna"],
            dna_generation=dna_state["generation"],
            dna_fitness=dna_state["fitness"],
            equity_usd=trading_state["equity_usd"],
            open_positions=trading_state["open_positions"],
            last_trades=trading_state["last_trades"],
            current_regime=trading_state["regime"],
            infra_modules=infra,
            backtest_modules=backtest,
            recent_logs=logs,
            recent_errors=errors,
        )
    
    def get_context_for_llm(self) -> str:
        """Get formatted context string for LLM injection."""
        state = self.get_current_state()
        return state.to_context_string()
    
    def get_full_context_dict(self) -> Dict[str, Any]:
        """Get full context as dictionary."""
        state = self.get_current_state()
        return asdict(state)
    
    def summarize_recent_changes(self) -> str:
        """Get a natural language summary of recent changes."""
        commits = self.get_recent_commits(5)
        uncommitted = self.get_uncommitted_changes()
        changed_today = self.get_files_changed_today()
        
        lines = ["📋 RECENT SYSTEM CHANGES"]
        lines.append("")
        
        if uncommitted:
            lines.append(f"⚠️ {len(uncommitted)} uncommitted files:")
            for f in uncommitted[:5]:
                lines.append(f"   • {f}")
            if len(uncommitted) > 5:
                lines.append(f"   ... and {len(uncommitted) - 5} more")
        
        if changed_today:
            lines.append(f"\n📝 {len(changed_today)} files changed today:")
            for f in changed_today[:10]:
                lines.append(f"   • {f}")
        
        if commits:
            lines.append(f"\n🔄 Recent commits:")
            for c in commits[:5]:
                lines.append(f"   • [{c.hash}] {c.message[:60]}")
        
        return "\n".join(lines)


# Global instance
_awareness: Optional[SystemAwareness] = None


def get_system_awareness() -> SystemAwareness:
    """Get or create global SystemAwareness instance."""
    global _awareness
    if _awareness is None:
        _awareness = SystemAwareness()
    return _awareness


if __name__ == "__main__":
    print("System Awareness Demo")
    print("=" * 60)
    
    awareness = SystemAwareness()
    
    print("\n" + awareness.get_context_for_llm())
    print("\n" + awareness.summarize_recent_changes())
