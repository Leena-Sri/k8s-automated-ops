# Kubernetes Automated Operations Lab

A production-style Python CLI tool for Kubernetes workload discovery, health monitoring, and automated remediation.

## Problem Statement

Managing Kubernetes workloads at scale requires continuous monitoring and quick response to failures. This project demonstrates a Python-based automation tool that:
- Discovers workloads across namespaces
- Monitors pod health and availability
- Automatically remediates unhealthy workloads
- Exposes metrics for observability

## Architecture

```
             Python CLI
                 |
                 v
       Kubernetes Client
                 |
       +---------+---------+
       |                   |
       v                   v
 Workload Discovery    Health Monitor
       |                   |
       +---------+---------+
                 |
                 v
        Remediation Engine
                 |
                 v
          Kubernetes API
                 |
                 v
             Workloads

Prometheus <--- Metrics
```

## Tech Stack

- **Python 3.12+**: Core language
- **Kubernetes**: Target platform
- **Docker**: Containerization
- **Prometheus**: Metrics and monitoring
- **pytest**: Testing framework
- **Click**: CLI framework
- **Pydantic**: Data validation

## Installation

### Prerequisites

- Python 3.12 or higher
- kubectl configured to access a Kubernetes cluster
- kind or MicroK8s (for local testing)

### Setup

```bash
# Clone the repository
git clone <repository-url>
cd k8s-automated-ops

# Install dependencies
pip install -e ".[dev]"

# Or install with uv
uv pip install -e ".[dev]"
```

### Kubernetes Setup

#### Using setup script (Linux/Mac)

```bash
./scripts/setup.sh
```

#### Using setup script (Windows)

```powershell
.\scripts\setup.ps1
```

#### Manual setup

```bash
# Create namespace
kubectl apply -f kubernetes/namespace.yaml

# Deploy demo application
kubectl apply -f kubernetes/deployment.yaml
kubectl apply -f kubernetes/service.yaml

# Wait for deployment to be ready
kubectl wait --for=condition=available --timeout=60s deployment/demo-app -n k8s-ops-demo
```

## How to Run

### Workload Discovery

```bash
# Discover workloads in default namespace
k8s-ops workloads

# Discover workloads in specific namespace
k8s-ops workloads --namespace k8s-ops-demo
```

Example output:
```
NAME             READY   DESIRED   STATUS
demo-app         3/3     3         HEALTHY
```

### Health Monitoring

```bash
# One-time health check
k8s-ops monitor --namespace k8s-ops-demo

# Continuous monitoring
k8s-ops monitor --namespace k8s-ops-demo --watch --interval 30
```

Example output:
```
Health Check Report
==================================================

✓ demo-app (k8s-ops-demo)
  Status: healthy
  Replicas: 3/3
  Restarts: 0
  No issues detected
```

### Automated Remediation

```bash
# Dry-run remediation (default)
k8s-ops remediate demo-app --namespace k8s-ops-demo --dry-run

# Execute actual remediation
k8s-ops remediate demo-app --namespace k8s-ops-demo --no-dry-run

# Remediate with verification
k8s-ops remediate demo-app --namespace k8s-ops-demo --no-dry-run --verify
```

Example output:
```
[DRY RUN]
Remediation Plan for demo-app
==================================================
Namespace: k8s-ops-demo
Action: rollout_restart
Reason: Issues detected: replica_mismatch: Only 1/3 replicas ready
```

## Failure Demonstration

### Linux/Mac

```bash
./scripts/demo-failure.sh
```

### Windows

```powershell
.\scripts\demo-failure.ps1
```

The demo demonstrates:
1. Healthy pod detection
2. Failure simulation (scaling to 0 replicas)
3. Problem detection by k8s-ops
4. Dry-run remediation planning
5. Actual remediation execution
6. Health verification after recovery

## Testing

### Run all tests

```bash
# Linux/Mac
./scripts/run-tests.sh

# Windows
python -m pytest --cov=k8s_ops --cov-report=term-missing --cov-report=html -v
```

### Run specific tests

```bash
# Run discovery tests
pytest tests/test_discovery.py

# Run health tests
pytest tests/test_health.py

# Run remediation tests
pytest tests/test_remediation.py
```

### Test coverage

The project targets 80%+ test coverage with comprehensive unit tests using mocked Kubernetes API calls.

## Python Design Decisions

- **Type hints**: All functions use type hints for better IDE support and error detection
- **Dataclasses**: Used for data models to reduce boilerplate
- **Dependency injection**: Kubernetes client is injected for testability
- **Protocol-based design**: `KubernetesClientProtocol` enables easy mocking
- **Exception handling**: Custom exceptions for clear error handling
- **Logging**: Structured logging for debugging and monitoring
- **Small functions**: Each function has a single responsibility
- **Separation of concerns**: Clear boundaries between discovery, health, and remediation

