@echo off
:: GODBRAIN Startup Script - Run cloudflared tunnel
:: Add this to Windows Task Scheduler to run at startup

cd /d C:\Users\zzkid\godbrain-quantum
start /min cmd /c "cloudflared tunnel run godbrain"
start /min cmd /c "python mobile_api.py"
cd mobile-app
start /min cmd /c "pnpm dev"

echo GODBRAIN services started!
