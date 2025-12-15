# ==============================================================================
# GODBRAIN QUANTUM - Windows GCP Deployment Script
# ==============================================================================
# Run this in PowerShell to deploy GODBRAIN to GCP
# ==============================================================================

Write-Host @"
╔═══════════════════════════════════════════════════════════════════════════════╗
║                    GODBRAIN QUANTUM - GCP DEPLOYMENT                          ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Green

# Get project ID
$PROJECT_ID = gcloud config get-value project
Write-Host "Project: $PROJECT_ID" -ForegroundColor Yellow

# Step 1: Build images
Write-Host "`n[1/4] Building Docker images via Cloud Build..." -ForegroundColor Yellow
gcloud builds submit --config=cloudbuild-complete.yaml .

# Step 2: Get cluster credentials  
Write-Host "`n[2/4] Getting cluster credentials..." -ForegroundColor Yellow
gcloud container clusters get-credentials godbrain-europe --zone europe-west1-b

# Step 3: Create namespace and secrets
Write-Host "`n[3/4] Setting up namespace and secrets..." -ForegroundColor Yellow
kubectl create namespace godbrain --dry-run=client -o yaml | kubectl apply -f -

# Check if secrets exist
$secretExists = kubectl get secret godbrain-secrets -n godbrain 2>$null
if (-not $secretExists) {
    Write-Host "Creating secrets..." -ForegroundColor Yellow
    
    $OKX_KEY = Read-Host "OKX API Key"
    $OKX_SECRET = Read-Host "OKX API Secret"
    $OKX_PASS = Read-Host "OKX Passphrase"
    $REDIS_PASS = Read-Host "Redis Password"
    $ANTHROPIC_KEY = Read-Host "Anthropic API Key"
    
    kubectl create secret generic godbrain-secrets `
        --namespace=godbrain `
        --from-literal=OKX_API_KEY="$OKX_KEY" `
        --from-literal=OKX_API_SECRET="$OKX_SECRET" `
        --from-literal=OKX_API_PASSPHRASE="$OKX_PASS" `
        --from-literal=REDIS_PASS="$REDIS_PASS" `
        --from-literal=ANTHROPIC_API_KEY="$ANTHROPIC_KEY"
}

# Step 4: Deploy
Write-Host "`n[4/4] Deploying to GKE..." -ForegroundColor Yellow

# Replace PROJECT_ID and apply
$manifest = Get-Content k8s/godbrain-complete.yaml -Raw
$manifest = $manifest -replace 'PROJECT_ID', $PROJECT_ID
$manifest | kubectl apply -f -
kubectl apply -f k8s/neural-trainer.yaml -n godbrain
kubectl apply -f k8s/seraph-backup.yaml -n godbrain

# Wait and show status
Write-Host "`nWaiting for pods to start..." -ForegroundColor Yellow
Start-Sleep -Seconds 30

kubectl get pods -n godbrain

Write-Host "`n`nDashboard URL:" -ForegroundColor Green
kubectl get svc dashboard -n godbrain -o jsonpath='{.status.loadBalancer.ingress[0].ip}'

Write-Host @"

╔═══════════════════════════════════════════════════════════════════════════════╗
║                    🚀 GODBRAIN IS NOW RUNNING 24/7                            ║
╚═══════════════════════════════════════════════════════════════════════════════╝
"@ -ForegroundColor Green
