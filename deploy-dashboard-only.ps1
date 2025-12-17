
Write-Host "🚀 Deploying Dashboard Fix Only..." -ForegroundColor Green
$PROJECT_ID = gcloud config get-value project
Write-Host "Project: $PROJECT_ID"

# Build only dashboard
Write-Host "Building image..."
gcloud builds submit --tag us-central1-docker.pkg.dev/$PROJECT_ID/godbrain/dashboard:latest .

# Restart deployment
Write-Host "Restarting deployment..."
kubectl rollout restart deployment dashboard -n godbrain

Write-Host "Waiting for rollout..."
kubectl rollout status deployment/dashboard -n godbrain

Write-Host "DONE." -ForegroundColor Green
