# Setup script for Kubernetes Automated Operations Lab (PowerShell)

$ErrorActionPreference = "Stop"

Write-Host "🚀 Setting up Kubernetes Automated Operations Lab" -ForegroundColor Green

# Check if kubectl is installed
if (-not (Get-Command kubectl -ErrorAction SilentlyContinue)) {
    Write-Host "❌ kubectl is not installed. Please install kubectl first." -ForegroundColor Red
    exit 1
}

# Check if Python 3.12+ is installed
if (-not (Get-Command python -ErrorAction SilentlyContinue)) {
    Write-Host "❌ Python is not installed. Please install Python 3.12+ first." -ForegroundColor Red
    exit 1
}

$pythonVersion = python --version
Write-Host "✅ Python version: $pythonVersion" -ForegroundColor Green

# Check Kubernetes connectivity
Write-Host "🔍 Checking Kubernetes connectivity..." -ForegroundColor Yellow
try {
    kubectl cluster-info > $null 2>&1
    Write-Host "✅ Kubernetes cluster is accessible" -ForegroundColor Green
} catch {
    Write-Host "❌ Cannot connect to Kubernetes cluster. Please check your kubeconfig." -ForegroundColor Red
    exit 1
}

# Create namespace
Write-Host "📦 Creating k8s-ops-demo namespace..." -ForegroundColor Yellow
kubectl apply -f ../kubernetes/namespace.yaml

# Deploy demo application
Write-Host "🚀 Deploying demo application..." -ForegroundColor Yellow
kubectl apply -f ../kubernetes/deployment.yaml
kubectl apply -f ../kubernetes/service.yaml

# Wait for deployment to be ready
Write-Host "⏳ Waiting for deployment to be ready..." -ForegroundColor Yellow
kubectl wait --for=condition=available --timeout=60s deployment/demo-app -n k8s-ops-demo

# Install Python dependencies
Write-Host "📦 Installing Python dependencies..." -ForegroundColor Yellow
cd ..
pip install -e ".[dev]"

Write-Host "✅ Setup complete!" -ForegroundColor Green
Write-Host ""
Write-Host "You can now run:" -ForegroundColor Cyan
Write-Host "  k8s-ops workloads --namespace k8s-ops-demo" -ForegroundColor White
Write-Host "  k8s-ops monitor --namespace k8s-ops-demo" -ForegroundColor White
Write-Host "  k8s-ops remediate demo-app --namespace k8s-ops-demo --dry-run" -ForegroundColor White
