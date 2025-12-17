
Write-Host "🚀 Deploying Dashboard V2 (Uncached)..." -ForegroundColor Green
$PROJECT_ID = gcloud config get-value project
Write-Host "Project: $PROJECT_ID"

# Build with unique V2 tag
$IMAGE = "us-central1-docker.pkg.dev/$PROJECT_ID/godbrain/dashboard:v2"
Write-Host "Building image: $IMAGE"

# Using current directory (.) to ensure Godbrain context
gcloud builds submit --tag $IMAGE .

# Update Kubernetes Deployment to use V2
Write-Host "Updating Kubernetes Deployment..."
kubectl set image deployment/dashboard dashboard=$IMAGE -n godbrain

Write-Host "Waiting for rollout..."
kubectl rollout status deployment/dashboard -n godbrain

Write-Host "DONE. Dashboard V2 is active." -ForegroundColor Green
