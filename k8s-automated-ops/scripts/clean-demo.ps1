# Clean up demo resources (PowerShell)

$ErrorActionPreference = "Stop"

$NAMESPACE = "k8s-ops-demo"

Write-Host "🧹 Cleaning up k8s-ops-demo resources" -ForegroundColor Yellow
Write-Host "====================================" -ForegroundColor Yellow
Write-Host ""

# Delete resources
Write-Host "Deleting deployment..." -ForegroundColor Yellow
kubectl delete deployment demo-app -n $NAMESPACE --ignore-not-found=true

Write-Host "Deleting service..." -ForegroundColor Yellow
kubectl delete service demo-app -n $NAMESPACE --ignore-not-found=true

Write-Host "Deleting namespace..." -ForegroundColor Yellow
kubectl delete namespace $NAMESPACE --ignore-not-found=true

Write-Host ""
Write-Host "✅ Cleanup complete!" -ForegroundColor Green
