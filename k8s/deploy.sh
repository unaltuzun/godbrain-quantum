#!/bin/bash
# ==============================================================================
# GODBRAIN QUANTUM - Kubernetes Deployment Script
# ==============================================================================
# This script builds Docker images and deploys to GCP Kubernetes
# ==============================================================================

set -e

# Configuration
PROJECT_ID="${GCP_PROJECT_ID:-YOUR_PROJECT_ID}"
REGION="${GCP_REGION:-us-central1}"
CLUSTER_NAME="${GCP_CLUSTER_NAME:-godbrain-cluster}"
IMAGE_REGISTRY="gcr.io/${PROJECT_ID}"

echo "=========================================="
echo "GODBRAIN QUANTUM - K8s Deployment"
echo "=========================================="
echo "Project ID: ${PROJECT_ID}"
echo "Region: ${REGION}"
echo "Cluster: ${CLUSTER_NAME}"
echo ""

# Check if gcloud is installed
if ! command -v gcloud &> /dev/null; then
    echo "ERROR: gcloud CLI not found. Please install Google Cloud SDK."
    exit 1
fi

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo "ERROR: kubectl not found. Please install kubectl."
    exit 1
fi

# Authenticate with GCP
echo "[1/6] Authenticating with GCP..."
gcloud auth configure-docker

# Set project
echo "[2/6] Setting GCP project..."
gcloud config set project ${PROJECT_ID}

# Get cluster credentials
echo "[3/6] Getting cluster credentials..."
gcloud container clusters get-credentials ${CLUSTER_NAME} --region ${REGION}

# Build and push Dashboard image
echo "[4/6] Building and pushing Dashboard image..."
docker build -t ${IMAGE_REGISTRY}/godbrain-dashboard:latest -f Dockerfile .
docker push ${IMAGE_REGISTRY}/godbrain-dashboard:latest

# Build and push Market Feed image
echo "[5/6] Building and pushing Market Feed image..."
docker build -t ${IMAGE_REGISTRY}/godbrain-market-feed:latest -f Dockerfile.market-feed .
docker push ${IMAGE_REGISTRY}/godbrain-market-feed:latest

# Update deployment YAML with project ID
sed -i.bak "s/YOUR_PROJECT_ID/${PROJECT_ID}/g" k8s/godbrain-deployment.yaml

# Create secrets (if not exists)
echo "[6/6] Creating/updating Kubernetes secrets..."
if kubectl get secret godbrain-secrets &> /dev/null; then
    echo "Secret 'godbrain-secrets' already exists. Updating..."
    kubectl delete secret godbrain-secrets
fi

# Create secret from .env file (if exists) or prompt for values
if [ -f .env ]; then
    kubectl create secret generic godbrain-secrets --from-env-file=.env
    echo "Secret created from .env file"
else
    echo "WARNING: .env file not found. Creating secret manually..."
    echo "Please run: kubectl create secret generic godbrain-secrets \\"
    echo "  --from-literal=ANTHROPIC_API_KEY='your-key' \\"
    echo "  --from-literal=REDIS_PASS='your-password' \\"
    echo "  --from-literal=REDIS_HOST='redis-service' \\"
    echo "  --from-literal=REDIS_PORT='6379'"
    read -p "Press Enter to continue after creating the secret..."
fi

# Apply deployment
echo "Deploying to Kubernetes..."
kubectl apply -f k8s/godbrain-deployment.yaml

# Wait for deployment
echo "Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=300s deployment/godbrain-dashboard
kubectl wait --for=condition=available --timeout=300s deployment/godbrain-market-feed

# Get service external IP
echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo "Getting LoadBalancer external IP..."
kubectl get service godbrain-dashboard-service

echo ""
echo "Dashboard URL:"
EXTERNAL_IP=$(kubectl get service godbrain-dashboard-service -o jsonpath='{.status.loadBalancer.ingress[0].ip}')
if [ -z "$EXTERNAL_IP" ]; then
    echo "  External IP pending... Run: kubectl get service godbrain-dashboard-service"
else
    echo "  http://${EXTERNAL_IP}"
fi

echo ""
echo "To view logs:"
echo "  Dashboard: kubectl logs -f deployment/godbrain-dashboard"
echo "  Market Feed: kubectl logs -f deployment/godbrain-market-feed"

