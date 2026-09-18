"""Workload discovery functionality."""

import logging
from dataclasses import dataclass
from typing import Any

from k8s_ops.kubernetes_client import KubernetesClientProtocol

logger = logging.getLogger(__name__)


@dataclass
class WorkloadInfo:
    """Information about a workload."""

    name: str
    namespace: str
    ready_replicas: int
    desired_replicas: int
    status: str
    pod_status: str
    restart_count: int


@dataclass
class PodInfo:
    """Information about a pod."""

    name: str
    namespace: str
    phase: str
    ready: bool
    restart_count: int
    node_name: str | None


class WorkloadDiscovery:
    """Discover and analyze Kubernetes workloads."""

    def __init__(self, k8s_client: KubernetesClientProtocol) -> None:
        """Initialize workload discovery."""
        self.k8s_client = k8s_client

    def discover_workloads(self, namespace: str) -> list[WorkloadInfo]:
        """Discover all workloads in a namespace."""
        logger.info(f"Discovering workloads in namespace: {namespace}")

        deployments = self.k8s_client.list_deployments(namespace)
        pods = self.k8s_client.list_pods(namespace)

        workloads = []
        for deployment in deployments:
            workload_info = self._analyze_workload(deployment, pods)
            workloads.append(workload_info)

        return workloads

    def _analyze_workload(self, deployment: dict[str, Any], pods: list[dict[str, Any]]) -> WorkloadInfo:
        """Analyze a single workload."""
        name = deployment["name"]
        namespace = deployment["namespace"]
        desired_replicas = deployment["replicas"]
        ready_replicas = deployment["ready_replicas"]

        # Get pods for this deployment
        deployment_pods = [p for p in pods if p["namespace"] == namespace and name in p["name"]]

        # Calculate pod status
        pod_status = self._get_pod_status(deployment_pods)
        restart_count = sum(p["restart_count"] for p in deployment_pods)

        # Determine overall status
        status = self._determine_status(ready_replicas, desired_replicas, pod_status, restart_count)

        return WorkloadInfo(
            name=name,
            namespace=namespace,
            ready_replicas=ready_replicas,
            desired_replicas=desired_replicas,
            status=status,
            pod_status=pod_status,
            restart_count=restart_count,
        )

    def _get_pod_status(self, pods: list[dict[str, Any]]) -> str:
        """Get the status of pods."""
        if not pods:
            return "NO_PODS"

        # Check for CrashLoopBackOff
        for pod in pods:
            if pod["phase"] == "CrashLoopBackOff":
                return "CRASH_LOOP_BACK_OFF"

        # Check if all pods are ready
        all_ready = all(p["ready"] for p in pods)
        if all_ready:
            return "READY"

        # Check if any pods are pending
        any_pending = any(p["phase"] == "Pending" for p in pods)
        if any_pending:
            return "PENDING"

        return "NOT_READY"

    def _determine_status(
        self, ready_replicas: int, desired_replicas: int, pod_status: str, restart_count: int
    ) -> str:
        """Determine the overall workload status."""
        if pod_status == "CRASH_LOOP_BACK_OFF":
            return "DEGRADED"
        if pod_status == "NO_PODS":
            return "UNHEALTHY"
        if restart_count > 5:
            return "DEGRADED"
        if ready_replicas == desired_replicas and pod_status == "READY":
            return "HEALTHY"
        if ready_replicas < desired_replicas:
            return "DEGRADED"
        return "UNKNOWN"

    def format_workloads_table(self, workloads: list[WorkloadInfo]) -> str:
        """Format workloads as a table."""
        if not workloads:
            return "No workloads found."

        # Calculate column widths
        max_name_len = max(len(w.name) for w in workloads)
        max_name_len = max(max_name_len, len("NAME"))

        # Build header
        header = f"{'NAME':<{max_name_len}}   {'READY':<8} {'DESIRED':<8} {'STATUS':<10}"
        separator = "-" * len(header)

        # Build rows
        rows = []
        for workload in workloads:
            ready_str = f"{workload.ready_replicas}/{workload.desired_replicas}"
            row = f"{workload.name:<{max_name_len}}   {ready_str:<8} {workload.desired_replicas:<8} {workload.status:<10}"
            rows.append(row)

        return "\n".join([header, separator] + rows)

    def get_pod_details(self, namespace: str) -> list[PodInfo]:
        """Get detailed information about pods."""
        pods = self.k8s_client.list_pods(namespace)
        return [
            PodInfo(
                name=pod["name"],
                namespace=pod["namespace"],
                phase=pod["phase"],
                ready=pod["ready"],
                restart_count=pod["restart_count"],
                node_name=pod["node_name"],
            )
            for pod in pods
        ]
