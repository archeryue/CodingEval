"""CLI report command."""

from __future__ import annotations

import json
from pathlib import Path

import click


@click.command("report")
@click.argument("results_file", type=click.Path(exists=True))
def report_cmd(results_file: str) -> None:
    """View results from a previous run."""
    from rich.console import Console
    from rich.table import Table

    console = Console()
    path = Path(results_file)

    with open(path) as f:
        data = json.load(f)

    console.print()
    console.print(f"[bold]Run: {data['run_id']}[/bold]")
    console.print(f"  Dataset: {data['dataset_name']}")
    console.print(f"  Agent: {data['agent_name']}")
    console.print(f"  Started: {data.get('started_at', 'N/A')}")
    console.print(f"  Completed: {data.get('completed_at', 'N/A')}")
    console.print()

    stats_table = Table(title="Statistics")
    stats_table.add_column("Metric", style="cyan")
    stats_table.add_column("Value", justify="right")
    stats_table.add_row("Total Instances", str(data["total_instances"]))
    stats_table.add_row("Resolved", f"[green]{data['resolved']}[/green]")
    stats_table.add_row("Failed", f"[red]{data['failed']}[/red]")
    stats_table.add_row("Errors", f"[yellow]{data['errors']}[/yellow]")
    stats_table.add_row("Timeouts", str(data.get("timeouts", 0)))
    stats_table.add_row("Resolve Rate", f"{data.get('resolve_rate', 0):.1%}")
    console.print(stats_table)
    console.print()

    if data.get("results"):
        detail_table = Table(title="Instance Results")
        detail_table.add_column("Instance ID", style="cyan", max_width=40)
        detail_table.add_column("Status", justify="center")
        detail_table.add_column("Resolved", justify="center")
        detail_table.add_column("Duration (s)", justify="right")
        detail_table.add_column("Cost ($)", justify="right")

        for r in data["results"]:
            status = r.get("status", "error")
            resolved = r.get("resolved", False)

            status_style = {
                "passed": "[green]passed[/green]",
                "failed": "[red]failed[/red]",
                "error": "[yellow]error[/yellow]",
                "timeout": "[magenta]timeout[/magenta]",
                "skipped": "[dim]skipped[/dim]",
            }.get(status, status)

            resolved_str = "[green]Yes[/green]" if resolved else "[red]No[/red]"
            duration = f"{r['agent_duration']:.1f}" if r.get("agent_duration") else "-"
            cost = f"{r['cost_usd']:.4f}" if r.get("cost_usd") else "-"

            detail_table.add_row(r["instance_id"], status_style, resolved_str, duration, cost)

        console.print(detail_table)
