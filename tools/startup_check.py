#!/usr/bin/env python3
"""
GODBRAIN Startup Health Check
=============================
Her şey çalışmaya başlamadan önce kritik gereksinimleri kontrol eder.

Kullanım:
    python tools/startup_check.py

Bu script şunları kontrol eder:
- Tüm gerekli environment variable'lar
- API key'lerin geçerliliği (format kontrolü)
- Redis bağlantısı (opsiyonel)
- Import'ların çalışması
"""

import os
import sys
from pathlib import Path
from typing import Dict, List, Tuple

# Add root to path
ROOT = Path(__file__).parent.parent
sys.path.insert(0, str(ROOT))

# Load .env
try:
    from dotenv import load_dotenv
    load_dotenv(ROOT / ".env")
except ImportError:
    pass


class Colors:
    RED = "\033[91m"
    GREEN = "\033[92m"
    YELLOW = "\033[93m"
    BLUE = "\033[94m"
    END = "\033[0m"


def ok(msg: str):
    print(f"  {Colors.GREEN}✓{Colors.END} {msg}")


def warn(msg: str):
    print(f"  {Colors.YELLOW}⚠{Colors.END} {msg}")


def fail(msg: str):
    print(f"  {Colors.RED}✗{Colors.END} {msg}")


def header(title: str):
    print(f"\n{Colors.BLUE}{'='*60}{Colors.END}")
    print(f"{Colors.BLUE}{title}{Colors.END}")
    print(f"{Colors.BLUE}{'='*60}{Colors.END}")


def check_env_vars() -> Tuple[int, int, int]:
    """Check required environment variables."""
    header("1. Environment Variables")
    
    critical = [
        ("OKX_API_KEY", "OKX trading"),
        ("OKX_API_SECRET", "OKX trading"),
        ("OKX_PASSWORD", "OKX trading"),
        ("ANTHROPIC_API_KEY", "Seraph AI (Claude)"),
    ]
    
    recommended = [
        ("OPENAI_API_KEY", "Multi-LLM (GPT-4)"),
        ("GEMINI_API_KEY", "Multi-LLM (Gemini)"),
        ("TELEGRAM_TOKEN", "Telegram alerts"),
        ("TELEGRAM_CHAT_ID", "Telegram alerts"),
        ("BINANCE_API_KEY", "Binance backup"),
        ("REDIS_PASS", "Redis persistence"),
    ]
    
    passed, warnings, failed = 0, 0, 0
    
    print("\n  Critical (required for operation):")
    for var, purpose in critical:
        val = os.getenv(var)
        if val and len(val) > 10:
            ok(f"{var} ({purpose})")
            passed += 1
        else:
            fail(f"{var} MISSING! ({purpose})")
            failed += 1
    
    print("\n  Recommended:")
    for var, purpose in recommended:
        val = os.getenv(var)
        if val and len(val) > 5:
            ok(f"{var} ({purpose})")
            passed += 1
        else:
            warn(f"{var} not set ({purpose})")
            warnings += 1
    
    return passed, warnings, failed


def check_api_key_format() -> Tuple[int, int]:
    """Validate API key formats."""
    header("2. API Key Format Validation")
    
    passed, failed = 0, 0
    
    # Anthropic key format: sk-ant-api03-...
    anthropic = os.getenv("ANTHROPIC_API_KEY", "")
    if anthropic.startswith("sk-ant-"):
        ok("ANTHROPIC_API_KEY format valid")
        passed += 1
    elif anthropic:
        fail("ANTHROPIC_API_KEY format invalid (should start with sk-ant-)")
        failed += 1
    
    # OKX key format: UUID
    okx = os.getenv("OKX_API_KEY", "")
    if len(okx) == 36 and okx.count("-") == 4:
        ok("OKX_API_KEY format valid (UUID)")
        passed += 1
    elif okx:
        warn("OKX_API_KEY format unusual (expected UUID)")
    
    # Telegram token format: numbers:alphanumeric
    telegram = os.getenv("TELEGRAM_TOKEN", "")
    if telegram and ":" in telegram:
        ok("TELEGRAM_TOKEN format valid")
        passed += 1
    elif telegram:
        warn("TELEGRAM_TOKEN format unusual")
    
    return passed, failed


