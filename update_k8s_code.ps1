# GODBRAIN K8S CODE SYNC
# Updates the ConfigMaps with the latest modular code

Write-Host "🔄 Updating voltran-agg-code ConfigMap..." -ForegroundColor Cyan

kubectl create configmap voltran-agg-code -n godbrain `
    --from-file=agg.py=agg.py `
    --from-file=config_center.py=config_center.py `
    --from-file=harvester.py=signals/harvester.py `
    --from-file=executor.py=execution/executor.py `
    --dry-run=client -o yaml | kubectl apply -f -

Write-Host "✅ ConfigMap updated. Restarting voltran deployment..." -ForegroundColor Green
kubectl rollout restart deployment voltran -n godbrain

Write-Host "🔍 Watching health..." -ForegroundColor Yellow
Start-Sleep -Seconds 5
kubectl get pods -n godbrain | Select-String "voltran"
