"""Kubernetes client abstraction layer."""

import logging
from typing import Protocol

from kubernetes import client, config
from kubernetes.client.rest import ApiException

from k8s_ops.config import Config
from k8s_ops.exceptions import KubernetesConnectionError, WorkloadNotFoundError

logger = logging.getLogger(__name__)


class KubernetesClientProtocol(Protocol):
    """Protocol for Kubernetes client operations."""

    def list_namespaces(self) -> list[str]:
        """List all namespaces."""
        ...

    def list_deployments(self, namespace: str) -> list[dict]:
        """List deployments in a namespace."""
        ...

    def list_pods(self, namespace: str) -> list[dict]:
        """List pods in a namespace."""
        ...

    def get_deployment(self, name: str, namespace: str) -> dict:
        """Get a specific deployment."""
        ...

    def restart_deployment(self, name: str, namespace: str, *, dry_run: bool) -> None:
        """Restart a deployment."""
        ...

    def scale_deployment(self, name: str, namespace: str, replicas: int, *, dry_run: bool) -> None:
        """Scale a deployment."""
        ...


class KubernetesClient:
    """Concrete implementation of Kubernetes client."""

    def __init__(self, cfg: Config) -> None:
        """Initialize Kubernetes client."""
        self.cfg = cfg
        self._load_config()
        self.apps_v1 = client.AppsV1Api()
        self.core_v1 = client.CoreV1Api()

    def _load_config(self) -> None:
        """Load Kubernetes configuration."""
        try:
            kubeconfig_path = self.cfg.get_kubeconfig_path()
            if kubeconfig_path:
                config.load_kube_config(
                    config_file=str(kubeconfig_path),
                    context=self.cfg.context,
                )
                logger.info(f"Loaded kubeconfig from {kubeconfig_path}")
            else:
                try:
                    config.load_incluster_config()
                    logger.info("Loaded in-cluster config")
                except config.ConfigException:
                    raise KubernetesConnectionError(
                        "No kubeconfig found and not running in-cluster"
                    )
        except Exception as e:
            raise KubernetesConnectionError(f"Failed to load Kubernetes config: {e}")

    def list_namespaces(self) -> list[str]:
        """List all namespaces."""
        try:
            namespaces = self.core_v1.list_namespace()
            return [ns.metadata.name for ns in namespaces.items]
        except ApiException as e:
            logger.error(f"Failed to list namespaces: {e}")
            raise KubernetesConnectionError(f"Failed to list namespaces: {e}")

    def list_deployments(self, namespace: str) -> list[dict]:
        """List deployments in a namespace."""
        try:
            deployments = self.apps_v1.list_namespaced_deployment(namespace)
            return [
                {
                    "name": dep.metadata.name,
                    "namespace": dep.metadata.namespace,
                    "replicas": dep.spec.replicas or 0,
                    "ready_replicas": dep.status.ready_replicas or 0,
                    "available_replicas": dep.status.available_replicas or 0,
                }
                for dep in deployments.items
            ]
        except ApiException as e:
            logger.error(f"Failed to list deployments in {namespace}: {e}")
            raise KubernetesConnectionError(f"Failed to list deployments: {e}")

    def list_pods(self, namespace: str) -> list[dict]:
        """List pods in a namespace."""
        try:
            pods = self.core_v1.list_namespaced_pod(namespace)
            return [
                {
                    "name": pod.metadata.name,
                    "namespace": pod.metadata.namespace,
                    "phase": pod.status.phase,
                    "ready": self._is_pod_ready(pod),
                    "restart_count": self._get_pod_restart_count(pod),
                    "node_name": pod.spec.node_name,
                }
                for pod in pods.items
            ]
        except ApiException as e:
            logger.error(f"Failed to list pods in {namespace}: {e}")
            raise KubernetesConnectionError(f"Failed to list pods: {e}")

    def get_deployment(self, name: str, namespace: str) -> dict:
        """Get a specific deployment."""
        try:
            dep = self.apps_v1.read_namespaced_deployment(name, namespace)
            return {
                "name": dep.metadata.name,
                "namespace": dep.metadata.namespace,
                "replicas": dep.spec.replicas or 0,
                "ready_replicas": dep.status.ready_replicas or 0,
                "available_replicas": dep.status.available_replicas or 0,
            }
        except ApiException as e:
            if e.status == 404:
                raise WorkloadNotFoundError(f"Deployment {name} not found in {namespace}")
            logger.error(f"Failed to get deployment {name}: {e}")
            raise KubernetesConnectionError(f"Failed to get deployment: {e}")

    def restart_deployment(self, name: str, namespace: str, *, dry_run: bool) -> None:
        """Restart a deployment by triggering a rollout restart."""
        try:
            body = {"spec": {"template": {"metadata": {"annotations": {"kubectl.kubernetes.io/restartedAt": "now"}}}}}
            if dry_run:
                logger.info(f"[DRY RUN] Would restart deployment/{name}")
                return
            self.apps_v1.patch_namespaced_deployment(
                name=name,
                namespace=namespace,
                body=body,
            )
            logger.info(f"Restarted deployment/{name}")
        except ApiException as e:
            logger.error(f"Failed to restart deployment {name}: {e}")
            raise KubernetesConnectionError(f"Failed to restart deployment: {e}")

    def scale_deployment(self, name: str, namespace: str, replicas: int, *, dry_run: bool) -> None:
        """Scale a deployment."""
        try:
            body = {"spec": {"replicas": replicas}}
            if dry_run:
                logger.info(f"[DRY RUN] Would scale deployment/{name} to {replicas} replicas")
                return
            self.apps_v1.patch_namespaced_deployment_scale(
                name=name,
                namespace=namespace,
                body=body,
            )
            logger.info(f"Scaled deployment/{name} to {replicas} replicas")
        except ApiException as e:
            logger.error(f"Failed to scale deployment {name}: {e}")
            raise KubernetesConnectionError(f"Failed to scale deployment: {e}")

    def _is_pod_ready(self, pod: client.V1Pod) -> bool:
        """Check if a pod is ready."""
        if not pod.status.conditions:
            return False
        for condition in pod.status.conditions:
            if condition.type == "Ready" and condition.status == "True":
                return True
        return False

    def _get_pod_restart_count(self, pod: client.V1Pod) -> int:
        """Get total restart count for a pod."""
        total = 0
        if pod.status.container_statuses:
            for container_status in pod.status.container_statuses:
                total += container_status.restart_count
        return total
