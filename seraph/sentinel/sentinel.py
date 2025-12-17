# -*- coding: utf-8 -*-
"""
═══════════════════════════════════════════════════════════════════════════════
SENTINEL - The Bug Keeper Daemon
Automated system health monitoring, bug detection, and self-healing.
═══════════════════════════════════════════════════════════════════════════════

Features:
- 10-minute scan cycles for bugs and errors
- Auto-fix for common issues
- Daily markdown reports with git commit
- Telegram alerts for critical errors

Usage:
    python -m seraph.sentinel --daemon
    python -m seraph.sentinel --scan-once
"""

import os
import sys
import ast
import time
import json
import signal
import logging
import argparse
import subprocess
from pathlib import Path
from datetime import datetime, timedelta
from typing import Dict, List, Optional, Any, Tuple
from dataclasses import dataclass, field, asdict
from enum import Enum

# Add project root to path
ROOT = Path(__file__).parent.parent.parent
sys.path.insert(0, str(ROOT))


# =============================================================================
# CONFIGURATION
# =============================================================================

SCAN_INTERVAL_MINUTES = 10
REPORT_HOUR = 9  # Daily report at 9 AM
EVOLUTION_INTERVAL_CYCLES = 6  # Evolve every 6 cycles (1 hour at 10min intervals)
EXCLUDED_DIRS = {".git", "__pycache__", ".venv", "venv", "node_modules", ".mypy_cache", ".pytest_cache", "backups"}
EXCLUDED_FILES = {"__pycache__", ".pyc"}

# Logging setup
LOG_DIR = ROOT / "logs"
LOG_DIR.mkdir(exist_ok=True)

logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s [%(levelname)s] %(name)s: %(message)s',
    handlers=[
        logging.StreamHandler(),
        logging.FileHandler(LOG_DIR / 'sentinel.log', encoding='utf-8')
    ]
)
logger = logging.getLogger("sentinel")


# =============================================================================
# DATA MODELS
# =============================================================================

class Severity(Enum):
    INFO = "info"
    WARNING = "warning"
    ERROR = "error"
    CRITICAL = "critical"


class IssueType(Enum):
    SYNTAX_ERROR = "syntax_error"
    IMPORT_ERROR = "import_error"
    CONFIG_ERROR = "config_error"
    MISSING_INIT = "missing_init"
    LOG_ERROR = "log_error"
    ORPHAN_FILE = "orphan_file"
    LAB_HEALTH = "lab_health"  # Physics lab monitoring


@dataclass
class Issue:
    """Detected issue."""
    type: IssueType
    severity: Severity
    file: str
    line: Optional[int]
    message: str
    fixable: bool = False
    fixed: bool = False
    fix_action: Optional[str] = None
    timestamp: str = field(default_factory=lambda: datetime.now().isoformat())
    
    def to_dict(self) -> Dict:
        return {
            "type": self.type.value,
            "severity": self.severity.value,
            "file": self.file,
            "line": self.line,
            "message": self.message,
            "fixable": self.fixable,
            "fixed": self.fixed,
            "fix_action": self.fix_action,
            "timestamp": self.timestamp,
        }


@dataclass
class ScanResult:
    """Result of a full system scan."""
    timestamp: str
    duration_seconds: float
    files_scanned: int
    issues: List[Issue] = field(default_factory=list)
    fixes_applied: int = 0
    
    @property
    def critical_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.CRITICAL)
    
    @property
    def error_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.ERROR)
    
    @property
    def warning_count(self) -> int:
        return sum(1 for i in self.issues if i.severity == Severity.WARNING)
    
    def to_dict(self) -> Dict:
        return {
            "timestamp": self.timestamp,
            "duration_seconds": self.duration_seconds,
            "files_scanned": self.files_scanned,
            "issues": [i.to_dict() for i in self.issues],
            "fixes_applied": self.fixes_applied,
            "summary": {
                "critical": self.critical_count,
                "error": self.error_count,
                "warning": self.warning_count,
            }
        }


# =============================================================================
# SCANNERS
# =============================================================================

