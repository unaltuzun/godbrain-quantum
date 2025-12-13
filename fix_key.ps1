# ==========================================
# GODBRAIN: KEY REGENERATION & CONNECT
# ==========================================
$ErrorActionPreference = "SilentlyContinue"
$KeyPath = "$env:USERPROFILE\.ssh\id_ed25519"

Write-Host ">> ANAHTAR KONTROL EDİLİYOR..." -ForegroundColor Cyan

# 1. Anahtar Yoksa/Bozuksa Yeniden Üret
if (-not (Test-Path $KeyPath)) {
    Write-Host "⚠️  Eski anahtar bulunamadı. YENİSİ ÜRETİLİYOR..." -ForegroundColor Yellow
    # Klasörü oluştur
    New-Item -ItemType Directory -Path "$env:USERPROFILE\.ssh" -Force | Out-Null
    # Anahtarı bas
    ssh-keygen -t ed25519 -f $KeyPath -N "" -C "godbrain-recovery-$(Get-Date -Format 'HHmm')"
    
    $PubKey = Get-Content "$KeyPath.pub"
    
    Write-Host ""
    Write-Host "🛑 DUR! AŞAĞIDAKİ SATIRI KOPYALA VE SUNUCUDA ÇALIŞTIR:" -ForegroundColor Red -BackgroundColor White
    Write-Host "----------------------------------------------------------------"
    Write-Host "echo `"$PubKey`" >> ~/.ssh/authorized_keys" -ForegroundColor Green
    Write-Host "----------------------------------------------------------------"
    Write-Host "Bunu sunucuda (GCP) yaptıktan sonra ENTER'a bas."
    Read-Host "Hazır olunca Enter'a bas..."
} else {
    Write-Host "✅ Anahtar bulundu. Bağlantı deneniyor..." -ForegroundColor Green
}

# 2. TÜNELİ BAŞLAT
Write-Host ">> Tünel Açılıyor (16379 -> 6379)..." -ForegroundColor Cyan
Stop-Process -Name "ssh" -Force # Temizlik

Start-Process ssh -ArgumentList "-N -L 16379:127.0.0.1:6379 -i `"$KeyPath`" -o ExitOnForwardFailure=yes -o StrictHostKeyChecking=no -o ServerAliveInterval=60 zzkidreal@34.140.113.224" -NoNewWindow

Write-Host ">> Bağlantı kuruluyor (5 sn)..."
Start-Sleep -Seconds 5

# 3. TEST
$Test = Test-NetConnection -ComputerName 127.0.0.1 -Port 16379
if ($Test.TcpTestSucceeded) {
    Write-Host "✅ BAŞARILI: TÜNEL AKTİF!" -ForegroundColor Green
    Write-Host "Voltran hattı onarıldı."
} else {
    Write-Host "❌ HATA: Bağlantı kurulamadı. Sunucuya anahtarı eklediğinden emin ol." -ForegroundColor Red
}