# ==============================================================================
# GODBRAIN QUANTUM - VM Deployment Script
# ==============================================================================
# Bu script'i PowerShell'de çalıştırın: .\deploy-vm.ps1
# ==============================================================================

$PROJECT_ID = "project-9ad1ce66-06b2-4a7f-bad"
$VM_NAME = "godbrain21"
$ZONE = "europe-west1-b"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "GODBRAIN QUANTUM - VM Deployment" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Dosyaları kopyala
Write-Host "[1] Dosyalar VM'ye kopyalanıyor..." -ForegroundColor Yellow
gcloud compute scp docker-compose.yml $VM_NAME`:/home/zzkid/godbrain-quantum/ --zone=$ZONE --project=$PROJECT_ID
gcloud compute scp Dockerfile Dockerfile.market-feed requirements.txt $VM_NAME`:/home/zzkid/godbrain-quantum/ --zone=$ZONE --project=$PROJECT_ID
gcloud compute scp core/god_dashboard.py market_feed.py $VM_NAME`:/home/zzkid/godbrain-quantum/ --zone=$ZONE --project=$PROJECT_ID
Write-Host "✓ Dosyalar kopyalandı" -ForegroundColor Green
Write-Host ""

# 2. .env dosyasını güncelle
Write-Host "[2] .env dosyası güncelleniyor..." -ForegroundColor Yellow
$envContent = @"
ENV=PRODUCTION
HOST=0.0.0.0
PORT=8000
ANTHROPIC_API_KEY=sk-ant-api03-tJhQHJe5qFk2oi5f2RkoJRikkcNEjOWj6S9tPYgvF26f87LcCCcIJAX-Sz_1kFpKBJkya5M9u
REDIS_HOST=redis
REDIS_PORT=6379
REDIS_PASS=voltran2024
SERAPH_MODEL=claude-sonnet-4-5-20250929
"@
$envContent | Out-File -FilePath temp_env.txt -Encoding utf8
gcloud compute scp temp_env.txt $VM_NAME`:/home/zzkid/godbrain-quantum/.env --zone=$ZONE --project=$PROJECT_ID
Remove-Item temp_env.txt
Write-Host "✓ .env dosyası güncellendi" -ForegroundColor Green
Write-Host ""

# 3. Eski container'ları durdur
Write-Host "[3] Eski container'lar durduruluyor..." -ForegroundColor Yellow
gcloud compute ssh $VM_NAME --zone=$ZONE --project=$PROJECT_ID --command="cd ~/godbrain-quantum && docker-compose down" 2>&1 | Out-Null
Write-Host "✓ Eski container'lar durduruldu" -ForegroundColor Green
Write-Host ""

# 4. Yeni image'ları build et
Write-Host "[4] Docker image'ları build ediliyor (bu biraz zaman alabilir)..." -ForegroundColor Yellow
gcloud compute ssh $VM_NAME --zone=$ZONE --project=$PROJECT_ID --command="cd ~/godbrain-quantum && docker-compose build" 2>&1
Write-Host "✓ Image'lar build edildi" -ForegroundColor Green
Write-Host ""

# 5. Container'ları başlat
Write-Host "[5] Container'lar başlatılıyor..." -ForegroundColor Yellow
gcloud compute ssh $VM_NAME --zone=$ZONE --project=$PROJECT_ID --command="cd ~/godbrain-quantum && docker-compose up -d" 2>&1
Write-Host "✓ Container'lar başlatıldı" -ForegroundColor Green
Write-Host ""

# 6. Durum kontrolü
Write-Host "[6] Container durumu kontrol ediliyor..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
gcloud compute ssh $VM_NAME --zone=$ZONE --project=$PROJECT_ID --command="cd ~/godbrain-quantum && docker-compose ps" 2>&1
Write-Host ""

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Deployment Tamamlandı!" -ForegroundColor Green
Write-Host "Dashboard URL: http://34.140.113.224:8000" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan

