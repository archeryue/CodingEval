"""Tests for reporters."""

import json
import tempfile
from pathlib import Path

from codingeval.core.models import (
    AgentOutput,
    EvalInstance,
    EvalResult,
    EvalStatus,
    InstanceRunResult,
    RunSummary,
)
from codingeval.reporters.console import ConsoleReporter
from codingeval.reporters.json_reporter import JSONReporter


def _make_summary() -> RunSummary:
    instance = EvalInstance(
        instance_id="test-001",
        dataset_name="test",
        repo="owner/repo",
        base_commit="abc123",
        problem_statement="Fix it",
    )
    return RunSummary(
        run_id="test-run-123",
        dataset_name="test",
        agent_name="test-agent",
        total_instances=1,
        resolved=1,
        results=[
            InstanceRunResult(
                instance=instance,
                agent_output=AgentOutput(
                    instance_id="test-001",
                    agent_name="test-agent",
                    duration_seconds=10.5,
                    cost_usd=0.05,
                ),
                eval_result=EvalResult(
                    instance_id="test-001",
                    status=EvalStatus.PASSED,
                    resolved=True,
                ),
            )
        ],
    )


def test_console_reporter_name():
    reporter = ConsoleReporter()
    assert reporter.name == "console"


def test_console_reporter_runs(capsys):
    reporter = ConsoleReporter()
    summary = _make_summary()
    reporter.report(summary)
    # Just verify it doesn't crash; output goes to rich console


def test_json_reporter_name():
    reporter = JSONReporter()
    assert reporter.name == "json"


def test_json_reporter_writes_file():
    reporter = JSONReporter()
    summary = _make_summary()

    with tempfile.TemporaryDirectory() as tmpdir:
        reporter.report(summary, output_dir=tmpdir)
        results_file = Path(tmpdir) / "test-run-123" / "results.json"
        assert results_file.exists()

        with open(results_file) as f:
            data = json.load(f)

        assert data["run_id"] == "test-run-123"
        assert data["resolved"] == 1
        assert len(data["results"]) == 1
