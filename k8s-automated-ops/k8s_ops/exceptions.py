"""Custom exceptions for k8s-ops."""


class K8sOpsError(Exception):
    """Base exception for k8s-ops errors."""

    pass


class KubernetesConnectionError(K8sOpsError):
    """Raised when unable to connect to Kubernetes cluster."""

    pass


class WorkloadNotFoundError(K8sOpsError):
    """Raised when a workload is not found."""

    pass


class RemediationError(K8sOpsError):
    """Raised when remediation fails."""

    pass


class HealthCheckError(K8sOpsError):
    """Raised when health check fails."""

    pass