class SyntaxScanner:
    """Scan Python files for syntax errors."""
    
    def scan(self, root: Path) -> List[Issue]:
        issues = []
        
        for py_file in root.rglob("*.py"):
            if any(ex in py_file.parts for ex in EXCLUDED_DIRS):
                continue
            
            try:
                source_bytes = py_file.read_bytes()
                has_bom = source_bytes.startswith(b'\xef\xbb\xbf')
                source = source_bytes.decode('utf-8-sig', errors='ignore')  # Handle BOM
                ast.parse(source)
                
                # Still report BOM as fixable even if syntax is OK
                if has_bom:
                    issues.append(Issue(
                        type=IssueType.SYNTAX_ERROR,
                        severity=Severity.WARNING,
                        file=str(py_file.relative_to(root)),
                        line=1,
                        message="File has UTF-8 BOM (U+FEFF) - should be removed",
                        fixable=True,
                        fix_action="fix_bom"
                    ))
            except SyntaxError as e:
                # Check if BOM is the cause
                source_bytes = py_file.read_bytes()
                has_bom = source_bytes.startswith(b'\xef\xbb\xbf')
                
                issues.append(Issue(
                    type=IssueType.SYNTAX_ERROR,
                    severity=Severity.CRITICAL,
                    file=str(py_file.relative_to(root)),
                    line=e.lineno,
                    message=f"SyntaxError: {e.msg}",
                    fixable=has_bom,  # Fixable if caused by BOM
                    fix_action="fix_bom" if has_bom else None
                ))
            except Exception as e:
                logger.debug(f"Error parsing {py_file}: {e}")
        
        return issues


class ImportScanner:
    """Check for import issues."""
    
    def scan(self, root: Path) -> List[Issue]:
        issues = []
        
        for py_file in root.rglob("*.py"):
            if any(ex in py_file.parts for ex in EXCLUDED_DIRS):
                continue
            
            try:
                source = py_file.read_text(encoding='utf-8', errors='ignore')
                tree = ast.parse(source)
                
                for node in ast.walk(tree):
                    if isinstance(node, ast.Import):
                        for alias in node.names:
                            if not self._can_import(alias.name, root):
                                issues.append(Issue(
                                    type=IssueType.IMPORT_ERROR,
                                    severity=Severity.WARNING,
                                    file=str(py_file.relative_to(root)),
                                    line=node.lineno,
                                    message=f"Import '{alias.name}' may not be available",
                                    fixable=False
                                ))
                    
                    elif isinstance(node, ast.ImportFrom):
                        if node.module and not self._can_import(node.module, root):
                            # Check if it's a local module
                            module_path = root / node.module.replace(".", "/")
                            if not (module_path.exists() or (module_path.with_suffix(".py")).exists()):
                                issues.append(Issue(
                                    type=IssueType.IMPORT_ERROR,
                                    severity=Severity.WARNING,
                                    file=str(py_file.relative_to(root)),
                                    line=node.lineno,
                                    message=f"Import from '{node.module}' may not be available",
                                    fixable=False
                                ))
            except SyntaxError:
                pass  # Handled by SyntaxScanner
            except Exception as e:
                logger.debug(f"Error checking imports in {py_file}: {e}")
        
        return issues
    
    def _can_import(self, module_name: str, root: Path) -> bool:
        """Check if a module can be imported."""
        # Standard library and common packages
        safe_modules = {
            "os", "sys", "json", "time", "datetime", "pathlib", "typing",
            "logging", "asyncio", "subprocess", "re", "math", "random",
            "collections", "itertools", "functools", "dataclasses", "enum",
            "abc", "copy", "hashlib", "base64", "threading", "signal",
            "numpy", "pandas", "redis", "ccxt", "anthropic", "requests",
            "aiohttp", "pytest", "pydantic"
        }
        
        base_module = module_name.split(".")[0]
        
        if base_module in safe_modules:
            return True
        
        # Check if it's a local module
        module_path = root / base_module
        if module_path.exists() or (root / f"{base_module}.py").exists():
            return True
        
        return True  # Assume OK for other modules


