@echo off
:: =============================================================================
:: GODBRAIN Startup Script - Run all services for 24/7 operation
:: Add this to Windows Task Scheduler to run at startup
:: =============================================================================

TITLE GODBRAIN Quantum Launcher
COLOR 0A

cd /d C:\Users\zzkid\godbrain-quantum

echo ==================================================
echo  GODBRAIN QUANTUM: Full System Startup
echo ==================================================

:: 1. Check and start Cloudflare Tunnel
echo [1/5] Checking Cloudflare Tunnel...
tasklist /FI "IMAGENAME eq cloudflared.exe" | findstr /I "cloudflared.exe" >nul
if %errorlevel% equ 0 (
    echo [SKIP] Cloudflare Tunnel already running.
) else (
    echo [START] Starting Cloudflare Tunnel...
    start /min "CLOUDFLARED" cloudflared tunnel --config cloudflared_config.yml --logfile cloudflared.log run godbrain
)

:: 2. Start Redis Tunnel (Kubernetes Port Forward with auto-restart)
echo [2/5] Starting Redis Tunnel (Kubernetes)...
start /min "REDIS_TUNNEL" scripts\redis_tunnel.bat
timeout /t 3 /nobreak >nul

:: 3. Start Market Feed
echo [3/5] Starting Market Feed...
start /min "MARKET_FEED" python core\market_feed.py

:: 4. Start Mobile API (Port 8001)
echo [4/5] Starting Mobile API...
start /min "MOBILE_API" python mobile_api.py

:: 5. Start Mobile App (Next.js)
echo [5/5] Starting Mobile App (Next.js)...
cd mobile-app
start /min "MOBILE_APP" pnpm dev
cd ..

echo.
echo ==================================================
echo  GODBRAIN services started successfully!
echo  - Cloudflare Tunnel: godbrain.org
echo  - Redis Tunnel: localhost:16379
echo  - Mobile API: http://localhost:8001
echo  - Mobile App: http://localhost:3000
echo ==================================================
echo.
echo NOTE: Keep Redis Tunnel window open for 24/7 operation.
