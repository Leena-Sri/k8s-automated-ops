"""Health monitoring functionality."""

import logging
from dataclasses import dataclass
from enum import Enum
from typing import Any

from k8s_ops.discovery import WorkloadDiscovery, WorkloadInfo
from k8s_ops.kubernetes_client import KubernetesClientProtocol

logger = logging.getLogger(__name__)


class HealthStatus(Enum):
    """Health status of a workload."""

    HEALTHY = "healthy"
    UNHEALTHY = "unhealthy"
    DEGRADED = "degraded"
    UNKNOWN = "unknown"


@dataclass
class HealthIssue:
    """Represents a health issue."""

    workload_name: str
    namespace: str
    issue_type: str
    severity: str
    details: str


@dataclass
class HealthCheckResult:
    """Result of a health check."""

    workload_name: str
    namespace: str
    status: HealthStatus
    issues: list[HealthIssue]
    ready_replicas: int
    desired_replicas: int
    restart_count: int


class HealthMonitor:
    """Monitor health of Kubernetes workloads."""

    def __init__(self, k8s_client: KubernetesClientProtocol) -> None:
        """Initialize health monitor."""
        self.k8s_client = k8s_client
        self.discovery = WorkloadDiscovery(k8s_client)

    def check_workload_health(self, namespace: str, workload_name: str) -> HealthCheckResult:
        """Check health of a specific workload."""
        logger.info(f"Checking health of {workload_name} in {namespace}")

        workloads = self.discovery.discover_workloads(namespace)
        workload = next((w for w in workloads if w.name == workload_name), None)

        if not workload:
            logger.warning(f"Workload {workload_name} not found")
            return HealthCheckResult(
                workload_name=workload_name,
                namespace=namespace,
                status=HealthStatus.UNKNOWN,
                issues=[],
                ready_replicas=0,
                desired_replicas=0,
                restart_count=0,
            )

        issues = self._identify_issues(workload)
        status = self._determine_health_status(workload, issues)

        return HealthCheckResult(
            workload_name=workload.name,
            namespace=workload.namespace,
            status=status,
            issues=issues,
            ready_replicas=workload.ready_replicas,
            desired_replicas=workload.desired_replicas,
            restart_count=workload.restart_count,
        )

    def check_all_workloads(self, namespace: str) -> list[HealthCheckResult]:
        """Check health of all workloads in a namespace."""
        logger.info(f"Checking health of all workloads in {namespace}")

        workloads = self.discovery.discover_workloads(namespace)
        results = []

        for workload in workloads:
            issues = self._identify_issues(workload)
            status = self._determine_health_status(workload, issues)

            results.append(
                HealthCheckResult(
                    workload_name=workload.name,
                    namespace=workload.namespace,
                    status=status,
                    issues=issues,
                    ready_replicas=workload.ready_replicas,
                    desired_replicas=workload.desired_replicas,
                    restart_count=workload.restart_count,
                )
            )

        return results

    def _identify_issues(self, workload: WorkloadInfo) -> list[HealthIssue]:
        """Identify health issues in a workload."""
        issues = []

        # Check for replica mismatch
        if workload.ready_replicas < workload.desired_replicas:
            issues.append(
                HealthIssue(
                    workload_name=workload.name,
                    namespace=workload.namespace,
                    issue_type="replica_mismatch",
                    severity="high",
                    details=f"Only {workload.ready_replicas}/{workload.desired_replicas} replicas ready",
                )
            )

        # Check for CrashLoopBackOff
        if workload.pod_status == "CRASH_LOOP_BACK_OFF":
            issues.append(
                HealthIssue(
                    workload_name=workload.name,
                    namespace=workload.namespace,
                    issue_type="crash_loop_back_off",
                    severity="critical",
                    details="Pods are in CrashLoopBackOff state",
                )
            )

        # Check for high restart count
        if workload.restart_count > 5:
            issues.append(
                HealthIssue(
                    workload_name=workload.name,
                    namespace=workload.namespace,
                    issue_type="high_restart_count",
                    severity="medium",
                    details=f"High restart count: {workload.restart_count}",
                )
            )

        # Check for no pods
        if workload.pod_status == "NO_PODS":
            issues.append(
                HealthIssue(
                    workload_name=workload.name,
                    namespace=workload.namespace,
                    issue_type="no_pods",
                    severity="critical",
                    details="No pods found for workload",
                )
            )

        # Check for pending pods
        if workload.pod_status == "PENDING":
            issues.append(
                HealthIssue(
                    workload_name=workload.name,
                    namespace=workload.namespace,
                    issue_type="pending_pods",
                    severity="medium",
                    details="Pods are in Pending state",
                )
            )

        return issues

    def _determine_health_status(self, workload: WorkloadInfo, issues: list[HealthIssue]) -> HealthStatus:
        """Determine overall health status."""
        if not issues and workload.status == "HEALTHY":
            return HealthStatus.HEALTHY

        # Check for critical issues
        critical_issues = [i for i in issues if i.severity == "critical"]
        if critical_issues:
            return HealthStatus.UNHEALTHY

        # Check for high severity issues
        high_issues = [i for i in issues if i.severity == "high"]
        if high_issues:
            return HealthStatus.DEGRADED

        # If there are any issues, it's degraded
        if issues:
            return HealthStatus.DEGRADED

        return HealthStatus.UNKNOWN

    def format_health_report(self, results: list[HealthCheckResult]) -> str:
        """Format health check results as a report."""
        if not results:
            return "No workloads to check."

        lines = ["Health Check Report", "=" * 50]

        for result in results:
            status_icon = self._get_status_icon(result.status)
            lines.append(f"\n{status_icon} {result.workload_name} ({result.namespace})")
            lines.append(f"  Status: {result.status.value}")
            lines.append(f"  Replicas: {result.ready_replicas}/{result.desired_replicas}")
            lines.append(f"  Restarts: {result.restart_count}")

            if result.issues:
                lines.append("  Issues:")
                for issue in result.issues:
                    lines.append(f"    - [{issue.severity.upper()}] {issue.issue_type}: {issue.details}")
            else:
                lines.append("  No issues detected")

        return "\n".join(lines)

    def _get_status_icon(self, status: HealthStatus) -> str:
        """Get an icon for the health status."""
        icons = {
            HealthStatus.HEALTHY: "✓",
            HealthStatus.UNHEALTHY: "✗",
            HealthStatus.DEGRADED: "⚠",
            HealthStatus.UNKNOWN: "?",
        }
        return icons.get(status, "?")

    def get_unhealthy_workloads(self, namespace: str) -> list[HealthCheckResult]:
        """Get only unhealthy workloads."""
        results = self.check_all_workloads(namespace)
        return [r for r in results if r.status in (HealthStatus.UNHEALTHY, HealthStatus.DEGRADED)]
