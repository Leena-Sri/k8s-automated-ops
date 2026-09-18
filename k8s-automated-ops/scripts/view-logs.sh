#!/bin/bash

# View logs for k8s-ops-demo pods

NAMESPACE="k8s-ops-demo"

if [ -z "$1" ]; then
    echo "Usage: $0 <pod-name> [optional: follow]"
    echo ""
    echo "Available pods:"
    kubectl get pods -n $NAMESPACE
    exit 1
fi

POD_NAME=$1
FOLLOW=${2:-""}

if [ "$FOLLOW" = "follow" ]; then
    echo "📋 Following logs for pod: $POD_NAME"
    kubectl logs -f $POD_NAME -n $NAMESPACE
else
    echo "📋 Logs for pod: $POD_NAME"
    kubectl logs $POD_NAME -n $NAMESPACE
fi
