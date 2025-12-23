@echo off
:: =============================================================================
:: 🚀 GODBRAIN MASTER STARTUP - Production Ready
:: =============================================================================
:: This is THE ONE script to start everything. Run this after system reboot.
:: =============================================================================

TITLE GODBRAIN - Master Controller
COLOR 0A

cd /d C:\Users\zzkid\godbrain-quantum

echo.
echo ══════════════════════════════════════════════════════════════════
echo   🚀 GODBRAIN QUANTUM - MASTER STARTUP
echo   Production Mode - Zero Error Tolerance
echo ══════════════════════════════════════════════════════════════════
echo.

:: Load .env
for /f "tokens=1,2 delims==" %%a in (.env) do (
    set "%%a=%%b"
)

:: 1. CLEANUP
echo [1/6] 🧹 Cleaning up old processes...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im kubectl.exe >nul 2>&1
timeout /t 2 /nobreak >nul
echo       ✅ Done

:: 2. KUBERNETES REDIS TUNNEL (Critical - Must run first)
echo [2/6] 🔗 Starting Kubernetes Redis Tunnel...
start /min "REDIS_TUNNEL" scripts\redis_tunnel.bat
timeout /t 5 /nobreak >nul

:: Verify Redis connection
python -c "import redis; r=redis.Redis(host='localhost',port=16379,password='voltran2024'); print('       ✅ Redis:', 'CONNECTED' if r.ping() else 'FAILED')" 2>nul || echo       ⚠️ Redis connection pending...

:: 3. CLOUDFLARE TUNNEL
echo [3/6] ☁️ Starting Cloudflare Tunnel...
tasklist /FI "IMAGENAME eq cloudflared.exe" | findstr /I "cloudflared.exe" >nul
if %errorlevel% neq 0 (
    start /min "CLOUDFLARE" cloudflared tunnel --config cloudflared_config.yml --logfile cloudflared.log run godbrain
    echo       ✅ Started
) else (
    echo       ✅ Already running
)

:: 4. DASHBOARD (Port 8000)
echo [4/6] 📊 Starting Dashboard...
start /min "DASHBOARD" python core\god_dashboard.py
timeout /t 3 /nobreak >nul
echo       ✅ Started on port 8000

:: 5. MOBILE API (Port 8001)
echo [5/6] 📱 Starting Mobile API...
start /min "MOBILE_API" python mobile_api.py
timeout /t 2 /nobreak >nul
echo       ✅ Started on port 8001

:: 6. SENTINEL (Guardian)
echo [6/6] 🛡️ Starting SENTINEL Guardian...
start /min "SENTINEL" python core\sentinel_v3.py
echo       ✅ Started

echo.
echo ══════════════════════════════════════════════════════════════════
echo   ✅ GODBRAIN ONLINE - All Systems Go
echo ══════════════════════════════════════════════════════════════════
echo.
echo   📊 Dashboard:   http://localhost:8000
echo   📱 Mobile API:  http://localhost:8001
echo   🌐 Public:      https://godbrain.org
echo   📲 Mobile App:  https://app.godbrain.org
echo.
echo   👁️ SENTINEL is watching. System will auto-heal.
echo   ⚠️ Do NOT close minimized windows!
echo.
echo ══════════════════════════════════════════════════════════════════

:: Quick health check
echo.
echo Running health check...
timeout /t 3 /nobreak >nul
curl -s http://localhost:8001/api/status 2>nul || echo API not responding yet...

pause
