"""Tests for remediation functionality."""

import pytest
from unittest.mock import Mock

from k8s_ops.remediation import (
    RemediationEngine,
    RemediationAction,
    RemediationPlan,
    RemediationResult,
)
from k8s_ops.health import HealthCheckResult, HealthStatus, HealthIssue
from k8s_ops.exceptions import RemediationError
from k8s_ops.kubernetes_client import KubernetesClientProtocol


@pytest.fixture
def mock_k8s_client():
    """Create a mock Kubernetes client."""
    client = Mock(spec=KubernetesClientProtocol)
    return client


@pytest.fixture
def remediation_engine(mock_k8s_client):
    """Create a RemediationEngine instance."""
    return RemediationEngine(mock_k8s_client)


def test_analyze_and_plan_healthy_workload(remediation_engine):
    """Test remediation planning for a healthy workload."""
    from k8s_ops.health import HealthMonitor

    health_mock = Mock(spec=HealthMonitor)
    health_mock.check_workload_health.return_value = HealthCheckResult(
        workload_name="healthy-app",
        namespace="default",
        status=HealthStatus.HEALTHY,
        issues=[],
        ready_replicas=2,
        desired_replicas=2,
        restart_count=0,
    )

    remediation_engine.health_monitor = health_mock

    with pytest.raises(RemediationError) as exc_info:
        remediation_engine.analyze_and_plan("default", "healthy-app")

    assert "healthy" in str(exc_info.value).lower()


def test_analyze_and_plan_crash_loop_back_off(remediation_engine):
    """Test remediation planning for CrashLoopBackOff."""
    from k8s_ops.health import HealthMonitor

    health_mock = Mock(spec=HealthMonitor)
    health_mock.check_workload_health.return_value = HealthCheckResult(
        workload_name="crashing-app",
        namespace="default",
        status=HealthStatus.UNHEALTHY,
        issues=[
            HealthIssue(
                workload_name="crashing-app",
                namespace="default",
                issue_type="crash_loop_back_off",
                severity="critical",
                details="Pods are in CrashLoopBackOff state",
            )
        ],
        ready_replicas=0,
        desired_replicas=1,
        restart_count=10,
    )

    remediation_engine.health_monitor = health_mock

    plan = remediation_engine.analyze_and_plan("default", "crashing-app")

    assert plan.workload_name == "crashing-app"
    assert plan.namespace == "default"
    assert plan.action == RemediationAction.ROLLOUT_RESTART
    assert "crash_loop_back_off" in plan.reason.lower()


def test_analyze_and_plan_replica_mismatch(remediation_engine):
    """Test remediation planning for replica mismatch."""
    from k8s_ops.health import HealthMonitor

    health_mock = Mock(spec=HealthMonitor)
    health_mock.check_workload_health.return_value = HealthCheckResult(
        workload_name="scaling-app",
        namespace="default",
        status=HealthStatus.DEGRADED,
        issues=[
            HealthIssue(
                workload_name="scaling-app",
                namespace="default",
                issue_type="replica_mismatch",
                severity="high",
                details="Only 1/3 replicas ready",
            )
        ],
        ready_replicas=1,
        desired_replicas=3,
        restart_count=0,
    )

    remediation_engine.health_monitor = health_mock

    plan = remediation_engine.analyze_and_plan("default", "scaling-app")

    assert plan.workload_name == "scaling-app"
    assert plan.action == RemediationAction.SCALE_DEPLOYMENT
    assert plan.parameters["replicas"] == 3


def test_analyze_and_plan_high_restart_count(remediation_engine):
    """Test remediation planning for high restart count."""
    from k8s_ops.health import HealthMonitor

    health_mock = Mock(spec=HealthMonitor)
    health_mock.check_workload_health.return_value = HealthCheckResult(
        workload_name="restart-app",
        namespace="default",
        status=HealthStatus.DEGRADED,
        issues=[
            HealthIssue(
                workload_name="restart-app",
                namespace="default",
                issue_type="high_restart_count",
                severity="medium",
                details="High restart count: 8",
            )
        ],
        ready_replicas=1,
        desired_replicas=1,
        restart_count=8,
    )

    remediation_engine.health_monitor = health_mock

    plan = remediation_engine.analyze_and_plan("default", "restart-app")

    assert plan.workload_name == "restart-app"
    assert plan.action == RemediationAction.ROLLOUT_RESTART


def test_execute_plan_dry_run(remediation_engine):
    """Test executing a plan in dry-run mode."""
    plan = RemediationPlan(
        workload_name="test-app",
        namespace="default",
        action=RemediationAction.ROLLOUT_RESTART,
        reason="Test remediation",
        parameters={},
    )

    result = remediation_engine.execute_plan(plan, dry_run=True)

    assert result.success is True
    assert result.dry_run is True
    assert "[DRY RUN]" in result.message
    assert "would" in result.message.lower()

    # Ensure no actual Kubernetes API calls were made
    remediation_engine.k8s_client.restart_deployment.assert_not_called()


def test_execute_plan_restart_success(remediation_engine, mock_k8s_client):
    """Test executing a successful restart plan."""
    plan = RemediationPlan(
        workload_name="test-app",
        namespace="default",
        action=RemediationAction.ROLLOUT_RESTART,
        reason="Test remediation",
        parameters={},
    )

    result = remediation_engine.execute_plan(plan, dry_run=False)

    assert result.success is True
    assert result.dry_run is False
    assert "Successfully" in result.message

    mock_k8s_client.restart_deployment.assert_called_once_with("test-app", "default", dry_run=False)


