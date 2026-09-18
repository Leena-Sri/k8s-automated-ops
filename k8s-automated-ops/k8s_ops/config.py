"""Configuration management for k8s-ops."""

import os
from dataclasses import dataclass
from pathlib import Path


@dataclass
class Config:
    """Configuration for the k8s-ops tool."""

    namespace: str = "default"
    kubeconfig: str | None = None
    context: str | None = None
    dry_run: bool = True
    log_level: str = "INFO"
    metrics_port: int = 8000

    @classmethod
    def from_env(cls) -> "Config":
        """Create configuration from environment variables."""
        return cls(
            namespace=os.getenv("K8S_OPS_NAMESPACE", "default"),
            kubeconfig=os.getenv("KUBECONFIG"),
            context=os.getenv("K8S_OPS_CONTEXT"),
            dry_run=os.getenv("K8S_OPS_DRY_RUN", "true").lower() == "true",
            log_level=os.getenv("K8S_OPS_LOG_LEVEL", "INFO"),
            metrics_port=int(os.getenv("K8S_OPS_METRICS_PORT", "8000")),
        )

    def get_kubeconfig_path(self) -> Path | None:
        """Get the kubeconfig path."""
        if self.kubeconfig:
            return Path(self.kubeconfig)
        default_path = Path.home() / ".kube" / "config"
        return default_path if default_path.exists() else None
