#!/bin/bash

# Check Kubernetes connectivity and cluster status

echo "🔍 Kubernetes Connectivity Check"
echo "================================"
echo ""

# Check kubectl installation
if ! command -v kubectl &> /dev/null; then
    echo "❌ kubectl is not installed"
    exit 1
fi

echo "✅ kubectl version:"
kubectl version --client
echo ""

# Check cluster connectivity
if kubectl cluster-info &> /dev/null; then
    echo "✅ Kubernetes cluster is accessible"
    kubectl cluster-info
else
    echo "❌ Cannot connect to Kubernetes cluster"
    exit 1
fi

echo ""
echo "📊 Cluster nodes:"
kubectl get nodes
echo ""

echo "📦 Namespaces:"
kubectl get namespaces
echo ""

echo "✅ All checks passed!"
