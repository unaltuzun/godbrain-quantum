# GODBRAIN QUANTUM - Kubernetes Deployment Guide

## Overview

This directory contains Kubernetes manifests for deploying GODBRAIN QUANTUM to GCP Kubernetes Engine.

## Prerequisites

1. **Google Cloud Platform Account** with billing enabled
2. **GCP Project** with Kubernetes Engine API enabled
3. **gcloud CLI** installed and authenticated
4. **kubectl** installed
5. **Docker** installed (for building images)

## Quick Start

### 1. Set Environment Variables

```bash
export GCP_PROJECT_ID="your-project-id"
export GCP_REGION="us-central1"
export GCP_CLUSTER_NAME="godbrain-cluster"
```

### 2. Create GKE Cluster (if not exists)

```bash
gcloud container clusters create ${GCP_CLUSTER_NAME} \
  --region=${GCP_REGION} \
  --num-nodes=2 \
  --machine-type=e2-medium \
  --enable-autorepair \
  --enable-autoupgrade
```

### 3. Create Kubernetes Secrets

**Option A: From .env file (Recommended)**
```bash
kubectl create secret generic godbrain-secrets --from-env-file=.env
```

**Option B: Manual creation**
```bash
kubectl create secret generic godbrain-secrets \
  --from-literal=ANTHROPIC_API_KEY='your-anthropic-key' \
  --from-literal=REDIS_HOST='redis-service' \
  --from-literal=REDIS_PORT='6379' \
  --from-literal=REDIS_PASS='your-redis-password' \
  --from-literal=SERAPH_MODEL='claude-sonnet-4-5-20250929'
```

### 4. Update Deployment YAML

Edit `k8s/godbrain-deployment.yaml` and replace `YOUR_PROJECT_ID` with your actual GCP project ID:

```yaml
image: gcr.io/YOUR_PROJECT_ID/godbrain-dashboard:latest
```

### 5. Build and Deploy

**Option A: Use deployment script**
```bash
chmod +x k8s/deploy.sh
./k8s/deploy.sh
```

**Option B: Manual deployment**
```bash
# Build and push images
docker build -t gcr.io/YOUR_PROJECT_ID/godbrain-dashboard:latest -f Dockerfile .
docker build -t gcr.io/YOUR_PROJECT_ID/godbrain-market-feed:latest -f Dockerfile.market-feed .
docker push gcr.io/YOUR_PROJECT_ID/godbrain-dashboard:latest
docker push gcr.io/YOUR_PROJECT_ID/godbrain-market-feed:latest

# Deploy to Kubernetes
kubectl apply -f k8s/godbrain-deployment.yaml
```

### 6. Get External IP

```bash
kubectl get service godbrain-dashboard-service
```

Access the dashboard at: `http://EXTERNAL_IP`

## Architecture

### Components

1. **godbrain-dashboard** (Deployment)
   - Dashboard web interface (Port 8000)
   - Seraph AI integration
   - LoadBalancer service for external access

2. **godbrain-market-feed** (Deployment)
   - OKX price feed
   - Writes to Redis
   - No external service (internal only)

### Secrets

All sensitive data is stored in Kubernetes Secrets:
- `ANTHROPIC_API_KEY`: Claude API key
- `REDIS_PASS`: Redis password
- `REDIS_HOST`: Redis hostname
- `REDIS_PORT`: Redis port

## Monitoring

### View Logs

```bash
# Dashboard logs
kubectl logs -f deployment/godbrain-dashboard

# Market feed logs
kubectl logs -f deployment/godbrain-market-feed
```

### Check Pod Status

```bash
kubectl get pods -l app=godbrain
```

### Check Services

```bash
kubectl get services -l app=godbrain
```

## Scaling

### Scale Dashboard

```bash
kubectl scale deployment/godbrain-dashboard --replicas=3
```

### Scale Market Feed

```bash
kubectl scale deployment/godbrain-market-feed --replicas=2
```

## Troubleshooting

### Pods Not Starting

1. Check pod status:
   ```bash
   kubectl describe pod <pod-name>
   ```

2. Check logs:
   ```bash
   kubectl logs <pod-name>
   ```

3. Verify secrets:
   ```bash
   kubectl get secret godbrain-secrets -o yaml
   ```

### API Key Issues

If you see authentication errors:
1. Verify secret is correct:
   ```bash
   kubectl get secret godbrain-secrets -o jsonpath='{.data.ANTHROPIC_API_KEY}' | base64 -d
   ```

2. Update secret:
   ```bash
   kubectl delete secret godbrain-secrets
   kubectl create secret generic godbrain-secrets --from-env-file=.env
   ```

### Redis Connection Issues

1. Verify Redis is accessible from pods
2. Check REDIS_HOST and REDIS_PORT in secrets
3. Test Redis connection:
   ```bash
   kubectl exec -it <pod-name> -- python -c "import socket; s=socket.socket(); s.connect(('REDIS_HOST', REDIS_PORT)); print('OK')"
   ```

## Cleanup

To remove all resources:

```bash
kubectl delete -f k8s/godbrain-deployment.yaml
kubectl delete secret godbrain-secrets
```

## Notes

- The LoadBalancer service will provision an external IP (may take a few minutes)
- Health checks are configured for both deployments
- Resource limits are set to prevent resource exhaustion
- Secrets are never committed to git (use .env file locally)