class ConfigScanner:
    """Validate JSON/YAML configuration files."""
    
    def scan(self, root: Path) -> List[Issue]:
        issues = []
        
        # Scan JSON files
        for json_file in root.rglob("*.json"):
            if any(ex in json_file.parts for ex in EXCLUDED_DIRS):
                continue
            
            try:
                content = json_file.read_text(encoding='utf-8')
                json.loads(content)
            except json.JSONDecodeError as e:
                issues.append(Issue(
                    type=IssueType.CONFIG_ERROR,
                    severity=Severity.ERROR,
                    file=str(json_file.relative_to(root)),
                    line=e.lineno,
                    message=f"Invalid JSON: {e.msg}",
                    fixable=False
                ))
            except Exception as e:
                logger.debug(f"Error reading {json_file}: {e}")
        
        # Scan YAML files
        try:
            import yaml
            for yaml_file in list(root.rglob("*.yaml")) + list(root.rglob("*.yml")):
                if any(ex in yaml_file.parts for ex in EXCLUDED_DIRS):
                    continue
                
                try:
                    content = yaml_file.read_text(encoding='utf-8')
                    yaml.safe_load(content)
                except yaml.YAMLError as e:
                    issues.append(Issue(
                        type=IssueType.CONFIG_ERROR,
                        severity=Severity.ERROR,
                        file=str(yaml_file.relative_to(root)),
                        line=getattr(e, 'problem_mark', None) and e.problem_mark.line,
                        message=f"Invalid YAML: {str(e)[:100]}",
                        fixable=False
                    ))
        except ImportError:
            pass  # YAML not installed
        
        return issues


class InitScanner:
    """Find directories missing __init__.py."""
    
    def scan(self, root: Path) -> List[Issue]:
        issues = []
        
        for dir_path in root.rglob("*"):
            if not dir_path.is_dir():
                continue
            if any(ex in dir_path.parts for ex in EXCLUDED_DIRS):
                continue
            
            # Check if directory contains Python files
            py_files = list(dir_path.glob("*.py"))
            if py_files and not (dir_path / "__init__.py").exists():
                # Check if parent has __init__.py (indicates it should be a package)
                parent_init = dir_path.parent / "__init__.py"
                if parent_init.exists() or dir_path.parent == root:
                    issues.append(Issue(
                        type=IssueType.MISSING_INIT,
                        severity=Severity.WARNING,
                        file=str(dir_path.relative_to(root)),
                        line=None,
                        message=f"Directory '{dir_path.name}' has Python files but no __init__.py",
                        fixable=True,
                        fix_action="create_init"
                    ))
        
        return issues


class LogScanner:
    """Scan log files for recent errors."""
    
    def scan(self, root: Path) -> List[Issue]:
        issues = []
        log_dir = root / "logs"
        
        if not log_dir.exists():
            return issues
        
        # Keywords that indicate errors
        error_keywords = ["ERROR", "CRITICAL", "Exception", "Traceback", "FATAL"]
        
        for log_file in log_dir.glob("*.log"):
            try:
                # Only check recent entries (last 1000 lines)
                content = log_file.read_text(encoding='utf-8', errors='ignore')
                lines = content.splitlines()[-1000:]
                
                # Check for errors in last hour
                for i, line in enumerate(lines):
                    if any(kw in line for kw in error_keywords):
                        # Try to parse timestamp
                        try:
                            timestamp_str = line[:19]
                            log_time = datetime.fromisoformat(timestamp_str)
                            if datetime.now() - log_time < timedelta(hours=1):
                                issues.append(Issue(
                                    type=IssueType.LOG_ERROR,
                                    severity=Severity.ERROR if "CRITICAL" in line else Severity.WARNING,
                                    file=str(log_file.relative_to(root)),
                                    line=len(lines) - len(lines) + i + 1,
                                    message=line[:200],
                                    fixable=False
                                ))
                        except (ValueError, IndexError):
                            pass
            except Exception as e:
                logger.debug(f"Error scanning log {log_file}: {e}")
        
        return issues


