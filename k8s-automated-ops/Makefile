.PHONY: help install test lint format clean docker-build docker-run setup demo cleanup

help:
	@echo "Kubernetes Automated Operations Lab - Makefile"
	@echo ""
	@echo "Available targets:"
	@echo "  install     - Install Python dependencies"
	@echo "  test        - Run tests with coverage"
	@echo "  lint        - Run code quality checks"
	@echo "  format      - Format code with black and ruff"
	@echo "  clean       - Clean up build artifacts"
	@echo "  docker-build - Build Docker image"
	@echo "  docker-run  - Run CLI tool in Docker"
	@echo "  setup       - Set up Kubernetes demo environment"
	@echo "  demo        - Run failure demonstration"
	@echo "  cleanup     - Clean up Kubernetes demo resources"

install:
	pip install -e ".[dev]"

test:
	pytest --cov=k8s_ops --cov-report=term-missing --cov-report=html -v

lint:
	ruff check k8s_ops/ tests/
	mypy k8s_ops/

format:
	black k8s_ops/ tests/
	ruff check --fix k8s_ops/ tests/

clean:
	rm -rf build/
	rm -rf dist/
	rm -rf *.egg-info
	rm -rf .pytest_cache/
	rm -rf .ruff_cache/
	rm -rf .mypy_cache/
	rm -rf htmlcov/
	find . -type d -name __pycache__ -exec rm -rf {} +

docker-build:
	docker build -t k8s-ops:latest .

docker-run:
	docker run -v ~/.kube:/root/.kube k8s-ops:latest $(ARGS)

setup:
	@echo "Setting up Kubernetes demo environment..."
	@if command -v bash >/dev/null 2>&1; then ./scripts/setup.sh; else powershell -ExecutionPolicy Bypass -File ./scripts/setup.ps1; fi

demo:
	@echo "Running failure demonstration..."
	@if command -v bash >/dev/null 2>&1; then ./scripts/demo-failure.sh; else powershell -ExecutionPolicy Bypass -File ./scripts/demo-failure.ps1; fi

cleanup:
	@echo "Cleaning up Kubernetes demo resources..."
	@if command -v bash >/dev/null 2>&1; then ./scripts/clean-demo.sh; else powershell -ExecutionPolicy Bypass -File ./scripts/clean-demo.ps1; fi
