#!/bin/bash
# ==============================================================================
# GODBRAIN QUANTUM - VM Deployment Script
# ==============================================================================
# Deploys to existing VM instance (godbrain21) using Docker Compose
# ==============================================================================

set -e

VM_NAME="godbrain21"
VM_ZONE="europe-west1-b"
VM_IP="34.140.113.224"
PROJECT_ID="project-9ad1ce66-06b2-4a7f-bad"

echo "=========================================="
echo "GODBRAIN QUANTUM - VM Deployment"
echo "=========================================="
echo "VM: ${VM_NAME} (${VM_IP})"
echo "Zone: ${VM_ZONE}"
echo ""

# Copy files to VM
echo "[1/5] Copying files to VM..."
gcloud compute scp \
    docker-compose.yml \
    Dockerfile \
    Dockerfile.market-feed \
    requirements.txt \
    core/god_dashboard.py \
    market_feed.py \
    ${VM_NAME}:~/godbrain-quantum/ \
    --zone=${VM_ZONE} \
    --project=${PROJECT_ID} \
    --recurse

# Copy .env file (if exists)
if [ -f .env ]; then
    echo "[2/5] Copying .env file to VM..."
    gcloud compute scp \
        .env \
        ${VM_NAME}:~/godbrain-quantum/.env \
        --zone=${VM_ZONE} \
        --project=${PROJECT_ID}
else
    echo "[2/5] WARNING: .env file not found. You'll need to create it on VM."
fi

# SSH into VM and deploy
echo "[3/5] Connecting to VM and deploying..."
gcloud compute ssh ${VM_NAME} \
    --zone=${VM_ZONE} \
    --project=${PROJECT_ID} \
    --command="
        cd ~/godbrain-quantum && \
        echo '[4/5] Installing Docker and Docker Compose...' && \
        sudo apt-get update -qq && \
        sudo apt-get install -y docker.io docker-compose-plugin -qq && \
        sudo usermod -aG docker \$USER && \
        echo '[5/5] Starting services with Docker Compose...' && \
        sudo docker compose down 2>/dev/null || true && \
        sudo docker compose up -d --build && \
        echo '' && \
        echo '==========================================' && \
        echo 'Deployment Complete!' && \
        echo '==========================================' && \
        sudo docker compose ps && \
        echo '' && \
        echo 'Dashboard URL: http://${VM_IP}:8000' && \
        echo 'To view logs: sudo docker compose logs -f'
    "

echo ""
echo "=========================================="
echo "Deployment Complete!"
echo "=========================================="
echo "Dashboard: http://${VM_IP}:8000"
echo ""
echo "To SSH into VM:"
echo "  gcloud compute ssh ${VM_NAME} --zone=${VM_ZONE} --project=${PROJECT_ID}"
echo ""
echo "To view logs:"
echo "  gcloud compute ssh ${VM_NAME} --zone=${VM_ZONE} --project=${PROJECT_ID} --command='cd ~/godbrain-quantum && sudo docker compose logs -f'"

