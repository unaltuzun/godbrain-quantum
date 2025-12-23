@echo off
TITLE GODBRAIN QUANTUM LAUNCHER
COLOR 0A

echo ===========================================
echo  GODBRAIN QUANTUM: CLOUD LINK INITIATED
echo ===========================================

:: 1. ESKI SURECLERI TEMIZLE
echo [1/4] Temizlik yapiliyor...
taskkill /f /im python.exe >nul 2>&1
taskkill /f /im ssh.exe >nul 2>&1

:: 2. VOLTRAN TUNELI (KUBERNETES PORT-FORWARD)
echo [2/4] Baglanti Kanallari Aciliyor...
:: Cloudflare Tunnel Check
tasklist /FI "IMAGENAME eq cloudflared.exe" | findstr /I "cloudflared.exe" >nul
if %errorlevel% neq 0 (
    echo >> Starting Cloudflare Tunnel...
    start /min "CLOUDFLARE" cloudflared tunnel --config cloudflared_config.yml --logfile cloudflared.log run godbrain
)

:: Kubernetes Redis Port Forward (replaces old SSH tunnel)
echo >> Starting Kubernetes Redis Tunnel...
tasklist /FI "WINDOWTITLE eq GODBRAIN Redis Tunnel*" | findstr /I "cmd.exe" >nul
if %errorlevel% neq 0 (
    start /min "REDIS_TUNNEL" scripts\redis_tunnel.bat
)

:: 3. MARKET FEEDER (OKX)
echo [3/4] Piyasa Verisi Baglaniyor...
start /min "FEEDER" python core\market_feed.py

:: 4. DASHBOARD (CLOUD BRAIN)
echo [4/4] Godbrain Dashboard Aciliyor...
timeout /t 3 >nul
start "DASHBOARD" python core\god_dashboard.py

echo.
echo >> SISTEM ONLINE. TARAYICI ACILIYOR...
echo >> Bu pencereyi kapatma (Minimize et).
pause