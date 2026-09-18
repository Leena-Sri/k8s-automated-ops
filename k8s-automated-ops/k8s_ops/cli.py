"""CLI interface for k8s-ops."""

import logging
import sys

import click

from k8s_ops.config import Config
from k8s_ops.discovery import WorkloadDiscovery
from k8s_ops.exceptions import K8sOpsError, KubernetesConnectionError, WorkloadNotFoundError
from k8s_ops.health import HealthMonitor
from k8s_ops.kubernetes_client import KubernetesClient
from k8s_ops.metrics import get_metrics
from k8s_ops.remediation import RemediationEngine

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format="%(asctime)s - %(name)s - %(levelname)s - %(message)s",
)
logger = logging.getLogger(__name__)


@click.group()
@click.option("--namespace", default="default", help="Kubernetes namespace")
@click.option("--kubeconfig", help="Path to kubeconfig file")
@click.option("--context", help="Kubernetes context")
@click.option("--dry-run", is_flag=True, default=True, help="Dry run mode (no actual changes)")
@click.option("--metrics-port", default=8000, help="Port for Prometheus metrics")
@click.pass_context
def cli(ctx: click.Context, namespace: str, kubeconfig: str | None, context: str | None, dry_run: bool, metrics_port: int) -> None:
    """Kubernetes Automated Operations CLI."""
    cfg = Config(
        namespace=namespace,
        kubeconfig=kubeconfig,
        context=context,
        dry_run=dry_run,
        metrics_port=metrics_port,
    )

    try:
        k8s_client = KubernetesClient(cfg)
        ctx.ensure_object(dict)
        ctx.obj["config"] = cfg
        ctx.obj["k8s_client"] = k8s_client
        ctx.obj["metrics"] = get_metrics()

        # Start metrics server if not in dry-run mode
        if not dry_run:
            ctx.obj["metrics"].start_server(metrics_port)

    except KubernetesConnectionError as e:
        logger.error(f"Failed to connect to Kubernetes: {e}")
        sys.exit(1)


@cli.command()
@click.pass_context
def workloads(ctx: click.Context) -> None:
    """Discover and display workloads."""
    cfg: Config = ctx.obj["config"]
    k8s_client: KubernetesClient = ctx.obj["k8s_client"]
    metrics = ctx.obj["metrics"]

    try:
        discovery = WorkloadDiscovery(k8s_client)

        with metrics.time_discovery(cfg.namespace):
            workloads = discovery.discover_workloads(cfg.namespace)

        metrics.record_workloads(cfg.namespace, len(workloads))

        table = discovery.format_workloads_table(workloads)
        click.echo(table)

    except K8sOpsError as e:
        logger.error(f"Workload discovery failed: {e}")
        sys.exit(1)


@cli.command()
@click.option("--watch", is_flag=True, help="Watch mode - continuous monitoring")
@click.option("--interval", default=30, help="Watch interval in seconds")
@click.pass_context
def monitor(ctx: click.Context, watch: bool, interval: int) -> None:
    """Monitor workload health."""
    cfg: Config = ctx.obj["config"]
    k8s_client: KubernetesClient = ctx.obj["k8s_client"]
    metrics = ctx.obj["metrics"]

    try:
        health_monitor = HealthMonitor(k8s_client)

        if watch:
            import time

            click.echo(f"Starting health monitoring (interval: {interval}s)")
            click.echo("Press Ctrl+C to stop\n")

            try:
                while True:
                    with metrics.time_health_check(cfg.namespace):
                        results = health_monitor.check_all_workloads(cfg.namespace)

                    unhealthy = [r for r in results if r.status.value in ("unhealthy", "degraded")]
                    metrics.record_unhealthy_workloads(cfg.namespace, len(unhealthy))

                    report = health_monitor.format_health_report(results)
                    click.echo(f"\n{report}")
                    click.echo(f"\nNext check in {interval}s...")

                    time.sleep(interval)

            except KeyboardInterrupt:
                click.echo("\nMonitoring stopped")

        else:
            with metrics.time_health_check(cfg.namespace):
                results = health_monitor.check_all_workloads(cfg.namespace)

            unhealthy = [r for r in results if r.status.value in ("unhealthy", "degraded")]
            metrics.record_unhealthy_workloads(cfg.namespace, len(unhealthy))

            report = health_monitor.format_health_report(results)
            click.echo(report)

            if unhealthy:
                click.echo(f"\n⚠ Found {len(unhealthy)} unhealthy workload(s)")
                sys.exit(1)

    except K8sOpsError as e:
        logger.error(f"Health monitoring failed: {e}")
        sys.exit(1)


@cli.command()
@click.argument("workload_name")
@click.option("--no-dry-run", is_flag=True, help="Execute actual remediation (disable dry-run)")
@click.option("--verify", is_flag=True, help="Verify recovery after remediation")
@click.option("--timeout", default=60, help="Recovery verification timeout in seconds")
@click.pass_context
def remediate(ctx: click.Context, workload_name: str, no_dry_run: bool, verify: bool, timeout: int) -> None:
    """Remediate an unhealthy workload."""
    cfg: Config = ctx.obj["config"]
    k8s_client: KubernetesClient = ctx.obj["k8s_client"]
    metrics = ctx.obj["metrics"]

    # Use CLI flag to override config default
    dry_run = cfg.dry_run and not no_dry_run

    try:
        remediation_engine = RemediationEngine(k8s_client)

        # Analyze and create plan
        plan = remediation_engine.analyze_and_plan(cfg.namespace, workload_name)
        plan_output = remediation_engine.format_remediation_plan(plan)

        if dry_run:
            click.echo("[DRY RUN]")
            click.echo(plan_output)
        else:
            click.echo(plan_output)

        # Execute plan
        result = remediation_engine.execute_plan(plan, dry_run=dry_run)
        result_output = remediation_engine.format_remediation_result(result)
        click.echo(result_output)

        # Record metrics
        metrics.record_remediation(
            cfg.namespace,
            plan.action.value,
            result.success,
            dry_run=dry_run,
        )

        # Verify recovery if requested and not dry-run
        if verify and not dry_run and result.success:
            click.echo(f"\nVerifying recovery (timeout: {timeout}s)...")
            recovered = remediation_engine.verify_recovery(cfg.namespace, workload_name, timeout)

            if recovered:
                click.echo("✓ Workload has recovered successfully")
            else:
                click.echo("✗ Workload did not recover within timeout")
                sys.exit(1)

    except WorkloadNotFoundError as e:
        logger.error(f"Workload not found: {e}")
        sys.exit(1)
    except K8sOpsError as e:
        logger.error(f"Remediation failed: {e}")
        sys.exit(1)


def main() -> None:
    """Entry point for the CLI."""
    cli()


if __name__ == "__main__":
    main()
