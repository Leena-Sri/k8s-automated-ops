"""Prometheus metrics for k8s-ops."""

import logging
import time
from contextlib import contextmanager
from typing import Any

from prometheus_client import Counter, Gauge, Histogram, start_http_server

logger = logging.getLogger(__name__)


class Metrics:
    """Prometheus metrics for k8s-ops."""

    def __init__(self) -> None:
        """Initialize metrics."""
        self.workloads_total = Gauge(
            "k8s_ops_workloads_total",
            "Total number of workloads discovered",
            ["namespace"],
        )

        self.unhealthy_workloads = Gauge(
            "k8s_ops_unhealthy_workloads",
            "Number of unhealthy workloads",
            ["namespace"],
        )

        self.remediation_total = Counter(
            "k8s_ops_remediation_total",
            "Total number of remediation actions executed",
            ["namespace", "action", "success"],
        )

        self.remediation_failures_total = Counter(
            "k8s_ops_remediation_failures_total",
            "Total number of remediation failures",
            ["namespace", "action"],
        )

        self.health_check_duration = Histogram(
            "k8s_ops_health_check_duration_seconds",
            "Duration of health checks",
            ["namespace"],
        )

        self.discovery_duration = Histogram(
            "k8s_ops_discovery_duration_seconds",
            "Duration of workload discovery",
            ["namespace"],
        )

    def record_workloads(self, namespace: str, count: int) -> None:
        """Record the number of workloads discovered."""
        self.workloads_total.labels(namespace=namespace).set(count)
        logger.debug(f"Recorded {count} workloads for namespace {namespace}")

    def record_unhealthy_workloads(self, namespace: str, count: int) -> None:
        """Record the number of unhealthy workloads."""
        self.unhealthy_workloads.labels(namespace=namespace).set(count)
        logger.debug(f"Recorded {count} unhealthy workloads for namespace {namespace}")

    def record_remediation(
        self, namespace: str, action: str, success: bool, dry_run: bool = False
    ) -> None:
        """Record a remediation action."""
        if dry_run:
            logger.debug(f"Skipping metrics for dry-run remediation")
            return

        self.remediation_total.labels(
            namespace=namespace, action=action, success=str(success).lower()
        ).inc()

        if not success:
            self.remediation_failures_total.labels(namespace=namespace, action=action).inc()

        logger.debug(f"Recorded remediation {action} in {namespace}: success={success}")

    @contextmanager
    def time_health_check(self, namespace: str):
        """Context manager to time health checks."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.health_check_duration.labels(namespace=namespace).observe(duration)
            logger.debug(f"Health check for {namespace} took {duration:.2f}s")

    @contextmanager
    def time_discovery(self, namespace: str):
        """Context manager to time workload discovery."""
        start_time = time.time()
        try:
            yield
        finally:
            duration = time.time() - start_time
            self.discovery_duration.labels(namespace=namespace).observe(duration)
            logger.debug(f"Discovery for {namespace} took {duration:.2f}s")

    def start_server(self, port: int = 8000) -> None:
        """Start the Prometheus metrics HTTP server."""
        try:
            start_http_server(port)
            logger.info(f"Prometheus metrics server started on port {port}")
        except Exception as e:
            logger.error(f"Failed to start metrics server: {e}")
            raise


# Global metrics instance
_metrics: Metrics | None = None


def get_metrics() -> Metrics:
    """Get the global metrics instance."""
    global _metrics
    if _metrics is None:
        _metrics = Metrics()
    return _metrics
