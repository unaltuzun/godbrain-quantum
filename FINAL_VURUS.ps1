$Root = "C:\godbrain-quantum"
$Core = "$Root\core"
$KeyPath = "$env:USERPROFILE\.ssh\id_ed25519"

Write-Host ">> RESTARTING GODBRAIN..." -ForegroundColor Cyan
Stop-Process -Name "python", "ssh" -Force -ErrorAction SilentlyContinue

Write-Host ">> 1. TUNNEL..." -ForegroundColor Yellow
Start-Process ssh -ArgumentList "-N -L 16379:127.0.0.1:6379 -i "$KeyPath" -o StrictHostKeyChecking=no zzkidreal@34.140.113.224" -WindowStyle Hidden

Write-Host ">> 2. FEEDER..." -ForegroundColor Yellow
Start-Process python -ArgumentList "$Core\market_feed.py" -WindowStyle Hidden

Write-Host ">> 3. DASHBOARD..." -ForegroundColor Green
Start-Sleep -Seconds 2
python "$Core\god_dashboard.py"
