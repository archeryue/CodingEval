"""Console reporter using Rich."""

from __future__ import annotations

from codingeval.core.models import RunSummary
from codingeval.core.reporter import Reporter


class ConsoleReporter(Reporter):
    """Reporter that outputs results to the console using Rich tables."""

    @property
    def name(self) -> str:
        return "console"

    def report(self, summary: RunSummary, output_dir: str | None = None) -> None:
        from rich.console import Console
        from rich.table import Table

        console = Console()

        # Summary header
        console.print()
        console.print(f"[bold]Run Summary: {summary.run_id}[/bold]")
        console.print(f"  Dataset: {summary.dataset_name}")
        console.print(f"  Agent: {summary.agent_name}")
        console.print(f"  Started: {summary.started_at.strftime('%Y-%m-%d %H:%M:%S')}")
        if summary.completed_at:
            console.print(
                f"  Completed: {summary.completed_at.strftime('%Y-%m-%d %H:%M:%S')}"
            )
        console.print()

        # Stats
        stats_table = Table(title="Statistics")
        stats_table.add_column("Metric", style="cyan")
        stats_table.add_column("Value", justify="right")
        stats_table.add_row("Total Instances", str(summary.total_instances))
        stats_table.add_row("Resolved", f"[green]{summary.resolved}[/green]")
        stats_table.add_row("Failed", f"[red]{summary.failed}[/red]")
        stats_table.add_row("Errors", f"[yellow]{summary.errors}[/yellow]")
        stats_table.add_row("Timeouts", str(summary.timeouts))
        stats_table.add_row("Skipped", str(summary.skipped))
        stats_table.add_row("Resolve Rate", f"{summary.resolve_rate:.1%}")
        console.print(stats_table)
        console.print()

        # Instance details
        if summary.results:
            detail_table = Table(title="Instance Results")
            detail_table.add_column("Instance ID", style="cyan", max_width=40)
            detail_table.add_column("Status", justify="center")
            detail_table.add_column("Resolved", justify="center")
            detail_table.add_column("Duration (s)", justify="right")
            detail_table.add_column("Cost ($)", justify="right")

            for result in summary.results:
                status = result.eval_result.status.value if result.eval_result else "error"
                resolved = result.eval_result.resolved if result.eval_result else False

                status_style = {
                    "passed": "[green]passed[/green]",
                    "failed": "[red]failed[/red]",
                    "error": "[yellow]error[/yellow]",
                    "timeout": "[magenta]timeout[/magenta]",
                    "skipped": "[dim]skipped[/dim]",
                }.get(status, status)

                resolved_str = "[green]Yes[/green]" if resolved else "[red]No[/red]"

                duration = (
                    f"{result.agent_output.duration_seconds:.1f}"
                    if result.agent_output
                    else "-"
                )
                cost = (
                    f"{result.agent_output.cost_usd:.4f}"
                    if result.agent_output and result.agent_output.cost_usd
                    else "-"
                )

                detail_table.add_row(
                    result.instance.instance_id,
                    status_style,
                    resolved_str,
                    duration,
                    cost,
                )

            console.print(detail_table)
