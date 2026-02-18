"""CLI list command."""

from __future__ import annotations

import click


@click.command("list")
@click.argument("plugin_type", type=click.Choice(["datasets", "agents", "evaluators", "reporters"]))
def list_cmd(plugin_type: str) -> None:
    """List registered plugins."""
    # Import to ensure registries are populated
    import codingeval.datasets  # noqa: F401
    import codingeval.agents  # noqa: F401
    import codingeval.evaluators  # noqa: F401
    import codingeval.reporters  # noqa: F401

    from rich.console import Console
    from rich.table import Table

    console = Console()

    registry_map = {
        "datasets": ("codingeval.datasets.registry", "list_datasets"),
        "agents": ("codingeval.agents.registry", "list_agents"),
        "evaluators": ("codingeval.evaluators.registry", "list_evaluators"),
        "reporters": ("codingeval.reporters.registry", "list_reporters"),
    }

    module_name, func_name = registry_map[plugin_type]
    import importlib
    module = importlib.import_module(module_name)
    list_func = getattr(module, func_name)
    names = list_func()

    table = Table(title=f"Registered {plugin_type.title()}")
    table.add_column("Name", style="cyan")

    for name in names:
        table.add_row(name)

    console.print(table)
