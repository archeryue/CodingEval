"""Main CLI entry point."""

from __future__ import annotations

import click

from codingeval.cli.list_cmd import list_cmd
from codingeval.cli.report import report_cmd
from codingeval.cli.run import run_cmd


@click.group()
@click.version_option(version="0.1.0", prog_name="codingeval")
def cli() -> None:
    """CodingEval: Evaluation framework for CLI coding agents."""


cli.add_command(run_cmd, "run")
cli.add_command(list_cmd, "list")
cli.add_command(report_cmd, "report")

if __name__ == "__main__":
    cli()