class LabScanner:
    """
    Monitor Physics Lab and Bridge health.
    
    Checks:
    - Lab state cache freshness
    - Evolution daemon activity
    - Bridge connectivity
    """
    
    def scan(self, root: Path) -> List[Issue]:
        issues = []
        
        # Check lab state cache
        lab_cache = root / "data" / "lab_state.json"
        
        if not lab_cache.exists():
            issues.append(Issue(
                type=IssueType.LAB_HEALTH,
                severity=Severity.WARNING,
                file="data/lab_state.json",
                line=None,
                message="Lab state cache not found - evolution daemon may not be running",
                fixable=False
            ))
            return issues
        
        try:
            import json
            data = json.loads(lab_cache.read_text(encoding='utf-8'))
            
            # Check cache freshness (should be < 5 minutes old)
            timestamp = datetime.fromisoformat(data.get("timestamp", ""))
            age_minutes = (datetime.now() - timestamp).total_seconds() / 60
            
            if age_minutes > 10:
                issues.append(Issue(
                    type=IssueType.LAB_HEALTH,
                    severity=Severity.WARNING,
                    file="data/lab_state.json",
                    line=None,
                    message=f"Lab cache is {age_minutes:.0f} minutes old - daemon may be stopped",
                    fixable=False
                ))
            
            # Check genome health
            alive = data.get("alive_genomes", 0)
            total = data.get("total_genomes", 0)
            
            if total > 0 and alive / total < 0.5:
                issues.append(Issue(
                    type=IssueType.LAB_HEALTH,
                    severity=Severity.WARNING,
                    file="quantum_lab/godbrain_core",
                    line=None,
                    message=f"Low genome survival rate: {alive}/{total} ({alive/total:.0%})",
                    fixable=False
                ))
            
            # Check noise robustness
            noise_rob = data.get("noise_robustness", 0)
            if noise_rob < 0.5:
                issues.append(Issue(
                    type=IssueType.LAB_HEALTH,
                    severity=Severity.INFO,
                    file="quantum_lab/godbrain_core",
                    line=None,
                    message=f"Lab noise robustness is low: {noise_rob:.1%}",
                    fixable=False
                ))
            
            # Log lab status (not an issue, just info)
            logger.debug(
                f"Lab health: {alive} alive genomes, "
                f"robustness={noise_rob:.1%}, cache age={age_minutes:.1f}m"
            )
            
        except Exception as e:
            issues.append(Issue(
                type=IssueType.LAB_HEALTH,
                severity=Severity.ERROR,
                file="data/lab_state.json",
                line=None,
                message=f"Failed to parse lab state: {e}",
                fixable=False
            ))
        
        return issues


# =============================================================================
# AUTO-FIXER
# =============================================================================

class AutoFixer:
    """Automatically fix detected issues."""
    
    def __init__(self, root: Path, dry_run: bool = False):
        self.root = root
        self.dry_run = dry_run
    
    def fix(self, issue: Issue) -> bool:
        """Attempt to fix an issue. Returns True if fixed."""
        if not issue.fixable:
            return False
        
        try:
            if issue.fix_action == "create_init":
                return self._create_init(issue)
            elif issue.fix_action == "fix_bom":
                return self._fix_bom(issue)
            
            return False
        except Exception as e:
            logger.error(f"Fix failed for {issue.file}: {e}")
            return False
    
    def _create_init(self, issue: Issue) -> bool:
        """Create missing __init__.py file."""
        init_path = self.root / issue.file / "__init__.py"
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would create {init_path}")
            return True
        
        init_content = f'''# -*- coding: utf-8 -*-
"""
{Path(issue.file).name} package
Auto-generated by SENTINEL on {datetime.now().strftime('%Y-%m-%d %H:%M')}
"""
'''
        init_path.write_text(init_content, encoding='utf-8')
        logger.info(f"Created {init_path}")
        return True
    
    def _fix_bom(self, issue: Issue) -> bool:
        """Remove UTF-8 BOM from file."""
        file_path = self.root / issue.file
        
        if self.dry_run:
            logger.info(f"[DRY RUN] Would fix BOM in {file_path}")
            return True
        
        try:
            # Read with potential BOM
            content = file_path.read_bytes()
            
            # Check and remove BOM
            if content.startswith(b'\xef\xbb\xbf'):
                content = content[3:]  # Remove BOM
                file_path.write_bytes(content)
                logger.info(f"Removed BOM from {file_path}")
                return True
            
            return False
        except Exception as e:
            logger.error(f"BOM fix failed for {file_path}: {e}")
            return False


