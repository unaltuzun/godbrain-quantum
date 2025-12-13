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

:: 2. VOLTRAN TUNELI (SSH)
echo [2/4] Voltran Tuneli Aciliyor...
:: Kendi kullanici adini dinamik alir (%USERPROFILE%)
start /min "TUNNEL" ssh -N -L 16379:127.0.0.1:6379 -i "%USERPROFILE%\.ssh\id_ed25519" -o StrictHostKeyChecking=no zzkidreal@34.140.113.224

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