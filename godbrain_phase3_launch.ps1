# ==========================================
# GODBRAIN PHASE 3: VOLTRAN LAUNCHER
# ==========================================

$Docs = [Environment]::GetFolderPath("MyDocuments")
$Root = "$Docs\godbrain-quantum" # Klasör adını güncelledim

# Klasör yoksa oluştur
if (-not (Test-Path $Root)) { New-Item -ItemType Directory -Path $Root -Force | Out-Null }

Write-Host ">> GODBRAIN VOLTRAN Mimarisi Yükleniyor..." -ForegroundColor Cyan

# 1. TEMİZLİK (Eski simülasyonları temizle)
Stop-Process -Name "mock-cortex", "conduit-router", "python" -ErrorAction SilentlyContinue

# 2. INJECTOR (Trade Sinyal Modu)
$TradeInjector = @"
import socket
import struct
import json
import time
import sys
import random

HOST = '127.0.0.1'
PORT = 9000

def connect_with_retry(host, port):
    while True:
        try:
            s = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            s.connect((host, port))
            return s
        except:
            time.sleep(1)

def send_trade_signals():
    s = connect_with_retry(HOST, PORT)
    print(f"✅ GODBRAIN SIGNAL LINK ESTABLISHED")
    
    # Payload: HFT Emir
    header = {"msg_id": "ORDER-66", "priority": 1}
    h_bytes = json.dumps(header).encode('utf-8')
    p_bytes = b'{"pair": "BTC/USDT", "side": "BUY", "amount": 0.5}'
    
    total_len = 4 + len(h_bytes) + len(p_bytes)
    pkt = struct.pack('>I', total_len) + \
          struct.pack('>I', len(h_bytes)) + \
          h_bytes + \
          p_bytes
          
    print(f"🚀 High-Frequency Trading (HFT) Started...")
    try:
        while True:
            s.sendall(pkt)
            time.sleep(0.05) # Hızlı emir
    except:
        pass

if __name__ == "__main__":
    send_trade_signals()
"@
$TradeInjector | Out-File -Encoding UTF8 "$Root\injector.py"

# 3. BAŞLATMA (Voltran Motorları)
# Borsa 1: BINANCE (Simülasyon: Laggy/Reject) -> 11001
$Binance = Start-Process powershell -ArgumentList "-Command", "cd '$Root\mock-cortex'; `$env:PORT='11001'; `$env:MODE='reject'; cargo run" -PassThru

# Borsa 2: OKX (Simülasyon: Fast) -> 11002
$OKX = Start-Process powershell -ArgumentList "-Command", "cd '$Root\mock-cortex'; `$env:PORT='11002'; `$env:MODE='accept'; cargo run" -PassThru

Write-Host ">> EXCHANGES CONNECTED." -ForegroundColor Green
Start-Sleep -Seconds 2

# Router (Beyin)
$Router = Start-Process powershell -ArgumentList "-Command", "cd '$Root\conduit-router'; cargo run" -PassThru -RedirectStandardOutput "$Root\engine.log" -RedirectStandardError "$Root\engine_err.log"

Write-Host ">> EXECUTION ENGINE ONLINE." -ForegroundColor Green
Start-Sleep -Seconds 3

# Sinyal
Start-Process python -ArgumentList "$Root\injector.py" -NoNewWindow

# --- 4. DASHBOARD (Voltran UI) ---
$LogFile = "$Root\engine_err.log"
$BinanceHealth = 1.0
$OKXHealth = 1.0

Clear-Host
Write-Host "========================================================" -ForegroundColor Cyan
Write-Host "   GODBRAIN PHASE 3: VOLTRAN NANOCORE EXECUTION" -ForegroundColor White
Write-Host "========================================================" -ForegroundColor Cyan

while ($true) {
    if (Test-Path $LogFile) {
        $Lines = Get-Content $LogFile -Tail 10 -ErrorAction SilentlyContinue
        foreach ($Line in $Lines) {
            if ($Line -match "Node (node-bad|node-good).*Weight.*to (\d+\.\d+)") {
                $Node = $Matches[1]
                $Val = [double]$Matches[2]
                if ($Node -eq "node-bad") { $BinanceHealth = $Val }
                if ($Node -eq "node-good") { $OKXHealth = $Val }
            }
        }
    }

    $BinanceBar = "█" * [math]::Round($BinanceHealth * 30)
    $OKXBar = "█" * [math]::Round($OKXHealth * 30)

    [Console]::SetCursorPosition(0, 5)
    
    Write-Host "`n>> EXCHANGE LATENCY & HEALTH STATUS" -ForegroundColor Yellow
    Write-Host "-------------------------------------"
    
    if ($BinanceHealth -lt 0.3) {
        Write-Host "BINANCE API [FAIL] | $BinanceBar ($BinanceHealth)" -ForegroundColor Red
        Write-Host "   └── STATUS: FROZEN / REJECTING ORDERS" -ForegroundColor Red
    } else {
        Write-Host "BINANCE API [OK]   | $BinanceBar ($BinanceHealth)" -ForegroundColor Green
    }
    Write-Host ""
    Write-Host "OKX API     [FAST] | $OKXBar ($OKXHealth)" -ForegroundColor Green
    
    Write-Host "`n-------------------------------------"
    Write-Host ">> ACTIVE STRATEGY: SLIPPAGE PROTECTION V2" -ForegroundColor Cyan
    
    if ($BinanceHealth -lt 0.5) {
        Write-Host "⚠️  ALERT: VOLTRAN INTERVENTION DETECTED" -ForegroundColor Yellow
        Write-Host "   └── REROUTING ALL LIQUIDITY TO >> OKX <<" -ForegroundColor Green
        Write-Host "   └── CAPITAL PRESERVED." -ForegroundColor Green
    } else {
        Write-Host "   └── MONITORING MARKET PULSE..." -ForegroundColor Gray
    }
    Start-Sleep -Milliseconds 200
}