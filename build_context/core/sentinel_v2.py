#!/usr/bin/env python3
"""
🛡️ GODBRAIN SENTINEL v2.0 - Autonomous System Guardian
=======================================================
Actually watches and fixes everything automatically.

Monitors:
- Docker services health
- Redis connectivity
- Genetics lab progress
- DNA pusher status
- Feedback loop status

Auto-heals:
- Restarts crashed services
- Reconnects Redis
- Alerts on persistent failures
"""

import os
import sys
import json
import time
import docker
import redis
from datetime import datetime, timedelta
from typing import Dict, List, Optional

# Redis Config
REDIS_HOST = os.getenv("REDIS_HOST", "127.0.0.1")
REDIS_PORT = int(os.getenv("REDIS_PORT", "16379"))
REDIS_PASS = os.getenv("REDIS_PASS", "voltran2024")

# Monitoring Config
CHECK_INTERVAL = 30  # Check every 30 seconds
AUTO_RESTART = True  # Automatically restart failed services
MAX_RESTART_ATTEMPTS = 3

# Services to monitor
CRITICAL_SERVICES = [
    "godbrain-redis",
    "godbrain-voltran",
    "godbrain-genetics",
    "godbrain-dashboard",
]

SECONDARY_SERVICES = [
    "godbrain-market-feed",
    "godbrain-dna-pusher",
    "godbrain-feedback-loop",
    "godbrain-synthia",
]