## Project Structure

```
k8s-automated-ops/
│
├── k8s_ops/
│   ├── cli.py                  # Click-based CLI interface
│   ├── config.py               # Configuration management
│   ├── kubernetes_client.py    # Kubernetes client abstraction
│   ├── discovery.py            # Workload discovery logic
│   ├── health.py               # Health monitoring logic
│   ├── remediation.py          # Automated remediation engine
│   ├── metrics.py              # Prometheus metrics
│   └── exceptions.py           # Custom exceptions
│
├── tests/
│   ├── test_discovery.py       # Discovery tests
│   ├── test_health.py          # Health monitoring tests
│   └── test_remediation.py     # Remediation tests
│
├── kubernetes/
│   ├── namespace.yaml          # Demo namespace
│   ├── deployment.yaml         # Demo deployment
│   └── service.yaml            # Demo service
│
├── monitoring/
│   └── prometheus.yml          # Prometheus configuration
│
├── scripts/
│   ├── setup.sh                # Linux/Mac setup script
│   ├── setup.ps1               # Windows setup script
│   ├── demo-failure.sh         # Linux/Mac failure demo
│   ├── demo-failure.ps1        # Windows failure demo
│   ├── check-k8s.sh            # Kubernetes connectivity check
│   ├── view-logs.sh            # Log viewing script
│   ├── check-pods.sh           # Pod status check
│   ├── run-tests.sh            # Test runner
│   └── clean-demo.sh           # Cleanup script
│
├── Dockerfile                  # Docker image for CLI tool
├── pyproject.toml              # Python project configuration
├── README.md                   # This file
└── LICENSE                     # MIT License
```

## Kubernetes Concepts Demonstrated

- **Workload discovery**: Deployments, Pods, Services
- **Pod lifecycle states**: Running, Pending, CrashLoopBackOff
- **Replica management**: Scaling and availability
- **Health probes**: Readiness and liveness probes
- **Resource management**: Requests and limits
- **Rollout operations**: Restart and scale operations
- **Namespace isolation**: Multi-tenancy

## Prometheus Metrics

The tool exposes the following Prometheus metrics:

- `k8s_ops_workloads_total`: Total number of workloads discovered
- `k8s_ops_unhealthy_workloads`: Number of unhealthy workloads
- `k8s_ops_remediation_total`: Total number of remediation actions executed
- `k8s_ops_remediation_failures_total`: Total number of remediation failures
- `k8s_ops_health_check_duration_seconds`: Duration of health checks
- `k8s_ops_discovery_duration_seconds`: Duration of workload discovery

### Running Prometheus

```bash
# Start Prometheus with the provided configuration
prometheus --config.file=monitoring/prometheus.yml
```

## Reliability and Safety Decisions

- **Dry-run by default**: All remediation operations require explicit confirmation
- **Namespace isolation**: Demo operates in dedicated namespace only
- **Idempotent operations**: Remediation actions can be safely retried
- **Health verification**: Post-remediation health checks ensure recovery
- **Comprehensive logging**: All operations are logged for audit trails
- **Test coverage**: 80%+ test coverage with mocked Kubernetes API
- **Error handling**: Graceful handling of Kubernetes API failures
- **Timeout handling**: Configurable timeouts for recovery verification

## Docker Usage

### Build the Docker image

```bash
docker build -t k8s-ops:latest .
```

### Run the CLI tool in Docker

```bash
# Mount kubeconfig and run
docker run -v ~/.kube:/root/.kube k8s-ops:latest workloads --namespace k8s-ops-demo
```

## Troubleshooting

### Kubernetes Connection Issues

```bash
# Check cluster connectivity
./scripts/check-k8s.sh

# Check kubeconfig
kubectl config view

# Test cluster access
kubectl cluster-info
```

### Pod Issues

```bash
# Check pod status
./scripts/check-pods.sh

# View pod logs
./scripts/view-logs.sh <pod-name>

# Describe pod for detailed information
kubectl describe pod <pod-name> -n k8s-ops-demo
```

### Test Failures

```bash
# Run tests with verbose output
pytest -v

# Run specific test with detailed output
pytest tests/test_discovery.py::test_discover_workloads -v -s
```

## Cleanup

### Remove demo resources

```bash
# Linux/Mac
./scripts/clean-demo.sh

# Windows
.\scripts\clean-demo.ps1
```

### Manual cleanup

```bash
kubectl delete namespace k8s-ops-demo
```
