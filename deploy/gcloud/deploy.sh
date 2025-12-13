#!/bin/bash
# GODBRAIN VOLTRAN - Google Cloud Deploy Script

PROJECT_ID="godbrain-voltran"
REGION="us-central1"
INSTANCE_NAME="voltran-evolution"

echo "🚀 Deploying GODBRAIN VOLTRAN to Google Cloud..."

# Create VM instance
gcloud compute instances create $INSTANCE_NAME \
    --project=$PROJECT_ID \
    --zone=${REGION}-a \
    --machine-type=e2-standard-4 \
    --image-family=ubuntu-2204-lts \
    --image-project=ubuntu-os-cloud \
    --boot-disk-size=50GB \
    --tags=voltran

# Setup firewall for Redis (internal only)
gcloud compute firewall-rules create allow-redis-internal \
    --project=$PROJECT_ID \
    --allow=tcp:6379 \
    --source-ranges=10.0.0.0/8 \
    --target-tags=voltran

echo "✅ VM Created. Run setup script on the instance."