# =============================================================================
# REPORTER
# =============================================================================

class Reporter:
    """Generate and distribute reports."""
    
    def __init__(self, root: Path):
        self.root = root
        self.report_dir = root / "reports" / "sentinel"
        self.report_dir.mkdir(parents=True, exist_ok=True)
    
    def generate_daily_report(self, results: List[ScanResult]) -> Path:
        """Generate daily markdown report."""
        today = datetime.now().strftime("%Y-%m-%d")
        report_file = self.report_dir / f"sentinel_report_{today}.md"
        
        # Aggregate results
        total_issues = sum(len(r.issues) for r in results)
        total_fixes = sum(r.fixes_applied for r in results)
        total_critical = sum(r.critical_count for r in results)
        total_errors = sum(r.error_count for r in results)
        
        # Generate report
        report = f"""# 🛡️ SENTINEL Daily Report - {today}

## Summary
- **Scans Performed:** {len(results)}
- **Total Issues Detected:** {total_issues}
- **Issues Fixed:** {total_fixes}
- **Critical Issues:** {total_critical}
- **Errors:** {total_errors}

## Status
{"🟢 **HEALTHY** - No critical issues" if total_critical == 0 else "🔴 **ATTENTION REQUIRED** - Critical issues detected"}

"""
        
        if results:
            report += "## Scan Details\n\n"
            for result in results[-10:]:  # Last 10 scans
                report += f"### {result.timestamp[:16]}\n"
                report += f"- Files scanned: {result.files_scanned}\n"
                report += f"- Issues: {len(result.issues)} (Fixed: {result.fixes_applied})\n"
                
                if result.issues:
                    report += "\n| Severity | Type | File | Message |\n"
                    report += "|----------|------|------|--------|\n"
                    for issue in result.issues[:10]:
                        report += f"| {issue.severity.value} | {issue.type.value} | `{issue.file}` | {issue.message[:50]}... |\n"
                    if len(result.issues) > 10:
                        report += f"\n*... and {len(result.issues) - 10} more issues*\n"
                
                report += "\n"
        
        report += f"\n---\n*Generated by SENTINEL at {datetime.now().isoformat()}*\n"
        
        report_file.write_text(report, encoding='utf-8')
        logger.info(f"Daily report saved to {report_file}")
        
        return report_file
    
    def git_commit_report(self, report_file: Path) -> bool:
        """Commit report to git."""
        try:
            subprocess.run(
                ["git", "add", str(report_file)],
                cwd=self.root,
                capture_output=True,
                timeout=10
            )
            
            result = subprocess.run(
                ["git", "commit", "-m", f"[SENTINEL] Daily report {datetime.now().strftime('%Y-%m-%d')}"],
                cwd=self.root,
                capture_output=True,
                timeout=10
            )
            
            if result.returncode == 0:
                logger.info("Report committed to git")
                return True
            else:
                logger.debug(f"Git commit skipped: {result.stderr.decode()}")
                return False
                
        except Exception as e:
            logger.warning(f"Git commit failed: {e}")
            return False
    
    def send_telegram_alert(self, result: ScanResult) -> bool:
        """Send Telegram alert for critical issues."""
        if result.critical_count == 0:
            return False
        
        try:
            from infrastructure.telegram_alerts import get_alerter, Alert, AlertLevel
            
            alerter = get_alerter()
            if not alerter._enabled:
                logger.warning("Telegram not configured - skipping alert")
                return False
            
            # Build alert message
            critical_issues = [i for i in result.issues if i.severity == Severity.CRITICAL]
            
            message = f"Detected {len(critical_issues)} critical issue(s):\n\n"
            
            for issue in critical_issues[:5]:
                message += f"• {issue.file}\n  {issue.message[:100]}\n\n"
            
            if len(critical_issues) > 5:
                message += f"... and {len(critical_issues) - 5} more\n"
            
            alert = Alert(
                level=AlertLevel.CRITICAL,
                title="SENTINEL Critical Issues",
                message=message
            )
            
            # Send synchronously if possible (limited asyncio compatibility)
            import asyncio
            try:
                loop = asyncio.get_event_loop()
                if loop.is_running():
                    asyncio.create_task(alerter.send_alert(alert))
                else:
                    loop.run_until_complete(alerter.send_alert(alert))
            except RuntimeError:
                asyncio.run(alerter.send_alert(alert))
            
            logger.info("Telegram alert sent")
            return True
            
        except Exception as e:
            logger.error(f"Telegram alert failed: {e}")
            return False


