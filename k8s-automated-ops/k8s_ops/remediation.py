"""Automated remediation functionality."""

import logging
import time
from dataclasses import dataclass
from enum import Enum
from typing import Any

from k8s_ops.exceptions import RemediationError, WorkloadNotFoundError
from k8s_ops.health import HealthCheckResult, HealthMonitor, HealthStatus
from k8s_ops.kubernetes_client import KubernetesClientProtocol

logger = logging.getLogger(__name__)


class RemediationAction(Enum):
    """Types of remediation actions."""

    ROLLOUT_RESTART = "rollout_restart"
    SCALE_DEPLOYMENT = "scale_deployment"


@dataclass
class RemediationPlan:
    """Plan for remediation."""

    workload_name: str
    namespace: str
    action: RemediationAction
    reason: str
    parameters: dict[str, Any]


@dataclass
class RemediationResult:
    """Result of a remediation action."""

    workload_name: str
    namespace: str
    action: RemediationAction
    success: bool
    message: str
    dry_run: bool


class RemediationEngine:
    """Engine for automated remediation of unhealthy workloads."""

    def __init__(self, k8s_client: KubernetesClientProtocol) -> None:
        """Initialize remediation engine."""
        self.k8s_client = k8s_client
        self.health_monitor = HealthMonitor(k8s_client)

    def analyze_and_plan(self, namespace: str, workload_name: str) -> RemediationPlan:
        """Analyze a workload and create a remediation plan."""
        logger.info(f"Analyzing {workload_name} for remediation")

        health_result = self.health_monitor.check_workload_health(namespace, workload_name)

        if health_result.status == HealthStatus.HEALTHY:
            raise RemediationError(f"Workload {workload_name} is healthy, no remediation needed")

        # Determine the best remediation action
        action, parameters = self._determine_action(health_result)

        # Build reason string
        reason = self._build_reason(health_result)

        return RemediationPlan(
            workload_name=workload_name,
            namespace=namespace,
            action=action,
            reason=reason,
            parameters=parameters,
        )

    def execute_plan(self, plan: RemediationPlan, dry_run: bool = True) -> RemediationResult:
        """Execute a remediation plan."""
        logger.info(f"Executing remediation plan for {plan.workload_name} (dry_run={dry_run})")

        if dry_run:
            logger.info(f"[DRY RUN] Would execute {plan.action.value} on {plan.workload_name}")
            return RemediationResult(
                workload_name=plan.workload_name,
                namespace=plan.namespace,
                action=plan.action,
                success=True,
                message=f"[DRY RUN] Would {plan.action.value} {plan.workload_name}. Reason: {plan.reason}",
                dry_run=True,
            )

        try:
            if plan.action == RemediationAction.ROLLOUT_RESTART:
                self.k8s_client.restart_deployment(plan.workload_name, plan.namespace, dry_run=False)
            elif plan.action == RemediationAction.SCALE_DEPLOYMENT:
                replicas = plan.parameters.get("replicas", 1)
                self.k8s_client.scale_deployment(
                    plan.workload_name, plan.namespace, replicas, dry_run=False
                )

            return RemediationResult(
                workload_name=plan.workload_name,
                namespace=plan.namespace,
                action=plan.action,
                success=True,
                message=f"Successfully executed {plan.action.value} on {plan.workload_name}",
                dry_run=False,
            )

        except Exception as e:
            logger.error(f"Remediation failed for {plan.workload_name}: {e}")
            return RemediationResult(
                workload_name=plan.workload_name,
                namespace=plan.namespace,
                action=plan.action,
                success=False,
                message=f"Remediation failed: {e}",
                dry_run=False,
            )

    def verify_recovery(self, namespace: str, workload_name: str, timeout: int = 60) -> bool:
        """Verify that a workload has recovered after remediation."""
        logger.info(f"Verifying recovery of {workload_name} (timeout={timeout}s)")

        start_time = time.time()
        while time.time() - start_time < timeout:
            health_result = self.health_monitor.check_workload_health(namespace, workload_name)
            if health_result.status == HealthStatus.HEALTHY:
                logger.info(f"Workload {workload_name} has recovered")
                return True
            time.sleep(5)

        logger.warning(f"Workload {workload_name} did not recover within timeout")
        return False

    def _determine_action(self, health_result: HealthCheckResult) -> tuple[RemediationAction, dict[str, Any]]:
        """Determine the best remediation action based on health issues."""
        # Check for CrashLoopBackOff - restart is best
        crash_loop_issues = [i for i in health_result.issues if i.issue_type == "crash_loop_back_off"]
        if crash_loop_issues:
            return RemediationAction.ROLLOUT_RESTART, {}

        # Check for high restart count - restart is best
        high_restart_issues = [i for i in health_result.issues if i.issue_type == "high_restart_count"]
        if high_restart_issues:
            return RemediationAction.ROLLOUT_RESTART, {}

        # Check for replica mismatch - scale up
        replica_issues = [i for i in health_result.issues if i.issue_type == "replica_mismatch"]
        if replica_issues:
            current_replicas = health_result.ready_replicas
            desired_replicas = health_result.desired_replicas
            if current_replicas < desired_replicas:
                return RemediationAction.SCALE_DEPLOYMENT, {"replicas": desired_replicas}

        # Default to restart for other issues
        return RemediationAction.ROLLOUT_RESTART, {}

    def _build_reason(self, health_result: HealthCheckResult) -> str:
        """Build a reason string for the remediation."""
        if not health_result.issues:
            return f"Workload status: {health_result.status.value}"

        issue_descriptions = [f"{i.issue_type}: {i.details}" for i in health_result.issues]
        return f"Issues detected: {', '.join(issue_descriptions)}"

    def format_remediation_plan(self, plan: RemediationPlan) -> str:
        """Format a remediation plan for display."""
        lines = [
            f"Remediation Plan for {plan.workload_name}",
            "=" * 50,
            f"Namespace: {plan.namespace}",
            f"Action: {plan.action.value}",
            f"Reason: {plan.reason}",
        ]
        if plan.parameters:
            lines.append("Parameters:")
            for key, value in plan.parameters.items():
                lines.append(f"  {key}: {value}")
        return "\n".join(lines)

    def format_remediation_result(self, result: RemediationResult) -> str:
        """Format a remediation result for display."""
        status = "✓" if result.success else "✗"
        lines = [
            f"{status} Remediation {result.action.value} for {result.workload_name}",
            "=" * 50,
            f"Namespace: {result.namespace}",
            f"Success: {result.success}",
            f"Message: {result.message}",
            f"Dry Run: {result.dry_run}",
        ]
        return "\n".join(lines)
