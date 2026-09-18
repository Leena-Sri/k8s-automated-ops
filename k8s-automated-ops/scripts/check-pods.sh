#!/bin/bash

# Check pod status in k8s-ops-demo namespace

NAMESPACE="k8s-ops-demo"

echo "📊 Pod Status Check"
echo "=================="
echo ""

echo "Pods in namespace $NAMESPACE:"
kubectl get pods -n $NAMESPACE
echo ""

if [ -n "$1" ]; then
    POD_NAME=$1
    echo "📋 Detailed pod information for: $POD_NAME"
    kubectl describe pod $POD_NAME -n $NAMESPACE
    echo ""
    echo "📋 Events for pod: $POD_NAME"
    kubectl get events -n $NAMESPACE --field-selector involvedObject.name=$POD_NAME
fi