class Sentinel:
    """Autonomous system guardian."""
    
    def __init__(self):
        self.redis = None
        self.restart_counts: Dict[str, int] = {}
        self.last_health: Dict[str, str] = {}
        self.issues: List[str] = []
        
    def log(self, msg: str, level: str = "INFO"):
        """Log message with timestamp."""
        timestamp = datetime.now().strftime("%H:%M:%S")
        prefix = {
            "INFO": "ℹ️",
            "OK": "✅",
            "WARN": "⚠️",
            "ERROR": "❌",
            "ACTION": "🔧"
        }.get(level, "•")
        print(f"[{timestamp}] [SENTINEL] {prefix} {msg}")
    
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
            return False
    
    def get_docker_status(self) -> Dict[str, Dict]:
        """Get status of all Docker services."""
        result = {}
        try:
            client = docker.from_env()
            containers = client.containers.list(all=True)
            
            for container in containers:
                name = container.name
                state = container.status  # e.g., 'running', 'exited'
                status_str = container.attrs.get('State', {}).get('Status', '')
                health = container.attrs.get('State', {}).get('Health', {}).get('Status', 'unknown')
                
                # Normalize health
                if health == 'healthy':
                    norm_health = 'healthy'
                elif health == 'unhealthy':
                    norm_health = 'unhealthy'
                elif health == 'starting':
                    norm_health = 'starting'
                elif state == 'running':
                    norm_health = 'running'
                elif state == 'exited':
                    norm_health = 'stopped'
                else:
                    norm_health = state
                
                result[name] = {
                    "status": f"{state} ({health})",
                    "state": state,
                    "health": norm_health
                }
        except Exception as e:
            self.log(f"Failed to get Docker status: {e}", "ERROR")
        
        return result
    
    def restart_service(self, service_name: str) -> bool:
        """Restart a Docker service."""
        try:
            # Check restart count
            count = self.restart_counts.get(service_name, 0)
            if count >= MAX_RESTART_ATTEMPTS:
                self.log(f"{service_name}: Max restart attempts reached ({MAX_RESTART_ATTEMPTS})", "WARN")
                return False
            
            self.log(f"Restarting {service_name}...", "ACTION")
            
            # Try docker restart via SDK
            client = docker.from_env()
            container = client.containers.get(service_name)
            container.restart()
            
            self.restart_counts[service_name] = count + 1
            time.sleep(5)
            
            # Verify
            status = self.get_docker_status()
            if service_name in status and status[service_name]["state"] == "running":
                self.log(f"{service_name}: Restarted successfully", "OK")
                return True
            else:
                self.log(f"{service_name}: Restart failed", "ERROR")
                return False
                
        except Exception as e:
            self.log(f"Failed to restart {service_name}: {e}", "ERROR")
            return False
    
    def check_genetics_progress(self) -> Optional[int]:
        """Check genetics lab progress."""
        if not self.redis:
            return None
        try:
            meta = self.redis.get("godbrain:genetics:best_meta")
            if meta:
                data = json.loads(meta)
                return data.get("gen", 0)
        except:
            pass
        return None
    
    def check_feedback_loop(self) -> Optional[Dict]:
        """Check feedback loop status."""
        if not self.redis:
            return None
        try:
            feedback = self.redis.get("godbrain:feedback:latest")
            if feedback:
                return json.loads(feedback)
        except:
            pass
        return None
    
    def check_dna_pusher(self) -> Optional[Dict]:
        """Check DNA pusher status."""
        if not self.redis:
            return None
        try:
            active = self.redis.get("godbrain:trading:active_dna")
            if active:
                return json.loads(active)
        except:
            pass
        return None
    
    def store_health_report(self, report: Dict) -> None:
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
            "services": {},
            "genetics": None,
            "feedback": None,
            "dna_active": None,
            "issues": [],
            "actions_taken": []
        }
        
        # 1. Check Docker services
        docker_status = self.get_docker_status()
        
        for service in CRITICAL_SERVICES + SECONDARY_SERVICES:
            if service in docker_status:
                status = docker_status[service]
                report["services"][service] = status
                
                # Auto-heal if stopped
                if status["state"] != "running" and AUTO_RESTART:
                    report["issues"].append(f"{service} is {status['state']}")
                    if self.restart_service(service):
                        report["actions_taken"].append(f"Restarted {service}")
                    
                # Track health changes
                prev_health = self.last_health.get(service)
                curr_health = status["health"]
                
                if prev_health and prev_health != curr_health:
                    if curr_health in ["healthy", "running"]:
                        self.log(f"{service}: {prev_health} → {curr_health}", "OK")
                        # Reset restart counter on recovery
                        self.restart_counts[service] = 0
                    else:
                        self.log(f"{service}: {prev_health} → {curr_health}", "WARN")
                
                self.last_health[service] = curr_health
            else:
                report["services"][service] = {"state": "not_found", "health": "missing"}
                report["issues"].append(f"{service} not found")
        
        # 2. Check genetics progress
        gen = self.check_genetics_progress()
        if gen:
            report["genetics"] = {"generation": gen}
        
        # 3. Check feedback loop
        feedback = self.check_feedback_loop()
        if feedback:
            report["feedback"] = {
                "score": feedback.get("feedback_score"),
                "time": feedback.get("timestamp")
            }
        
        # 4. Check DNA pusher
        dna = self.check_dna_pusher()
        if dna:
            report["dna_active"] = {
                "source": dna.get("source"),
                "score": dna.get("score"),
                "gen": dna.get("gen")
            }
        
        # Store report
        self.store_health_report(report)
        
        return report
    
    def print_status_summary(self, report: Dict) -> None:
        """Print nice status summary."""
        print("\n" + "═" * 60)
        print("  🛡️  SENTINEL HEALTH REPORT")
        print("═" * 60)
        
        # Services
        for service, status in report["services"].items():
            health = status.get("health", "unknown")
            icon = {
                "healthy": "✅",
                "running": "🟢",
                "starting": "⏳",
                "unhealthy": "⚠️",
                "stopped": "🔴",
                "missing": "❓"
            }.get(health, "❓")
            
            short_name = service.replace("godbrain-", "")
            print(f"  {icon} {short_name:20} {health}")
        
        print("─" * 60)
        
        # Stats
        if report.get("genetics"):
            print(f"  🧬 Genetics: Gen {report['genetics']['generation']}")
        
        if report.get("dna_active"):
            dna = report["dna_active"]
            print(f"  💉 Active DNA: {dna['source']} (score: {dna['score']})")
        
        if report.get("feedback"):
            fb = report["feedback"]
            print(f"  📊 Feedback: Score {fb['score']}")
        
        # Issues
        if report["issues"]:
            print("─" * 60)
            print("  ⚠️  Issues:")
            for issue in report["issues"]:
                print(f"     • {issue}")
        
        if report["actions_taken"]:
            print("  🔧 Actions:")
            for action in report["actions_taken"]:
                print(f"     • {action}")
        
        print("═" * 60 + "\n")
    
    def run_forever(self):
        """Run continuous monitoring."""
        self.log("SENTINEL v2.0 ONLINE")
        self.log(f"Monitoring {len(CRITICAL_SERVICES + SECONDARY_SERVICES)} services")
        self.log(f"Check interval: {CHECK_INTERVAL}s")
        self.log(f"Auto-restart: {'ON' if AUTO_RESTART else 'OFF'}")
        
        # Initial Redis connection
        if self.connect_redis():
            self.log("Redis connected", "OK")
        else:
            self.log("Redis offline - will retry", "WARN")
        
        check_count = 0
        
        while True:
            try:
                # Run health check
                report = self.run_health_check()
                check_count += 1
                
                # Print summary every 5 checks (2.5 min) or if issues
                if check_count % 5 == 0 or report["issues"]:
                    self.print_status_summary(report)
                
                # Reconnect Redis if needed
                if not self.redis or not self.redis.ping():
                    self.connect_redis()
                
            except Exception as e:
                self.log(f"Health check error: {e}", "ERROR")
            
            time.sleep(CHECK_INTERVAL)


def main():
    sentinel = Sentinel()
    sentinel.run_forever()


if __name__ == "__main__":
    main()
