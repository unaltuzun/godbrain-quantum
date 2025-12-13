#!/bin/bash
cd /opt/godbrain
source .venv/bin/activate

# Kill existing
pkill -f "blackjack_lab.py" 2>/dev/null || true
pkill -f "roulette_lab.py" 2>/dev/null || true
pkill -f "chaos_lab.py" 2>/dev/null || true

sleep 1

# Start labs
nohup python genetics/blackjack_lab.py >> logs/blackjack.log 2>&1 &
echo "🦅 Blackjack Lab started: $!"

nohup python genetics/roulette_lab.py >> logs/roulette.log 2>&1 &
echo "🐺 Roulette Lab started: $!"

nohup python genetics/chaos_lab.py >> logs/chaos.log 2>&1 &
echo "🦁 Chaos Lab started: $!"

echo ""
echo "✅ All labs running!"
echo "Watch: tail -f logs/*.log"
