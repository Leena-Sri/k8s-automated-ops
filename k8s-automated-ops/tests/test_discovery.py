"""Tests for workload discovery functionality."""

import pytest
from unittest.mock import Mock, MagicMock

from k8s_ops.discovery import WorkloadDiscovery, WorkloadInfo, PodInfo
from k8s_ops.kubernetes_client import KubernetesClientProtocol


@pytest.fixture
def mock_k8s_client():
    """Create a mock Kubernetes client."""
    client = Mock(spec=KubernetesClientProtocol)
    return client


@pytest.fixture
def discovery(mock_k8s_client):
    """Create a WorkloadDiscovery instance."""
    return WorkloadDiscovery(mock_k8s_client)


def test_discover_workloads(discovery, mock_k8s_client):
    """Test workload discovery."""
    # Mock deployment data
    mock_k8s_client.list_deployments.return_value = [
        {
            "name": "test-app",
            "namespace": "default",
            "replicas": 3,
            "ready_replicas": 3,
            "available_replicas": 3,
        }
    ]

    # Mock pod data
    mock_k8s_client.list_pods.return_value = [
        {
            "name": "test-app-123",
            "namespace": "default",
            "phase": "Running",
            "ready": True,
            "restart_count": 0,
            "node_name": "node1",
        }
    ]

    workloads = discovery.discover_workloads("default")

    assert len(workloads) == 1
    assert workloads[0].name == "test-app"
    assert workloads[0].namespace == "default"
    assert workloads[0].desired_replicas == 3
    assert workloads[0].ready_replicas == 3


def test_discover_workloads_empty(discovery, mock_k8s_client):
    """Test workload discovery with no workloads."""
    mock_k8s_client.list_deployments.return_value = []
    mock_k8s_client.list_pods.return_value = []

    workloads = discovery.discover_workloads("default")

    assert len(workloads) == 0


def test_workload_info_healthy_status(discovery, mock_k8s_client):
    """Test workload status determination for healthy workload."""
    mock_k8s_client.list_deployments.return_value = [
        {
            "name": "healthy-app",
            "namespace": "default",
            "replicas": 2,
            "ready_replicas": 2,
            "available_replicas": 2,
        }
    ]

    mock_k8s_client.list_pods.return_value = [
        {
            "name": "healthy-app-123",
            "namespace": "default",
            "phase": "Running",
            "ready": True,
            "restart_count": 0,
            "node_name": "node1",
        },
        {
            "name": "healthy-app-456",
            "namespace": "default",
            "phase": "Running",
            "ready": True,
            "restart_count": 0,
            "node_name": "node2",
        },
    ]

    workloads = discovery.discover_workloads("default")

    assert len(workloads) == 1
    assert workloads[0].status == "HEALTHY"


def test_workload_info_degraded_status(discovery, mock_k8s_client):
    """Test workload status determination for degraded workload."""
    mock_k8s_client.list_deployments.return_value = [
        {
            "name": "degraded-app",
            "namespace": "default",
            "replicas": 3,
            "ready_replicas": 2,
            "available_replicas": 2,
        }
    ]

    mock_k8s_client.list_pods.return_value = [
        {
            "name": "degraded-app-123",
            "namespace": "default",
            "phase": "Running",
            "ready": True,
            "restart_count": 0,
            "node_name": "node1",
        },
        {
            "name": "degraded-app-456",
            "namespace": "default",
            "phase": "Running",
            "ready": True,
            "restart_count": 0,
            "node_name": "node2",
        },
        {
            "name": "degraded-app-789",
            "namespace": "default",
            "phase": "Pending",
            "ready": False,
            "restart_count": 0,
            "node_name": "node3",
        },
    ]

    workloads = discovery.discover_workloads("default")

    assert len(workloads) == 1
    assert workloads[0].status == "DEGRADED"


def test_workload_info_crash_loop_back_off(discovery, mock_k8s_client):
    """Test workload status determination for CrashLoopBackOff."""
    mock_k8s_client.list_deployments.return_value = [
        {
            "name": "crashing-app",
            "namespace": "default",
            "replicas": 1,
            "ready_replicas": 0,
            "available_replicas": 0,
        }
    ]

    mock_k8s_client.list_pods.return_value = [
        {
            "name": "crashing-app-123",
            "namespace": "default",
            "phase": "CrashLoopBackOff",
            "ready": False,
            "restart_count": 10,
            "node_name": "node1",
        }
    ]

    workloads = discovery.discover_workloads("default")

    assert len(workloads) == 1
    assert workloads[0].status == "DEGRADED"
    assert workloads[0].pod_status == "CRASH_LOOP_BACK_OFF"


def test_workload_info_high_restart_count(discovery, mock_k8s_client):
    """Test workload status determination for high restart count."""
    mock_k8s_client.list_deployments.return_value = [
        {
            "name": "restart-app",
            "namespace": "default",
            "replicas": 1,
            "ready_replicas": 1,
            "available_replicas": 1,
        }
    ]

    mock_k8s_client.list_pods.return_value = [
        {
            "name": "restart-app-123",
            "namespace": "default",
            "phase": "Running",
            "ready": True,
            "restart_count": 8,
            "node_name": "node1",
        }
    ]

    workloads = discovery.discover_workloads("default")

    assert len(workloads) == 1
    assert workloads[0].status == "DEGRADED"
    assert workloads[0].restart_count == 8


def test_format_workloads_table(discovery):
    """Test formatting workloads as a table."""
    workloads = [
        WorkloadInfo(
            name="app1",
            namespace="default",
            ready_replicas=2,
            desired_replicas=2,
            status="HEALTHY",
            pod_status="READY",
            restart_count=0,
        ),
        WorkloadInfo(
            name="app2",
            namespace="default",
            ready_replicas=1,
            desired_replicas=3,
            status="DEGRADED",
            pod_status="NOT_READY",
            restart_count=5,
        ),
    ]

    table = discovery.format_workloads_table(workloads)

    assert "NAME" in table
    assert "READY" in table
    assert "DESIRED" in table
    assert "STATUS" in table
    assert "app1" in table
    assert "app2" in table
    assert "HEALTHY" in table
    assert "DEGRADED" in table


def test_format_workloads_table_empty(discovery):
    """Test formatting empty workloads table."""
    table = discovery.format_workloads_table([])
    assert table == "No workloads found."


def test_get_pod_details(discovery, mock_k8s_client):
    """Test getting pod details."""
    mock_k8s_client.list_pods.return_value = [
        {
            "name": "pod-1",
            "namespace": "default",
            "phase": "Running",
            "ready": True,
            "restart_count": 0,
            "node_name": "node1",
        },
        {
            "name": "pod-2",
            "namespace": "default",
            "phase": "Pending",
            "ready": False,
            "restart_count": 1,
            "node_name": "node2",
        },
    ]

    pods = discovery.get_pod_details("default")

    assert len(pods) == 2
    assert all(isinstance(p, PodInfo) for p in pods)
    assert pods[0].name == "pod-1"
    assert pods[1].name == "pod-2"
    assert pods[0].ready is True
    assert pods[1].ready is False
