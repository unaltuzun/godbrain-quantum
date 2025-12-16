#!/usr/bin/env python3
"""
SERAPH MEMORY TEST - Run this before deploying to verify memory system works

Usage:
    python tests/test_seraph_memory.py

This test MUST pass before deploying Dashboard. If it fails, DO NOT DEPLOY.
"""

import sys
import os

# Add project root to path
sys.path.insert(0, os.path.dirname(os.path.dirname(os.path.abspath(__file__))))


def test_seraph_import():
    """Test 1: SeraphJarvis module can be imported without hanging."""
    print("Test 1: Importing SeraphJarvis...", end=" ")
    try:
        from seraph.seraph_jarvis import SeraphJarvis, get_seraph
        print("[OK] PASS")
        return True
    except Exception as e:
        print(f"[FAIL]: {e}")
        return False


def test_seraph_creation():
    """Test 2: SeraphJarvis instance can be created quickly."""
    print("Test 2: Creating SeraphJarvis instance...", end=" ")
    try:
        from seraph.seraph_jarvis import SeraphJarvis
        import time
        start = time.time()
        seraph = SeraphJarvis()
        elapsed = time.time() - start
        
        if elapsed > 5.0:  # Should be instant due to lazy loading
            print(f"[FAIL]: Took {elapsed:.2f}s (too slow, max 5s)")
            return False
        
        print(f"[OK] PASS ({elapsed:.2f}s)")
        return True
    except Exception as e:
        print(f"[FAIL]: {e}")
        return False


def test_seraph_age():
    """Test 3: Seraph knows its birth date."""
    print("Test 3: Checking Seraph age...", end=" ")
    try:
        from seraph.seraph_jarvis import SeraphJarvis
        seraph = SeraphJarvis()
        age = seraph.get_age()
        
        # Check for Turkish or English age format
        if age and len(age) > 0:
            print(f"[OK] PASS ({age})")
            return True
        else:
            print(f"[FAIL]: Empty age returned")
            return False
    except Exception as e:
        print(f"[FAIL]: {e}")
        return False


def test_memory_module():
    """Test 4: Long-term memory module loads correctly."""
    print("Test 4: Loading long-term memory...", end=" ")
    try:
        from seraph.long_term_memory import get_long_term_memory
        memory = get_long_term_memory()
        
        if memory is not None:
            print("[OK] PASS")
            return True
        else:
            print("[FAIL]: Memory is None")
            return False
    except Exception as e:
        print(f"[FAIL]: {e}")
        return False


def test_memory_stats():
    """Test 5: Memory stats can be retrieved (lazy load test)."""
    print("Test 5: Getting memory stats...", end=" ")
    try:
        from seraph.seraph_jarvis import SeraphJarvis
        seraph = SeraphJarvis()
        stats = seraph.get_memory_stats()
        
        if isinstance(stats, dict):
            print(f"[OK] PASS (keys: {list(stats.keys())})")
            return True
        else:
            print(f"[FAIL]: Invalid stats type: {type(stats)}")
            return False
    except Exception as e:
        print(f"[FAIL]: {e}")
        return False


def test_system_awareness():
    """Test 6: System awareness module loads correctly."""
    print("Test 6: Loading system awareness...", end=" ")
    try:
        from seraph.system_awareness import SystemAwareness
        awareness = SystemAwareness()
        print("[OK] PASS")
        return True
    except Exception as e:
        print(f"[FAIL]: {e}")
        return False


def test_codebase_rag():
    """Test 7: Codebase RAG module loads correctly."""
    print("Test 7: Loading codebase RAG...", end=" ")
    try:
        from seraph.codebase_rag import CodebaseRAG
        # Don't instantiate (slow), just import
        print("[OK] PASS")
        return True
    except Exception as e:
        print(f"[FAIL]: {e}")
        return False


def main():
    """Run all Seraph memory tests."""
    print()
    print("=" * 60)
    print("SERAPH MEMORY VERIFICATION TESTS")
    print("Run this before deploying to prevent memory breakage!")
    print("=" * 60)
    print()
    
    tests = [
        test_seraph_import,
        test_seraph_creation,
        test_seraph_age,
        test_memory_module,
        test_memory_stats,
        test_system_awareness,
        test_codebase_rag,
    ]
    
    results = []
    for test in tests:
        try:
            result = test()
            results.append(result)
        except Exception as e:
            print(f"[CRASH]: {e}")
            results.append(False)
    
    print()
    print("=" * 60)
    passed = sum(results)
    total = len(results)
    
    if passed == total:
        print(f"[OK] ALL TESTS PASSED ({passed}/{total})")
        print("Safe to deploy!")
        print("=" * 60)
        return 0
    else:
        print(f"[FAIL] SOME TESTS FAILED ({passed}/{total})")
        print("DO NOT DEPLOY until all tests pass!")
        print("=" * 60)
        return 1


if __name__ == "__main__":
    sys.exit(main())
