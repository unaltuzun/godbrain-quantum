#!/usr/bin/env bash
ROOT="/mnt/c/godbrain-quantum"
source "$ROOT/.venv/bin/activate"
cd "$ROOT"
LOG="$ROOT/logs/chaos_lab.log"
echo "🦁 Starting CHAOS LAB..."
nohup python genetics/chaos_lab.py --redis-host 127.0.0.1 --redis-port 6379 >> "$LOG" 2>&1 &
echo "✅ Chaos Lab PID: $!"