# =============================================================================
# SENTINEL DAEMON
# =============================================================================

class Sentinel:
    """
    SENTINEL - The Bug Keeper Daemon
    
    Continuously monitors the codebase for issues and automatically fixes them.
    Features memory and pattern learning for smarter fixes.
    """
    
    def __init__(self, root: Path = None, dry_run: bool = False):
        self.root = root or ROOT
        self.dry_run = dry_run
        self.running = False
        
        # Memory system
        from seraph.sentinel.memory import get_sentinel_memory
        self.memory = get_sentinel_memory()
        
        # Components
        self.scanners = [
            SyntaxScanner(),
            ImportScanner(),
            ConfigScanner(),
            InitScanner(),
            LogScanner(),
            LabScanner(),  # Physics lab monitoring
        ]
        self.fixer = AutoFixer(self.root, dry_run=dry_run)
        self.reporter = Reporter(self.root)
        
        # State
        self.scan_results: List[ScanResult] = []
        self.last_report_date: Optional[str] = None
        self.last_evolution_cycle: int = 0
        self.cycles_completed = 0
        
        logger.info(f"SENTINEL initialized with memory ({len(self.memory.patterns)} patterns learned)")
    
    def scan(self) -> ScanResult:
        """Perform a full system scan."""
        start_time = time.time()
        logger.info("Starting system scan...")
        
        all_issues: List[Issue] = []
        files_scanned = len(list(self.root.rglob("*.py")))
        
        # Run all scanners
        for scanner in self.scanners:
            try:
                issues = scanner.scan(self.root)
                all_issues.extend(issues)
                logger.debug(f"{scanner.__class__.__name__}: {len(issues)} issues")
            except Exception as e:
                logger.error(f"Scanner {scanner.__class__.__name__} failed: {e}")
        
        # Create result
        result = ScanResult(
            timestamp=datetime.now().isoformat(),
            duration_seconds=time.time() - start_time,
            files_scanned=files_scanned,
            issues=all_issues,
        )
        
        logger.info(
            f"Scan complete: {files_scanned} files, {len(all_issues)} issues "
            f"(Critical: {result.critical_count}, Error: {result.error_count})"
        )
        
        return result
    
    def fix_issues(self, result: ScanResult) -> int:
        """Attempt to fix all fixable issues with memory-enhanced fixing."""
        fixes = 0
        
        for issue in result.issues:
            issue_dict = issue.to_dict()
            
            # Remember the issue (learn patterns)
            pattern_id = self.memory.remember_issue(issue_dict)
            issue_dict["pattern_id"] = pattern_id
            
            # Check for fix suggestion from memory
            if not issue.fix_action:
                suggested_fix = self.memory.get_fix_suggestion(issue_dict)
                if suggested_fix:
                    issue.fix_action = suggested_fix
                    issue.fixable = True
                    logger.info(f"Memory suggested fix '{suggested_fix}' for {issue.file}")
            
            # Try to fix
            if issue.fixable and not issue.fixed:
                start_time = time.time()
                success = self.fixer.fix(issue)
                duration_ms = (time.time() - start_time) * 1000
                
                if success:
                    issue.fixed = True
                    fixes += 1
                
                # Record fix attempt in memory
                self.memory.record_fix(issue_dict, success=success, duration_ms=duration_ms)
        
        result.fixes_applied = fixes
        
        if fixes > 0:
            logger.info(f"Applied {fixes} automatic fixes")
        
        # Record scan in memory
        self.memory.record_scan(len(result.issues))
        
        return fixes
    
    def should_send_daily_report(self) -> bool:
        """Check if it's time for daily report."""
        now = datetime.now()
        today = now.strftime("%Y-%m-%d")
        
        # Send report if: different day AND around report hour
        if self.last_report_date != today and now.hour >= REPORT_HOUR:
            return True
        
        return False
    
    def run_cycle(self) -> ScanResult:
        """Run one monitoring cycle with memory integration."""
        logger.info(f"=== Cycle {self.cycles_completed + 1} ===")
        
        # 1. Scan
        result = self.scan()
        
        # 2. Fix issues with memory
        self.fix_issues(result)
        
        # 3. Store result
        self.scan_results.append(result)
        # Keep only last 144 results (24h worth at 10min intervals)
        self.scan_results = self.scan_results[-144:]
        
        # 4. Telegram alert for critical issues
        if result.critical_count > 0:
            self.reporter.send_telegram_alert(result)
        
        # 5. Daily report
        if self.should_send_daily_report():
            report_file = self.reporter.generate_daily_report(self.scan_results)
            self.reporter.git_commit_report(report_file)
            self.last_report_date = datetime.now().strftime("%Y-%m-%d")
        
        # 6. Evolution cycle (every hour)
        self.cycles_completed += 1
        if self.cycles_completed - self.last_evolution_cycle >= EVOLUTION_INTERVAL_CYCLES:
            self.memory.evolve()
            self.memory.save()
            self.last_evolution_cycle = self.cycles_completed
            logger.info(self.memory.get_memory_summary())
        
        return result
    
    def run(self, interval_minutes: int = SCAN_INTERVAL_MINUTES, max_cycles: int = None):
        """Run daemon continuously."""
        self.running = True
        
        logger.info("=" * 60)
        logger.info("🛡️ SENTINEL BUG KEEPER STARTING")
        logger.info(f"Scan interval: {interval_minutes} minutes")
        logger.info(f"Report hour: {REPORT_HOUR}:00")
        logger.info(f"Dry run: {self.dry_run}")
        logger.info("=" * 60)
        
        # Signal handling
        def signal_handler(signum, frame):
            logger.info("Shutdown signal received")
            self.running = False
        
        signal.signal(signal.SIGINT, signal_handler)
        signal.signal(signal.SIGTERM, signal_handler)
        
        # Main loop
        while self.running:
            try:
                self.run_cycle()
            except Exception as e:
                logger.exception(f"Cycle error: {e}")
            
            if max_cycles and self.cycles_completed >= max_cycles:
                logger.info(f"Max cycles ({max_cycles}) reached")
                break
            
            # Wait for next cycle
            logger.info(f"Sleeping {interval_minutes} minutes...")
            for _ in range(interval_minutes * 60):
                if not self.running:
                    break
                time.sleep(1)
        
        # Final report and memory save
        if self.scan_results:
            self.reporter.generate_daily_report(self.scan_results)
        
        # Save memory
        self.memory.save()
        logger.info(self.memory.get_memory_summary())
        
        logger.info("🛡️ SENTINEL STOPPED")


# =============================================================================
# CLI
# =============================================================================

def main():
    parser = argparse.ArgumentParser(description="SENTINEL Bug Keeper Daemon")
    parser.add_argument("--daemon", action="store_true", help="Run as daemon")
    parser.add_argument("--scan-once", action="store_true", help="Run one scan and exit")
    parser.add_argument("--interval", type=int, default=SCAN_INTERVAL_MINUTES, help="Scan interval in minutes")
    parser.add_argument("--cycles", type=int, help="Max cycles (default: infinite)")
    parser.add_argument("--dry-run", action="store_true", help="Don't actually fix issues")
    parser.add_argument("--report", action="store_true", help="Generate report from existing data")
    
    args = parser.parse_args()
    
    sentinel = Sentinel(dry_run=args.dry_run)
    
    if args.scan_once:
        result = sentinel.run_cycle()
        print(json.dumps(result.to_dict(), indent=2))
    elif args.report:
        report = sentinel.reporter.generate_daily_report(sentinel.scan_results)
        print(f"Report generated: {report}")
    elif args.daemon:
        sentinel.run(interval_minutes=args.interval, max_cycles=args.cycles)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()
