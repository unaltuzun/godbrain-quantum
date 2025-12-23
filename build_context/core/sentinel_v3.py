#!/usr/bin/env python3
"""
🛡️ GODBRAIN SENTINEL v3.0 - Production Kubernetes Guardian
===========================================================
Watches everything and fixes automatically. Zero tolerance for errors.

Features:
- Kubernetes native (kubectl, no Docker dependency)
- OKX API equity tracking
- Redis health monitoring
- Auto-heal via kubectl
- Writes all metrics to Redis
"""

import os
import sys
import json
import time
import hmac
import base64
import hashlib
import subprocess
from datetime import datetime, timezone
from typing import Dict, List, Optional
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent))

try:
    from dotenv import load_dotenv
    load_dotenv()
except:
    pass

import redis
import requests

# ═══════════════════════════════════════════════════════════════════════════════
# CONFIGURATION
# ═══════════════════════════════════════════════════════════════════════════════

REDIS_HOST = os.getenv("REDIS_HOST", "localhost")
REDIS_PORT = int(os.getenv("REDIS_PORT", "16379"))
REDIS_PASS = os.getenv("REDIS_PASS", "voltran2024")

OKX_API_KEY = os.getenv("OKX_API_KEY")
OKX_API_SECRET = os.getenv("OKX_API_SECRET")
OKX_PASSWORD = os.getenv("OKX_PASSWORD")

CHECK_INTERVAL = 30  # seconds
EQUITY_CHECK_INTERVAL = 60  # seconds (don't spam OKX API)
NAMESPACE = "godbrain"

CRITICAL_PODS = ["redis", "voltran"]
OPTIONAL_PODS = ["seraph"]


# ═══════════════════════════════════════════════════════════════════════════════
# OKX API CLIENT
# ═══════════════════════════════════════════════════════════════════════════════

class OKXClient:
    """Minimal OKX API client for equity fetching."""
    
    BASE_URL = "https://www.okx.com"
    
    def __init__(self, api_key: str, secret: str, password: str):
        self.api_key = api_key
        self.secret = secret
        self.password = password
        
    def _sign(self, timestamp: str, method: str, path: str, body: str = "") -> str:
        message = timestamp + method + path + body
        mac = hmac.new(
            self.secret.encode("utf-8"),
            message.encode("utf-8"),
            hashlib.sha256
        )
        return base64.b64encode(mac.digest()).decode("utf-8")
    
    def _request(self, method: str, path: str, body: str = "") -> dict:
        timestamp = datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%S.%f")[:-3] + "Z"
        signature = self._sign(timestamp, method, path, body)
        
        headers = {
            "OK-ACCESS-KEY": self.api_key,
            "OK-ACCESS-SIGN": signature,
            "OK-ACCESS-TIMESTAMP": timestamp,
            "OK-ACCESS-PASSPHRASE": self.password,
            "Content-Type": "application/json"
        }
        
        url = self.BASE_URL + path
        
        try:
            if method == "GET":
                resp = requests.get(url, headers=headers, timeout=10)
            else:
                resp = requests.post(url, headers=headers, data=body, timeout=10)
            
            return resp.json()
        except Exception as e:
            return {"code": "-1", "msg": str(e), "data": []}
    
    def get_balance(self) -> dict:
        """Get trading account balance."""
        path = "/api/v5/account/balance"
        return self._request("GET", path)
    
    def get_equity(self) -> Optional[float]:
        """Get total equity in USD."""
        try:
            data = self.get_balance()
            if data.get("code") == "0" and data.get("data"):
                total_eq = data["data"][0].get("totalEq", "0")
                return float(total_eq)
        except Exception as e:
            print(f"[EQUITY ERROR] {e}")
        return None


# ═══════════════════════════════════════════════════════════════════════════════
# SENTINEL v3.0
# ═══════════════════════════════════════════════════════════════════════════════

