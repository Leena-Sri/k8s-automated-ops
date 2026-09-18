# Demo failure script for Kubernetes Automated Operations Lab (PowerShell)

$ErrorActionPreference = "Stop"

$NAMESPACE = "k8s-ops-demo"
$DEPLOYMENT = "demo-app"

Write-Host "🎭 Kubernetes Automated Operations Lab - Failure Demo" -ForegroundColor Cyan
Write-Host "====================================================" -ForegroundColor Cyan
Write-Host ""

# Check if deployment exists
$deploymentExists = kubectl get deployment $DEPLOYMENT -n $NAMESPACE 2>$null
if (-not $deploymentExists) {
    Write-Host "❌ Deployment $DEPLOYMENT not found in namespace $NAMESPACE" -ForegroundColor Red
    Write-Host "Please run setup.ps1 first" -ForegroundColor Yellow
    exit 1
}

Write-Host "📊 Step 1: Check initial workload status" -ForegroundColor Yellow
Write-Host "----------------------------------------" -ForegroundColor Yellow
kubectl get deployment $DEPLOYMENT -n $NAMESPACE
kubectl get pods -n $NAMESPACE -l app=demo-app
Write-Host ""

Write-Host "🔍 Step 2: Run health check" -ForegroundColor Yellow
Write-Host "----------------------------" -ForegroundColor Yellow
k8s-ops monitor --namespace $NAMESPACE
Write-Host ""

Write-Host "🔧 Step 3: Simulate failure by setting replicas to 0" -ForegroundColor Yellow
Write-Host "------------------------------------------------------" -ForegroundColor Yellow
kubectl scale deployment $DEPLOYMENT --replicas=0 -n $NAMESPACE
Write-Host "✅ Scaled deployment to 0 replicas" -ForegroundColor Green
Write-Host ""

Write-Host "⏳ Step 4: Wait for pods to terminate" -ForegroundColor Yellow
Write-Host "-------------------------------------" -ForegroundColor Yellow
try {
    kubectl wait --for=delete pods -l app=demo-app -n $NAMESPACE --timeout=30s
} catch {
    Write-Host "Pods terminated (or timeout reached)" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "📊 Step 5: Check workload status after failure" -ForegroundColor Yellow
Write-Host "-----------------------------------------------" -ForegroundColor Yellow
kubectl get deployment $DEPLOYMENT -n $NAMESPACE
kubectl get pods -n $NAMESPACE -l app=demo-app
Write-Host ""

Write-Host "🔍 Step 6: Run health check (should detect unhealthy)" -ForegroundColor Yellow
Write-Host "------------------------------------------------------" -ForegroundColor Yellow
try {
    k8s-ops monitor --namespace $NAMESPACE
} catch {
    Write-Host "Health check detected unhealthy workloads (expected)" -ForegroundColor Yellow
}
Write-Host ""

Write-Host "🔧 Step 7: Test dry-run remediation" -ForegroundColor Yellow
Write-Host "-----------------------------------" -ForegroundColor Yellow
k8s-ops remediate $DEPLOYMENT --namespace $NAMESPACE --dry-run
Write-Host ""

Write-Host "🔧 Step 8: Execute actual remediation" -ForegroundColor Yellow
Write-Host "--------------------------------------" -ForegroundColor Yellow
k8s-ops remediate $DEPLOYMENT --namespace $NAMESPACE --no-dry-run --verify
Write-Host ""

Write-Host "⏳ Step 9: Wait for recovery" -ForegroundColor Yellow
Write-Host "----------------------------" -ForegroundColor Yellow
kubectl wait --for=condition=available --timeout=60s deployment/$DEPLOYMENT -n $NAMESPACE
Write-Host ""

Write-Host "📊 Step 10: Verify final workload status" -ForegroundColor Yellow
Write-Host "-----------------------------------------" -ForegroundColor Yellow
kubectl get deployment $DEPLOYMENT -n $NAMESPACE
kubectl get pods -n $NAMESPACE -l app=demo-app
Write-Host ""

Write-Host "🔍 Step 11: Final health check" -ForegroundColor Yellow
Write-Host "------------------------------" -ForegroundColor Yellow
k8s-ops monitor --namespace $NAMESPACE
Write-Host ""

Write-Host "✅ Demo complete!" -ForegroundColor Green
Write-Host ""
Write-Host "The demo demonstrated:" -ForegroundColor Cyan
Write-Host "  ✓ Healthy pod detection" -ForegroundColor White
Write-Host "  ✓ Failure simulation (scaling to 0)" -ForegroundColor White
Write-Host "  ✓ Problem detection by k8s-ops" -ForegroundColor White
Write-Host "  ✓ Dry-run remediation planning" -ForegroundColor White
Write-Host "  ✓ Actual remediation execution" -ForegroundColor White
Write-Host "  ✓ Health verification after recovery" -ForegroundColor White
