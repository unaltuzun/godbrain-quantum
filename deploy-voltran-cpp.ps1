
Write-Host "🚀 Deploying Voltran (C++ Core Activated)..." -ForegroundColor Green
$PROJECT_ID = gcloud config get-value project
Write-Host "Project: $PROJECT_ID"

# Build Voltran with C++ Core
Write-Host "Building image: us-central1-docker.pkg.dev/$PROJECT_ID/godbrain/voltran:cpp"
gcloud builds submit --config=cloudbuild-voltran.yaml .

# Update Kubernetes Deployment
$IMAGE = "us-central1-docker.pkg.dev/$PROJECT_ID/godbrain/voltran:cpp"
Write-Host "Updating Kubernetes Deployment..."
kubectl set image deployment/voltran voltran=$IMAGE -n godbrain

Write-Host "Waiting for rollout..."
kubectl rollout status deployment/voltran -n godbrain

Write-Host "DONE. Voltran C++ Core is ACTIVE." -ForegroundColor Green
