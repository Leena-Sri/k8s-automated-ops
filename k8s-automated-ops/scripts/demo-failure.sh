#!/bin/bash

# Demo failure script for Kubernetes Automated Operations Lab

set -e

NAMESPACE="k8s-ops-demo"
DEPLOYMENT="demo-app"

echo "🎭 Kubernetes Automated Operations Lab - Failure Demo"
echo "===================================================="
echo ""

# Check if deployment exists
if ! kubectl get deployment $DEPLOYMENT -n $NAMESPACE &> /dev/null; then
    echo "❌ Deployment $DEPLOYMENT not found in namespace $NAMESPACE"
    echo "Please run setup.sh first"
    exit 1
fi

echo "📊 Step 1: Check initial workload status"
echo "----------------------------------------"
kubectl get deployment $DEPLOYMENT -n $NAMESPACE
kubectl get pods -n $NAMESPACE -l app=demo-app
echo ""

echo "🔍 Step 2: Run health check"
echo "----------------------------"
k8s-ops monitor --namespace $NAMESPACE
echo ""

echo "🔧 Step 3: Simulate failure by setting replicas to 0"
echo "------------------------------------------------------"
kubectl scale deployment $DEPLOYMENT --replicas=0 -n $NAMESPACE
echo "✅ Scaled deployment to 0 replicas"
echo ""

echo "⏳ Step 4: Wait for pods to terminate"
echo "-------------------------------------"
kubectl wait --for=delete pods -l app=demo-app -n $NAMESPACE --timeout=30s || true
echo ""

echo "📊 Step 5: Check workload status after failure"
echo "-----------------------------------------------"
kubectl get deployment $DEPLOYMENT -n $NAMESPACE
kubectl get pods -n $NAMESPACE -l app=demo-app
echo ""

echo "🔍 Step 6: Run health check (should detect unhealthy)"
echo "------------------------------------------------------"
k8s-ops monitor --namespace $NAMESPACE || true
echo ""

echo "🔧 Step 7: Test dry-run remediation"
echo "-----------------------------------"
k8s-ops remediate $DEPLOYMENT --namespace $NAMESPACE --dry-run
echo ""

echo "🔧 Step 8: Execute actual remediation"
echo "--------------------------------------"
k8s-ops remediate $DEPLOYMENT --namespace $NAMESPACE --no-dry-run --verify
echo ""

echo "⏳ Step 9: Wait for recovery"
echo "----------------------------"
kubectl wait --for=condition=available --timeout=60s deployment/$DEPLOYMENT -n $NAMESPACE
echo ""

echo "📊 Step 10: Verify final workload status"
echo "-----------------------------------------"
kubectl get deployment $DEPLOYMENT -n $NAMESPACE
kubectl get pods -n $NAMESPACE -l app=demo-app
echo ""

echo "🔍 Step 11: Final health check"
echo "------------------------------"
k8s-ops monitor --namespace $NAMESPACE
echo ""

echo "✅ Demo complete!"
echo ""
echo "The demo demonstrated:"
echo "  ✓ Healthy pod detection"
echo "  ✓ Failure simulation (scaling to 0)"
echo "  ✓ Problem detection by k8s-ops"
echo "  ✓ Dry-run remediation planning"
echo "  ✓ Actual remediation execution"
echo "  ✓ Health verification after recovery"
