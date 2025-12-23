@echo off
:: =============================================================================
:: GODBRAIN Redis Port Forward - Auto-Restart Loop
:: Keeps kubectl port-forward running 24/7 with automatic reconnection
:: =============================================================================

TITLE GODBRAIN Redis Tunnel (Kubernetes)
COLOR 0A

echo ===================================================
echo  GODBRAIN: Kubernetes Redis Port Forward (24/7)
echo ===================================================
echo.
echo This window must remain open for Redis connectivity.
echo Port forwarding will auto-restart on disconnect.
echo.

:loop
echo [%date% %time%] Starting kubectl port-forward...
kubectl port-forward svc/redis 16379:6379 -n godbrain

echo.
echo [%date% %time%] Connection lost. Reconnecting in 5 seconds...
timeout /t 5 /nobreak >nul
goto loop
