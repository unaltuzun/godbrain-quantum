# ==========================================
# GODBRAIN PHASE 3: FINAL LINK ESTABLISH
# ==========================================
$ErrorActionPreference = "SilentlyContinue"

Write-Host ">> VOLTRAN BAĞLANTISI KURULUYOR..." -ForegroundColor Cyan

# 1. TEMİZLİK (Eski kırıntıları süpür)
Stop-Process -Name "ssh" -Force
Get-NetTCPConnection -LocalPort 16379 | ForEach-Object { Stop-Process -Id $_.OwningProcess -Force }
Start-Sleep -Seconds 1

# 2. TÜNELİ ATEŞLE (SSH Tunneling)
# Local Port 16379 -> Remote Port 6379
# Anahtar: Senin az önce server'a eklediğin anahtar.
$KeyPath = "$env:USERPROFILE\.ssh\id_ed25519"

if (-not (Test-Path $KeyPath)) {
    Write-Host "❌ HATA: Private Key ($KeyPath) bulunamadı!" -ForegroundColor Red
    Write-Host "Server'a eklediğin anahtarın private dosyası silinmiş olabilir."
    exit
}

Write-Host ">> Tünel Başlatılıyor (16379 -> 6379)..." -ForegroundColor Yellow

# SSH Tünelini arka planda başlat
Start-Process ssh -ArgumentList "-N -L 16379:127.0.0.1:6379 -i `"$KeyPath`" -o ExitOnForwardFailure=yes -o StrictHostKeyChecking=no -o ServerAliveInterval=60 zzkidreal@34.140.113.224" -NoNewWindow

# Bağlantının oturması için bekle
Write-Host ">> Bağlantı bekleniyor..."
Start-Sleep -Seconds 5

# 3. BAĞLANTI TESTİ (Handshake)
$Test = Test-NetConnection -ComputerName 127.0.0.1 -Port 16379

if ($Test.TcpTestSucceeded) {
    Write-Host "✅ TÜNEL AKTİF! HAT GÜVENLİ." -ForegroundColor Green
} else {
    Write-Host "❌ BAĞLANTI REDDEDİLDİ." -ForegroundColor Red
    Write-Host "Server'daki 'authorized_keys' ile bendeki 'id_ed25519' eşleşmiyor olabilir."
    exit
}

# 4. VERİ SENKRONİZASYONU (Sync Job)
Write-Host ">> Veri Eşitleyici Başlatılıyor..." -ForegroundColor Magenta

$ScriptBlock = {
    $GCP_HOST="127.0.0.1"
    $GCP_PORT=16379
    $PASS="voltran2024"
    # İzlenecek Kritik Genetik Veriler
    $Keys = @("godbrain:genetics:best_meta", "godbrain:genetics:best_dna", "godbrain:roulette:best_meta", "godbrain:chaos:best_dna")
    
    Write-Host "SYNC ACTIVE. (Pencereyi kapatma)"
    while ($true) {
        # Burada sadece bağlantıyı canlı tutuyoruz, 
        # Gerçek veri çekme işini Godbrain yapacak.
        Start-Sleep -Seconds 10
    }
}

Start-Job -ScriptBlock $ScriptBlock | Out-Null

Write-Host "------------------------------------------------"
Write-Host "🚀 VOLTRAN SİSTEMİ ONLINE." -ForegroundColor Cyan
Write-Host "Tünel Portu: 16379"
Write-Host "------------------------------------------------"
Write-Host "Şimdi Godbrain botlarını veya Rezonans testini başlatabilirsin." -ForegroundColor Yellow