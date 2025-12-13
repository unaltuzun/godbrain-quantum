#!/usr/bin/env bash
# GODBRAIN CODE-21 – GENETICS STACK SETUP (ROULETTE + CHAOS + VOLTRAN Bridge)

set -e

ROOT="/mnt/c/godbrain-quantum"
VENV="$ROOT/.venv"
PYTHON_BIN="python3"

echo "🚀 GENETICS STACK SETUP..."
echo "ROOT = $ROOT"
echo

cd "$ROOT"
mkdir -p "$ROOT/genetics"
mkdir -p "$ROOT/logs"

echo "🧱 Updating system & installing redis-server..."
sudo apt-get update -y
sudo apt-get install -y python3 python3-pip python3-venv redis-server

echo "🔁 Starting redis-server..."
sudo systemctl enable redis-server 2>/dev/null || true
sudo systemctl restart redis-server 2>/dev/null || sudo service redis-server restart || redis-server --daemonize yes

echo "✅ Redis ping:"
redis-cli ping || echo "⚠️ Redis ping failed."

echo
echo "🐍 Checking virtualenv: $VENV"
if [ ! -d "$VENV" ]; then
  echo "📦 Creating venv..."
  $PYTHON_BIN -m venv "$VENV"
fi

source "$VENV/bin/activate"

echo
echo "📦 Installing Python packages (redis, numpy, pandas, python-dotenv, ccxt)..."
pip install --upgrade pip --quiet
pip install redis numpy pandas python-dotenv ccxt --quiet || pip install redis numpy pandas python-dotenv ccxt

echo
echo "✅ Installed packages:"
pip list | grep -E "redis|numpy|pandas|python-dotenv|ccxt" || true

echo
echo "📂 Checking lab files..."
for f in "$ROOT/genetics/roulette_lab.py" "$ROOT/genetics/chaos_lab.py" "$ROOT/genetics/voltran_bridge.py"; do
  if [ ! -f "$f" ]; then
    echo "⚠️ Missing: $f (create it before running labs)"
  else
    echo "✅ Found: $f"
  fi
done

echo
echo "🔧 Creating launcher scripts..."

cat > "$ROOT/start_roulette_lab.sh" << 'LAEOF'
#!/usr/bin/env bash
ROOT="/mnt/c/godbrain-quantum"
source "$ROOT/.venv/bin/activate"
cd "$ROOT"
LOG="$ROOT/logs/roulette_lab.log"
echo "🎰 Starting ROULETTE LAB..."
nohup python genetics/roulette_lab.py --redis-host 127.0.0.1 --redis-port 6379 >> "$LOG" 2>&1 &
echo "✅ Roulette Lab PID: $!"
LAEOF
chmod +x "$ROOT/start_roulette_lab.sh"

cat > "$ROOT/start_chaos_lab.sh" << 'LAEOF'
#!/usr/bin/env bash
ROOT="/mnt/c/godbrain-quantum"
source "$ROOT/.venv/bin/activate"
cd "$ROOT"
LOG="$ROOT/logs/chaos_lab.log"
echo "🦁 Starting CHAOS LAB..."
nohup python genetics/chaos_lab.py --redis-host 127.0.0.1 --redis-port 6379 >> "$LOG" 2>&1 &
echo "✅ Chaos Lab PID: $!"
LAEOF
chmod +x "$ROOT/start_chaos_lab.sh"

echo
echo "==================================================================="
echo "✅ GENETICS STACK READY!"
echo
echo "Start labs manually if needed:"
echo "  ./start_roulette_lab.sh"
echo "  ./start_chaos_lab.sh"
echo
echo "Redis keys used:"
echo "  godbrain:genetics:*  (Blackjack - Cloud)"
echo "  godbrain:roulette:*  (Roulette - Local)"
echo "  godbrain:chaos:*     (Chaos - Local)"
echo "==================================================================="
