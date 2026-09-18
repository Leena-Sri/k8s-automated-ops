"""Tests for health monitoring functionality."""

import pytest
from unittest.mock import Mock

from k8s_ops.health import (
    HealthMonitor,
    HealthStatus,
    HealthIssue,
    HealthCheckResult,
)
from k8s_ops.discovery import WorkloadInfo
from k8s_ops.kubernetes_client import KubernetesClientProtocol


@pytest.fixture
def mock_k8s_client():
    """Create a mock Kubernetes client."""
    client = Mock(spec=KubernetesClientProtocol)
    return client


@pytest.fixture
def health_monitor(mock_k8s_client):
    """Create a HealthMonitor instance."""
    return HealthMonitor(mock_k8s_client)


def test_check_workload_health_healthy(health_monitor, mock_k8s_client):
    """Test health check for a healthy workload."""
    # Mock the discovery to return a healthy workload
    from k8s_ops.discovery import WorkloadDiscovery

    discovery_mock = Mock(spec=WorkloadDiscovery)
    discovery_mock.discover_workloads.return_value = [
        WorkloadInfo(
            name="healthy-app",
            namespace="default",
            ready_replicas=3,
            desired_replicas=3,
            status="HEALTHY",
            pod_status="READY",
            restart_count=0,
        )
    ]

    health_monitor.discovery = discovery_mock

    result = health_monitor.check_workload_health("default", "healthy-app")

    assert result.workload_name == "healthy-app"
    assert result.status == HealthStatus.HEALTHY
    assert len(result.issues) == 0
    assert result.ready_replicas == 3
    assert result.desired_replicas == 3


def test_check_workload_health_unhealthy(health_monitor, mock_k8s_client):
    """Test health check for an unhealthy workload."""
    from k8s_ops.discovery import WorkloadDiscovery

    discovery_mock = Mock(spec=WorkloadDiscovery)
    discovery_mock.discover_workloads.return_value = [
        WorkloadInfo(
            name="unhealthy-app",
            namespace="default",
            ready_replicas=0,
            desired_replicas=3,
            status="DEGRADED",
            pod_status="CRASH_LOOP_BACK_OFF",
            restart_count=10,
        )
    ]

    health_monitor.discovery = discovery_mock

    result = health_monitor.check_workload_health("default", "unhealthy-app")

    assert result.workload_name == "unhealthy-app"
    assert result.status == HealthStatus.UNHEALTHY
    assert len(result.issues) > 0


def test_check_workload_health_not_found(health_monitor, mock_k8s_client):
    """Test health check for a non-existent workload."""
    from k8s_ops.discovery import WorkloadDiscovery

    discovery_mock = Mock(spec=WorkloadDiscovery)
    discovery_mock.discover_workloads.return_value = []

    health_monitor.discovery = discovery_mock

    result = health_monitor.check_workload_health("default", "nonexistent")

    assert result.workload_name == "nonexistent"
    assert result.status == HealthStatus.UNKNOWN
    assert len(result.issues) == 0


def test_check_all_workloads(health_monitor, mock_k8s_client):
    """Test health check for all workloads."""
    from k8s_ops.discovery import WorkloadDiscovery

    discovery_mock = Mock(spec=WorkloadDiscovery)
    discovery_mock.discover_workloads.return_value = [
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
            restart_count=0,
        ),
    ]

    health_monitor.discovery = discovery_mock

    results = health_monitor.check_all_workloads("default")

    assert len(results) == 2
    assert results[0].workload_name == "app1"
    assert results[1].workload_name == "app2"


def test_identify_replica_mismatch(health_monitor):
    """Test identification of replica mismatch issues."""
    workload = WorkloadInfo(
        name="app",
        namespace="default",
        ready_replicas=1,
        desired_replicas=3,
        status="DEGRADED",
        pod_status="NOT_READY",
        restart_count=0,
    )

    issues = health_monitor._identify_issues(workload)

    assert len(issues) > 0
    assert any(i.issue_type == "replica_mismatch" for i in issues)


def test_identify_crash_loop_back_off(health_monitor):
    """Test identification of CrashLoopBackOff issues."""
    workload = WorkloadInfo(
        name="app",
        namespace="default",
        ready_replicas=0,
        desired_replicas=1,
        status="DEGRADED",
        pod_status="CRASH_LOOP_BACK_OFF",
        restart_count=10,
    )

    issues = health_monitor._identify_issues(workload)

    assert len(issues) > 0
    assert any(i.issue_type == "crash_loop_back_off" for i in issues)
    assert any(i.severity == "critical" for i in issues)


