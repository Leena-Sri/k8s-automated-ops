#!/bin/bash

# Run tests for k8s-ops

set -e

echo "🧪 Running tests for k8s-ops"
echo "============================"
echo ""

cd ..

# Run tests with coverage
echo "Running pytest with coverage..."
pytest --cov=k8s_ops --cov-report=term-missing --cov-report=html -v

echo ""
echo "✅ Tests complete!"
echo ""
echo "Coverage report: htmlcov/index.html"
