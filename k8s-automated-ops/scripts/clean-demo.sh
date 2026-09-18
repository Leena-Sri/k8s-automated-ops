#!/bin/bash

# Clean up demo resources

set -e

NAMESPACE="k8s-ops-demo"

echo "🧹 Cleaning up k8s-ops-demo resources"
echo "===================================="
echo ""

# Delete resources
echo "Deleting deployment..."
kubectl delete deployment demo-app -n $NAMESPACE --ignore-not-found=true

echo "Deleting service..."
kubectl delete service demo-app -n $NAMESPACE --ignore-not-found=true

echo "Deleting namespace..."
kubectl delete namespace $NAMESPACE --ignore-not-found=true

echo ""
echo "✅ Cleanup complete!"
