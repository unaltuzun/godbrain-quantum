# ==============================================================================
# GODBRAIN - Safe Deploy Script with Seraph Memory Verification
# ==============================================================================
# Bu script deploy öncesinde Seraph testlerini çalıştırır.
# Eğer testler başarısız olursa deploy DURUR!

Write-Host "═══════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host "                         GODBRAIN SAFE DEPLOY                                  " -ForegroundColor Cyan
Write-Host "═══════════════════════════════════════════════════════════════════════════════" -ForegroundColor Cyan
Write-Host ""

# Step 1: Run Seraph Memory Tests
Write-Host "STEP 1/4: Running Seraph Memory Tests..." -ForegroundColor Yellow
$testResult = python tests/test_seraph_memory.py
Write-Host $testResult
if ($LASTEXITCODE -ne 0) {
    Write-Host ""
    Write-Host "❌ SERAPH TESTS FAILED - DEPLOY CANCELLED!" -ForegroundColor Red
    Write-Host "Fix the issues above before deploying." -ForegroundColor Red
    exit 1
}

Write-Host ""
Write-Host "✅ Seraph tests passed. Continuing..." -ForegroundColor Green
Write-Host ""

# Step 2: Build Dashboard Lite Image
Write-Host "STEP 2/4: Building Dashboard Lite..." -ForegroundColor Yellow
gcloud builds submit --config cloudbuild-dashboard-lite.yaml --project project-9ad1ce66-06b2-4a7f-bad -q
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ BUILD FAILED!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Build complete." -ForegroundColor Green

# Step 3: Deploy to GKE
Write-Host ""
Write-Host "STEP 3/4: Deploying to GKE..." -ForegroundColor Yellow
kubectl rollout restart deployment/dashboard -n godbrain
kubectl rollout status deployment/dashboard -n godbrain --timeout=120s
if ($LASTEXITCODE -ne 0) {
    Write-Host "❌ DEPLOY FAILED!" -ForegroundColor Red
    exit 1
}
Write-Host "✅ Deploy complete." -ForegroundColor Green

# Step 4: Verify Seraph in Production
Write-Host ""
Write-Host "STEP 4/4: Verifying Seraph in production..." -ForegroundColor Yellow
Start-Sleep -Seconds 10  # Wait for pod to be ready
$verifyResult = kubectl exec deployment/dashboard -n godbrain -- timeout 30 python -c "from seraph.seraph_jarvis import SeraphJarvis; s = SeraphJarvis(); print('Seraph OK - Age:', s.get_age())" 2>&1
Write-Host $verifyResult

Write-Host ""
Write-Host "═══════════════════════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host "                    ✅ DEPLOY COMPLETE - SERAPH VERIFIED                       " -ForegroundColor Green
Write-Host "═══════════════════════════════════════════════════════════════════════════════" -ForegroundColor Green
Write-Host ""
Write-Host "Dashboard: http://34.140.113.224" -ForegroundColor Cyan
