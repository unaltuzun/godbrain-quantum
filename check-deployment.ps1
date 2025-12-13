# ==============================================================================
# GODBRAIN QUANTUM - Deployment Kontrol Script
# ==============================================================================
# Bu script'i PowerShell'de çalıştırın: .\check-deployment.ps1
# ==============================================================================

$PROJECT_ID = "project-9ad1ce66-06b2-4a7f-bad"
$VM_NAME = "godbrain21"
$ZONE = "europe-west1-b"
$VM_IP = "34.140.113.224"

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "GODBRAIN QUANTUM - Deployment Kontrol" -ForegroundColor Cyan
Write-Host "==========================================" -ForegroundColor Cyan
Write-Host ""

# 1. Container durumu
Write-Host "[1] Container Durumu Kontrol Ediliyor..." -ForegroundColor Yellow
gcloud compute ssh $VM_NAME --zone=$ZONE --project=$PROJECT_ID --command="cd ~/godbrain-quantum && docker-compose ps" 2>&1
Write-Host ""

# 2. Dashboard logları
Write-Host "[2] Dashboard Logları (Son 20 satır)..." -ForegroundColor Yellow
gcloud compute ssh $VM_NAME --zone=$ZONE --project=$PROJECT_ID --command="cd ~/godbrain-quantum && docker-compose logs --tail=20 dashboard" 2>&1
Write-Host ""

# 3. Market Feed logları
Write-Host "[3] Market Feed Logları (Son 10 satır)..." -ForegroundColor Yellow
gcloud compute ssh $VM_NAME --zone=$ZONE --project=$PROJECT_ID --command="cd ~/godbrain-quantum && docker-compose logs --tail=10 market-feed" 2>&1
Write-Host ""

# 4. Dashboard erişim bilgisi
Write-Host "[4] Dashboard Erişim Bilgisi" -ForegroundColor Green
Write-Host "Dashboard URL: http://$VM_IP:8000" -ForegroundColor Green
Write-Host "Tarayıcınızda açın: http://$VM_IP:8000" -ForegroundColor Green
Write-Host ""

# 5. Container'ları yeniden başlatma komutu
Write-Host "[5] Container'ları Yeniden Başlatmak İçin:" -ForegroundColor Yellow
Write-Host "gcloud compute ssh $VM_NAME --zone=$ZONE --project=$PROJECT_ID --command=`"cd ~/godbrain-quantum && docker-compose restart`"" -ForegroundColor White
Write-Host ""

# 6. Canlı log takibi
Write-Host "[6] Canlı Log Takibi İçin:" -ForegroundColor Yellow
Write-Host "gcloud compute ssh $VM_NAME --zone=$ZONE --project=$PROJECT_ID --command=`"cd ~/godbrain-quantum && docker-compose logs -f`"" -ForegroundColor White
Write-Host ""

Write-Host "==========================================" -ForegroundColor Cyan
Write-Host "Kontrol Tamamlandı!" -ForegroundColor Green
Write-Host "==========================================" -ForegroundColor Cyan