def test_identify_high_restart_count(health_monitor):
    """Test identification of high restart count issues."""
    workload = WorkloadInfo(
        name="app",
        namespace="default",
        ready_replicas=1,
        desired_replicas=1,
        status="HEALTHY",
        pod_status="READY",
        restart_count=8,
    )

    issues = health_monitor._identify_issues(workload)

    assert len(issues) > 0
    assert any(i.issue_type == "high_restart_count" for i in issues)


def test_identify_no_pods(health_monitor):
    """Test identification of no pods issues."""
    workload = WorkloadInfo(
        name="app",
        namespace="default",
        ready_replicas=0,
        desired_replicas=1,
        status="UNHEALTHY",
        pod_status="NO_PODS",
        restart_count=0,
    )

    issues = health_monitor._identify_issues(workload)

    assert len(issues) > 0
    assert any(i.issue_type == "no_pods" for i in issues)
    assert any(i.severity == "critical" for i in issues)


def test_identify_pending_pods(health_monitor):
    """Test identification of pending pods issues."""
    workload = WorkloadInfo(
        name="app",
        namespace="default",
        ready_replicas=0,
        desired_replicas=1,
        status="DEGRADED",
        pod_status="PENDING",
        restart_count=0,
    )

    issues = health_monitor._identify_issues(workload)

    assert len(issues) > 0
    assert any(i.issue_type == "pending_pods" for i in issues)


def test_determine_health_status_healthy(health_monitor):
    """Test health status determination for healthy workload."""
    workload = WorkloadInfo(
        name="app",
        namespace="default",
        ready_replicas=2,
        desired_replicas=2,
        status="HEALTHY",
        pod_status="READY",
        restart_count=0,
    )

    status = health_monitor._determine_health_status(workload, [])

    assert status == HealthStatus.HEALTHY


def test_determine_health_status_unhealthy(health_monitor):
    """Test health status determination for unhealthy workload."""
    workload = WorkloadInfo(
        name="app",
        namespace="default",
        ready_replicas=0,
        desired_replicas=1,
        status="DEGRADED",
        pod_status="CRASH_LOOP_BACK_OFF",
        restart_count=10,
    )

    issues = health_monitor._identify_issues(workload)
    status = health_monitor._determine_health_status(workload, issues)

    assert status == HealthStatus.UNHEALTHY


def test_determine_health_status_degraded(health_monitor):
    """Test health status determination for degraded workload."""
    workload = WorkloadInfo(
        name="app",
        namespace="default",
        ready_replicas=1,
        desired_replicas=3,
        status="DEGRADED",
        pod_status="NOT_READY",
        restart_count=0,
    )

    issues = health_monitor._identify_issues(workload)
    status = health_monitor._determine_health_status(workload, issues)

    assert status == HealthStatus.DEGRADED


def test_format_health_report(health_monitor):
    """Test formatting health report."""
    results = [
        HealthCheckResult(
            workload_name="app1",
            namespace="default",
            status=HealthStatus.HEALTHY,
            issues=[],
            ready_replicas=2,
            desired_replicas=2,
            restart_count=0,
        ),
        HealthCheckResult(
            workload_name="app2",
            namespace="default",
            status=HealthStatus.DEGRADED,
            issues=[
                HealthIssue(
                    workload_name="app2",
                    namespace="default",
                    issue_type="replica_mismatch",
                    severity="high",
                    details="Only 1/3 replicas ready",
                )
            ],
            ready_replicas=1,
            desired_replicas=3,
            restart_count=0,
        ),
    ]

    report = health_monitor.format_health_report(results)

    assert "Health Check Report" in report
    assert "app1" in report
    assert "app2" in report
    assert "healthy" in report
    assert "degraded" in report
    assert "replica_mismatch" in report


def test_get_unhealthy_workloads(health_monitor, mock_k8s_client):
    """Test getting only unhealthy workloads."""
    from k8s_ops.discovery import WorkloadDiscovery

    discovery_mock = Mock(spec=WorkloadDiscovery)
    discovery_mock.discover_workloads.return_value = [
        WorkloadInfo(
            name="healthy-app",
            namespace="default",
            ready_replicas=2,
            desired_replicas=2,
            status="HEALTHY",
            pod_status="READY",
            restart_count=0,
        ),
        WorkloadInfo(
            name="unhealthy-app",
            namespace="default",
            ready_replicas=0,
            desired_replicas=1,
            status="DEGRADED",
            pod_status="CRASH_LOOP_BACK_OFF",
            restart_count=10,
        ),
    ]

    health_monitor.discovery = discovery_mock

    unhealthy = health_monitor.get_unhealthy_workloads("default")

    assert len(unhealthy) == 1
    assert unhealthy[0].workload_name == "unhealthy-app"
