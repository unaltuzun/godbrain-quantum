#!/bin/bash
# ==============================================================================
# GODBRAIN QUANTUM - One-Click GCP Deployment
# ==============================================================================
# This script builds and deploys all GODBRAIN components to GCP.
#
# Prerequisites:
#   1. gcloud CLI installed and authenticated
#   2. kubectl installed with gke-gcloud-auth-plugin
#   3. GKE cluster running (godbrain-cluster)
#
# Usage:
#   chmod +x deploy-gcp.sh
#   ./deploy-gcp.sh
# ==============================================================================

set -e

# Colors
RED='\033[0;31m'
GREEN='\033[0;32m'
YELLOW='\033[1;33m'
NC='\033[0m'

echo -e "${GREEN}"
echo "╔═══════════════════════════════════════════════════════════════════════════════╗"
echo "║                    GODBRAIN QUANTUM - GCP DEPLOYMENT                          ║"
echo "╚═══════════════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"

# Get project ID
PROJECT_ID=$(gcloud config get-value project)
echo -e "${YELLOW}Project: ${PROJECT_ID}${NC}"

# Check cluster
echo -e "\n${YELLOW}[1/5] Checking GKE cluster...${NC}"
gcloud container clusters get-credentials godbrain-cluster --zone us-central1
kubectl get nodes

# Build images
echo -e "\n${YELLOW}[2/5] Building Docker images via Cloud Build...${NC}"
gcloud builds submit --config=cloudbuild-complete.yaml .

# Create namespace
echo -e "\n${YELLOW}[3/5] Creating namespace...${NC}"
kubectl create namespace godbrain --dry-run=client -o yaml | kubectl apply -f -

# Check for secrets
echo -e "\n${YELLOW}[4/5] Checking secrets...${NC}"
if ! kubectl get secret godbrain-secrets -n godbrain &> /dev/null; then
    echo -e "${RED}⚠️  Secrets not found!${NC}"
    echo "Please create secrets first:"
    echo "  1. Edit k8s/godbrain-secrets-template.yaml with your API keys"
    echo "  2. Run: kubectl apply -f k8s/godbrain-secrets.yaml"
    echo ""
    read -p "Do you want to create secrets now? (y/n) " -n 1 -r
    echo
    if [[ $REPLY =~ ^[Yy]$ ]]; then
        echo "Enter your secrets (they will be Base64 encoded automatically):"
        read -p "OKX API Key: " OKX_KEY
        read -p "OKX API Secret: " OKX_SECRET
        read -p "OKX Passphrase: " OKX_PASS
        read -p "Redis Password: " REDIS_PASS
        read -p "Anthropic API Key: " ANTHROPIC_KEY
        
        kubectl create secret generic godbrain-secrets \
            --namespace=godbrain \
            --from-literal=OKX_API_KEY="$OKX_KEY" \
            --from-literal=OKX_API_SECRET="$OKX_SECRET" \
            --from-literal=OKX_API_PASSPHRASE="$OKX_PASS" \
            --from-literal=REDIS_PASS="$REDIS_PASS" \
            --from-literal=ANTHROPIC_API_KEY="$ANTHROPIC_KEY"
    else
        echo "Skipping deployment. Please create secrets and run again."
        exit 1
    fi
fi

# Deploy
echo -e "\n${YELLOW}[5/5] Deploying to GKE...${NC}"

# Replace PROJECT_ID in manifest
sed "s/PROJECT_ID/${PROJECT_ID}/g" k8s/godbrain-complete.yaml | kubectl apply -f -

# Wait for deployments
echo -e "\n${YELLOW}Waiting for deployments...${NC}"
kubectl rollout status deployment/redis -n godbrain --timeout=120s
kubectl rollout status deployment/voltran -n godbrain --timeout=120s
kubectl rollout status deployment/genetics -n godbrain --timeout=120s
kubectl rollout status deployment/dashboard -n godbrain --timeout=120s
kubectl rollout status deployment/market-feed -n godbrain --timeout=120s

# Get external IP
echo -e "\n${GREEN}✅ Deployment complete!${NC}"
echo ""
echo "Dashboard URL:"
kubectl get svc dashboard -n godbrain -o jsonpath='{.status.loadBalancer.ingress[0].ip}'
echo ""
echo ""
echo "All pods:"
kubectl get pods -n godbrain

echo -e "\n${GREEN}"
echo "╔═══════════════════════════════════════════════════════════════════════════════╗"
echo "║                    🚀 GODBRAIN IS NOW RUNNING 24/7                            ║"
echo "╚═══════════════════════════════════════════════════════════════════════════════╝"
echo -e "${NC}"