def test_execute_plan_scale_success(remediation_engine, mock_k8s_client):
    """Test executing a successful scale plan."""
    plan = RemediationPlan(
        workload_name="test-app",
        namespace="default",
        action=RemediationAction.SCALE_DEPLOYMENT,
        reason="Test remediation",
        parameters={"replicas": 3},
    )

    result = remediation_engine.execute_plan(plan, dry_run=False)

    assert result.success is True
    assert result.dry_run is False

    mock_k8s_client.scale_deployment.assert_called_once_with("test-app", "default", 3, dry_run=False)


def test_execute_plan_failure(remediation_engine, mock_k8s_client):
    """Test executing a failed remediation plan."""
    mock_k8s_client.restart_deployment.side_effect = Exception("API error")

    plan = RemediationPlan(
        workload_name="test-app",
        namespace="default",
        action=RemediationAction.ROLLOUT_RESTART,
        reason="Test remediation",
        parameters={},
    )

    result = remediation_engine.execute_plan(plan, dry_run=False)

    assert result.success is False
    assert result.dry_run is False
    assert "failed" in result.message.lower()


def test_verify_recovery_success(remediation_engine):
    """Test successful recovery verification."""
    from k8s_ops.health import HealthMonitor

    health_mock = Mock(spec=HealthMonitor)
    health_mock.check_workload_health.return_value = HealthCheckResult(
        workload_name="test-app",
        namespace="default",
        status=HealthStatus.HEALTHY,
        issues=[],
        ready_replicas=2,
        desired_replicas=2,
        restart_count=0,
    )

    remediation_engine.health_monitor = health_mock

    recovered = remediation_engine.verify_recovery("default", "test-app", timeout=10)

    assert recovered is True


def test_verify_recovery_timeout(remediation_engine):
    """Test recovery verification timeout."""
    from k8s_ops.health import HealthMonitor

    health_mock = Mock(spec=HealthMonitor)
    health_mock.check_workload_health.return_value = HealthCheckResult(
        workload_name="test-app",
        namespace="default",
        status=HealthStatus.DEGRADED,
        issues=[
            HealthIssue(
                workload_name="test-app",
                namespace="default",
                issue_type="replica_mismatch",
                severity="high",
                details="Only 1/2 replicas ready",
            )
        ],
        ready_replicas=1,
        desired_replicas=2,
        restart_count=0,
    )

    remediation_engine.health_monitor = health_mock

    recovered = remediation_engine.verify_recovery("default", "test-app", timeout=5)

    assert recovered is False


def test_determine_action_crash_loop_back_off(remediation_engine):
    """Test action determination for CrashLoopBackOff."""
    health_result = HealthCheckResult(
        workload_name="test-app",
        namespace="default",
        status=HealthStatus.UNHEALTHY,
        issues=[
            HealthIssue(
                workload_name="test-app",
                namespace="default",
                issue_type="crash_loop_back_off",
                severity="critical",
                details="Pods are in CrashLoopBackOff state",
            )
        ],
        ready_replicas=0,
        desired_replicas=1,
        restart_count=10,
    )

    action, params = remediation_engine._determine_action(health_result)

    assert action == RemediationAction.ROLLOUT_RESTART
    assert params == {}


def test_determine_action_replica_mismatch(remediation_engine):
    """Test action determination for replica mismatch."""
    health_result = HealthCheckResult(
        workload_name="test-app",
        namespace="default",
        status=HealthStatus.DEGRADED,
        issues=[
            HealthIssue(
                workload_name="test-app",
                namespace="default",
                issue_type="replica_mismatch",
                severity="high",
                details="Only 1/3 replicas ready",
            )
        ],
        ready_replicas=1,
        desired_replicas=3,
        restart_count=0,
    )

    action, params = remediation_engine._determine_action(health_result)

    assert action == RemediationAction.SCALE_DEPLOYMENT
    assert params["replicas"] == 3


def test_determine_action_default(remediation_engine):
    """Test default action determination."""
    health_result = HealthCheckResult(
        workload_name="test-app",
        namespace="default",
        status=HealthStatus.DEGRADED,
        issues=[
            HealthIssue(
                workload_name="test-app",
                namespace="default",
                issue_type="pending_pods",
                severity="medium",
                details="Pods are in Pending state",
            )
        ],
        ready_replicas=0,
        desired_replicas=1,
        restart_count=0,
    )

    action, params = remediation_engine._determine_action(health_result)

    assert action == RemediationAction.ROLLOUT_RESTART
    assert params == {}


def test_format_remediation_plan(remediation_engine):
    """Test formatting remediation plan."""
    plan = RemediationPlan(
        workload_name="test-app",
        namespace="default",
        action=RemediationAction.ROLLOUT_RESTART,
        reason="Test remediation",
        parameters={"replicas": 3},
    )

    formatted = remediation_engine.format_remediation_plan(plan)

    assert "test-app" in formatted
    assert "default" in formatted
    assert "rollout_restart" in formatted
    assert "Test remediation" in formatted
    assert "replicas" in formatted


def test_format_remediation_result(remediation_engine):
    """Test formatting remediation result."""
    result = RemediationResult(
        workload_name="test-app",
        namespace="default",
        action=RemediationAction.ROLLOUT_RESTART,
        success=True,
        message="Successfully executed rollout_restart",
        dry_run=False,
    )

    formatted = remediation_engine.format_remediation_result(result)

    assert "test-app" in formatted
    assert "default" in formatted
    assert "rollout_restart" in formatted
    assert "True" in formatted
    assert "Successfully" in formatted