def check_imports() -> Tuple[int, int]:
    """Test critical imports."""
    header("3. Module Imports")
    
    modules = [
        ("core.risk_manager", "RiskManager"),
        ("core.emergency_shutdown", "EmergencyShutdown"),
        ("seraph.seraph_jarvis", "SeraphJarvis"),
        ("seraph.long_term_memory", "LongTermMemory"),
        ("infrastructure.health", "HealthCheck"),
        ("infrastructure.dna_tracker", "DNATracker"),
        ("infrastructure.llm_router", "LLMRouter"),
        ("infrastructure.llm_providers", "get_provider"),
    ]
    
    passed, failed = 0, 0
    
    for module, cls in modules:
        try:
            exec(f"from {module} import {cls}")
            ok(f"{module}.{cls}")
            passed += 1
        except Exception as e:
            fail(f"{module}.{cls}: {e}")
            failed += 1
    
    return passed, failed


def check_redis() -> bool:
    """Test Redis connection."""
    header("4. Redis Connection (Optional)")
    
    try:
        import redis
        host = os.getenv("REDIS_HOST", "127.0.0.1")
        port = int(os.getenv("REDIS_PORT", "16379"))
        password = os.getenv("REDIS_PASS", None)
        
        r = redis.Redis(host=host, port=port, password=password, socket_timeout=2)
        r.ping()
        ok(f"Redis connected ({host}:{port})")
        return True
    except Exception as e:
        warn(f"Redis not available: {e}")
        return False


def check_dotenv_file() -> bool:
    """Check if .env file exists and has content."""
    header("5. Configuration Files")
    
    env_file = ROOT / ".env"
    if env_file.exists():
        content = env_file.read_text()
        lines = [l for l in content.split("\n") if l.strip() and not l.startswith("#")]
        if len(lines) >= 4:
            ok(f".env file exists ({len(lines)} keys)")
            return True
        else:
            warn(f".env file has only {len(lines)} keys")
            return False
    else:
        fail(".env file MISSING!")
        return False


def main():
    print(f"\n{Colors.BLUE}╔══════════════════════════════════════════════════════════╗{Colors.END}")
    print(f"{Colors.BLUE}║           GODBRAIN STARTUP HEALTH CHECK                   ║{Colors.END}")
    print(f"{Colors.BLUE}╚══════════════════════════════════════════════════════════╝{Colors.END}")
    
    total_passed = 0
    total_warnings = 0
    total_failed = 0
    
    # Check .env file first
    check_dotenv_file()
    
    # Environment variables
    p, w, f = check_env_vars()
    total_passed += p
    total_warnings += w
    total_failed += f
    
    # API key formats
    p, f = check_api_key_format()
    total_passed += p
    total_failed += f
    
    # Imports
    p, f = check_imports()
    total_passed += p
    total_failed += f
    
    # Redis (optional)
    check_redis()
    
    # Summary
    header("SUMMARY")
    print(f"\n  {Colors.GREEN}Passed:{Colors.END}   {total_passed}")
    print(f"  {Colors.YELLOW}Warnings:{Colors.END} {total_warnings}")
    print(f"  {Colors.RED}Failed:{Colors.END}   {total_failed}")
    
    if total_failed > 0:
        print(f"\n  {Colors.RED}⚠ SYSTEM NOT READY - {total_failed} critical issues!{Colors.END}")
        print(f"  {Colors.YELLOW}Run 'cat .env' to check your configuration.{Colors.END}")
        return 1
    elif total_warnings > 0:
        print(f"\n  {Colors.YELLOW}System ready with {total_warnings} warnings{Colors.END}")
        return 0
    else:
        print(f"\n  {Colors.GREEN}✓ SYSTEM FULLY READY{Colors.END}")
        return 0


if __name__ == "__main__":
    sys.exit(main())