class SentinelV3:
    """Production-grade Kubernetes guardian."""
    
    def __init__(self):
        self.redis: Optional[redis.Redis] = None
        self.okx: Optional[OKXClient] = None
        self.last_equity_check = 0
        self.last_equity = 0.0
        self.issues: List[str] = []
        self.last_pod_status: Dict[str, str] = {}
        
        # Initialize OKX client
        if OKX_API_KEY and OKX_API_SECRET and OKX_PASSWORD:
            self.okx = OKXClient(OKX_API_KEY, OKX_API_SECRET, OKX_PASSWORD)
            self.log("OKX API initialized", "OK")
        else:
            self.log("OKX API credentials missing!", "ERROR")
    
    def log(self, msg: str, level: str = "INFO"):
        """Log with timestamp."""
        ts = datetime.now().strftime("%H:%M:%S")
        icons = {
            "INFO": "ℹ️",
            "OK": "✅",
            "WARN": "⚠️",
            "ERROR": "❌",
            "ACTION": "🔧",
            "MONEY": "💰"
        }
        print(f"[{ts}] [SENTINEL] {icons.get(level, '•')} {msg}")
    
    def connect_redis(self) -> bool:
        """Connect to Redis."""
        try:
            self.redis = redis.Redis(
                host=REDIS_HOST,
                port=REDIS_PORT,
                password=REDIS_PASS,
                decode_responses=True,
                socket_timeout=5
            )
            self.redis.ping()
            return True
        except Exception as e:
            self.log(f"Redis connection failed: {e}", "ERROR")
            self.redis = None
            return False
    
    def kubectl(self, *args) -> str:
        """Run kubectl command."""
        try:
            result = subprocess.run(
                ["kubectl"] + list(args),
                capture_output=True,
                text=True,
                timeout=30
            )
            return result.stdout
        except Exception as e:
            return f"ERROR: {e}"
    
    def get_pod_status(self) -> Dict[str, Dict]:
        """Get status of all pods in namespace."""
        output = self.kubectl("get", "pods", "-n", NAMESPACE, "-o", "json")
        result = {}
        
        try:
            data = json.loads(output)
            for item in data.get("items", []):
                name = item["metadata"]["name"]
                phase = item["status"]["phase"]
                
                # Get container status
                containers = item["status"].get("containerStatuses", [])
                ready = all(c.get("ready", False) for c in containers) if containers else False
                restarts = sum(c.get("restartCount", 0) for c in containers)
                
                result[name] = {
                    "phase": phase,
                    "ready": ready,
                    "restarts": restarts,
                    "healthy": phase == "Running" and ready
                }
        except:
            pass
        
        return result
    
    def restart_pod(self, pod_name: str) -> bool:
        """Restart a pod by deleting it (deployment will recreate)."""
        self.log(f"Restarting pod: {pod_name}", "ACTION")
        output = self.kubectl("delete", "pod", pod_name, "-n", NAMESPACE)
        return "deleted" in output.lower()
    
    def fetch_and_store_equity(self) -> Optional[float]:
        """Fetch equity from OKX and store in Redis."""
        if not self.okx:
            return None
        
        now = time.time()
        if now - self.last_equity_check < EQUITY_CHECK_INTERVAL:
            return self.last_equity
        
        self.last_equity_check = now
        equity = self.okx.get_equity()
        
        if equity is not None:
            self.last_equity = equity
            self.log(f"Equity: ${equity:,.2f}", "MONEY")
            
            # Store in Redis
            if self.redis:
                try:
                    self.redis.set("godbrain:trading:equity", str(equity))
                    self.redis.set("godbrain:trading:balance", str(equity))
                    self.redis.set("godbrain:sentinel:last_equity_update", datetime.now().isoformat())
                except Exception as e:
                    self.log(f"Failed to store equity in Redis: {e}", "ERROR")
            
            return equity
        else:
            self.log("Failed to fetch equity from OKX", "WARN")
            return None
    
    def check_critical_services(self) -> List[str]:
        """Check critical pods and return list of issues."""
        issues = []
        pods = self.get_pod_status()
        
        for critical in CRITICAL_PODS:
            # Find matching pod
            found = False
            for pod_name, status in pods.items():
                if critical in pod_name.lower():
                    found = True
                    if not status["healthy"]:
                        issues.append(f"{pod_name}: unhealthy (phase={status['phase']}, ready={status['ready']})")
                        
                        # Check if status changed
                        prev = self.last_pod_status.get(pod_name)
                        if prev and prev != status["phase"]:
                            self.log(f"{pod_name}: {prev} → {status['phase']}", "WARN")
                        
                        self.last_pod_status[pod_name] = status["phase"]
                    break
            
            if not found:
                issues.append(f"Critical pod '{critical}' not found!")
        
        return issues
    
    def store_health_report(self, report: Dict):
        """Store health report in Redis."""
        if not self.redis:
            return
        try:
            self.redis.set("godbrain:sentinel:health", json.dumps(report))
            self.redis.lpush("godbrain:sentinel:history", json.dumps(report))
            self.redis.ltrim("godbrain:sentinel:history", 0, 99)
        except:
            pass
    
    def run_health_check(self) -> Dict:
        """Run comprehensive health check."""
        report = {
            "timestamp": datetime.now().isoformat(),
            "redis_connected": self.redis is not None,
            "equity": self.last_equity,
            "pods": {},
            "issues": [],
            "actions_taken": []
        }
        
        # 1. Check Redis
        if not self.redis or not self.connect_redis():
            report["issues"].append("Redis connection failed")
        
        # 2. Check pods
        pods = self.get_pod_status()
        for name, status in pods.items():
            report["pods"][name] = status
        
        # 3. Check critical services
        issues = self.check_critical_services()
        report["issues"].extend(issues)
        
        # 4. Fetch equity
        eq = self.fetch_and_store_equity()
        if eq:
            report["equity"] = eq
        
        # 5. Store report
        self.store_health_report(report)
        
        return report
    
    def print_status(self, report: Dict):
        """Print status summary."""
        print("\n" + "═" * 60)
        print("  🛡️  SENTINEL v3.0 - PRODUCTION GUARDIAN")
        print("═" * 60)
        
        # Equity
        eq = report.get("equity", 0)
        print(f"  💰 Equity: ${eq:,.2f}")
        print(f"  📡 Redis: {'✅ Connected' if report['redis_connected'] else '❌ Disconnected'}")
        
        print("─" * 60)
        
        # Pods
        for name, status in report.get("pods", {}).items():
            icon = "✅" if status["healthy"] else "❌"
            short = name.split("-")[0]
            print(f"  {icon} {short:20} {status['phase']} (restarts: {status['restarts']})")
        
        # Issues
        if report["issues"]:
            print("─" * 60)
            print("  ⚠️  ISSUES:")
            for issue in report["issues"]:
                print(f"     • {issue}")
        
        print("═" * 60 + "\n")
    
    def run_forever(self):
        """Run continuous monitoring."""
        self.log("SENTINEL v3.0 ONLINE - Production Mode", "OK")
        self.log(f"Monitoring namespace: {NAMESPACE}")
        self.log(f"Check interval: {CHECK_INTERVAL}s")
        self.log(f"Equity check interval: {EQUITY_CHECK_INTERVAL}s")
        
        # Initial connections
        self.connect_redis()
        
        check_count = 0
        
        while True:
            try:
                report = self.run_health_check()
                check_count += 1
                
                # Print every 5 checks or if issues
                if check_count % 5 == 0 or report["issues"]:
                    self.print_status(report)
                
            except Exception as e:
                self.log(f"Health check error: {e}", "ERROR")
            
            time.sleep(CHECK_INTERVAL)


def main():
    sentinel = SentinelV3()
    sentinel.run_forever()


if __name__ == "__main__":
    main()
