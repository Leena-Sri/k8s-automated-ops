#!/bin/bash

# Setup script for Kubernetes Automated Operations Lab

set -e

echo "🚀 Setting up Kubernetes Automated Operations Lab"

# Check if kubectl is installed
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed. Please install kubectl first."
    exit 1
fi

# Check if Python 3.12+ is installed
if ! command -v python3 &> /dev/null; then
    echo "❌ Python 3 is not installed. Please install Python 3.12+ first."
    exit 1
fi

PYTHON_VERSION=$(python3 --version | awk '{print $2}')
echo "✅ Python version: $PYTHON_VERSION"

# Check Kubernetes connectivity
echo "🔍 Checking Kubernetes connectivity..."
if kubectl cluster-info &> /dev/null; then
    echo "✅ Kubernetes cluster is accessible"
else
    echo "❌ Cannot connect to Kubernetes cluster. Please check your kubeconfig."
    exit 1
fi

# Create namespace
echo "📦 Creating k8s-ops-demo namespace..."
kubectl apply -f ../kubernetes/namespace.yaml

# Deploy demo application
echo "🚀 Deploying demo application..."
kubectl apply -f ../kubernetes/deployment.yaml
kubectl apply -f ../kubernetes/service.yaml

# Wait for deployment to be ready
echo "⏳ Waiting for deployment to be ready..."
kubectl wait --for=condition=available --timeout=60s deployment/demo-app -n k8s-ops-demo

# Install Python dependencies
echo "📦 Installing Python dependencies..."
cd ..
pip install -e ".[dev]"

echo "✅ Setup complete!"
echo ""
echo "You can now run:"
echo "  k8s-ops workloads --namespace k8s-ops-demo"
echo "  k8s-ops monitor --namespace k8s-ops-demo"
echo "  k8s-ops remediate demo-app --namespace k8s-ops-demo --dry-run"
