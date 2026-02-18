"""CLI run command."""

from __future__ import annotations

import click


@click.command("run")
@click.option("--config", "-c", type=click.Path(exists=True), help="Config YAML file")
@click.option("--dataset", "-d", "dataset_name", help="Dataset name")
@click.option("--agent", "-a", "agent_name", help="Agent name")
@click.option("--limit", "-n", type=int, help="Max instances to run")
@click.option("--instance", "-i", "instance_ids", multiple=True, help="Specific instance IDs")
@click.option("--max-workers", "-w", type=int, help="Max parallel workers")
@click.option("--run-id", help="Custom run ID")
@click.option("--log-level", default="INFO", help="Log level")
@click.option("--dry-run", is_flag=True, help="Validate setup without running the agent")
@click.option("--no-docker", is_flag=True, help="Run tests on host instead of Docker")
def run_cmd(
    config: str | None,
    dataset_name: str | None,
    agent_name: str | None,
    limit: int | None,
    instance_ids: tuple[str, ...],
    max_workers: int | None,
    run_id: str | None,
    log_level: str,
    dry_run: bool,
    no_docker: bool,
) -> None:
    """Run an evaluation."""
    # Import here to ensure registries are populated
    import codingeval.agents  # noqa: F401
    import codingeval.datasets  # noqa: F401
    import codingeval.evaluators  # noqa: F401
    import codingeval.reporters  # noqa: F401
    from codingeval.agents.registry import get_agent
    from codingeval.core.config import RunConfig
    from codingeval.core.runner import Runner
    from codingeval.datasets.registry import get_dataset
    from codingeval.evaluators.registry import get_evaluator
    from codingeval.reporters.registry import get_reporter
    from codingeval.utils.logging import setup_logging

    # Load config
    if config:
        run_config = RunConfig.from_yaml(config)
    else:
        run_config = RunConfig()

    # Apply CLI overrides
    run_config.merge_overrides(
        dataset_name=dataset_name,
        agent_name=agent_name,
        limit=limit,
        instance_ids=list(instance_ids) if instance_ids else None,
        max_workers=max_workers,
    )
    run_config.log_level = log_level
    if no_docker:
        run_config.docker.enabled = False

    setup_logging(run_config.log_level)

    # Resolve components
    dataset = get_dataset(run_config.dataset.name)
    agent = get_agent(run_config.agent.name)
    agent.configure(run_config.agent.options)
    evaluator = get_evaluator(run_config.evaluator)
    reporter = get_reporter(run_config.reporter)

    if dry_run:
        _dry_run(run_config, dataset, agent)
        return

    # Run
    runner = Runner(run_config, dataset, agent, evaluator, reporter)
    summary = runner.run(run_id=run_id)

    # Also write JSON results
    if run_config.reporter != "json":
        from codingeval.reporters.json_reporter import JSONReporter

        json_reporter = JSONReporter()
        json_reporter.report(summary, output_dir=run_config.results_dir)

    click.echo(
        f"\nRun {summary.run_id} complete: "
        f"{summary.resolved}/{summary.total_instances} resolved"
    )


def _dry_run(run_config, dataset, agent) -> None:
    """Validate setup: load dataset, check Docker, verify agent command."""
    import shutil

    from rich.console import Console

    console = Console()
    instances = []

    console.print("\n[bold]Dry run — validating setup[/bold]\n")

    # 1. Dataset
    console.print("[cyan]Dataset:[/cyan]", run_config.dataset.name)
    try:
        dataset.load(**run_config.dataset.options)
        instances = dataset.get_instances(
            split=run_config.dataset.split,
            instance_ids=run_config.dataset.instance_ids or None,
            limit=run_config.dataset.limit or 5,
        )
        console.print(f"  [green]OK[/green] — loaded {len(instances)} instances")
        if instances:
            console.print(f"  First: {instances[0].instance_id}")
            console.print(f"  Repo:  {instances[0].repo}")
    except Exception as e:
        console.print(f"  [red]FAIL[/red] — {e}")

    # 2. Agent
    console.print(f"\n[cyan]Agent:[/cyan] {agent.name}")
    console.print(f"  Execution mode: {agent.execution_mode.value}")
    console.print(f"  Timeout: {agent.get_timeout_seconds()}s")
    if instances:
        cmd = agent.build_command(instances[0], "/tmp/testbed")
        # Show command without the prompt (it can be very long)
        cmd_display = cmd[:6] + (["..."] if len(cmd) > 6 else [])
        console.print(f"  Command: {' '.join(cmd_display)}")

    # 3. Docker
    console.print("\n[cyan]Docker:[/cyan]")
    try:
        import docker

        client = docker.from_env()
        client.ping()
        console.print("  [green]OK[/green] — Docker daemon reachable")

        # Check for base image
        try:
            client.images.get(run_config.docker.base_image)
            console.print(f"  [green]OK[/green] — Image {run_config.docker.base_image} found")
        except docker.errors.ImageNotFound:
            console.print(
                f"  [yellow]WARN[/yellow] — Image {run_config.docker.base_image} not found. "
                f"Build it with: docker build -t {run_config.docker.base_image} docker/base/"
            )
        client.close()
    except Exception as e:
        console.print(f"  [red]FAIL[/red] — {e}")

    # 4. Agent binary
    console.print("\n[cyan]Agent binary:[/cyan]")
    # Determine the binary name from agent command or fall back to common name
    if instances:
        binary = agent.build_command(instances[0], "/tmp")[0]
    else:
        binary = "claude" if agent.name == "claude-code" else agent.name
    if shutil.which(binary):
        console.print(f"  [green]OK[/green] — {binary!r} found in PATH")
    else:
        console.print(f"  [red]FAIL[/red] — {binary!r} not found in PATH")

    console.print()
