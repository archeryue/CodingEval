"""Integration tests for the evaluation pipeline.

These tests use mock agents and a custom dataset to exercise the pipeline
without requiring Docker, network access, or real agent binaries.
"""

from __future__ import annotations

import json
import tempfile
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from codingeval.core.config import RunConfig
from codingeval.core.models import (
    AgentOutput,
    EvalInstance,
    EvalResult,
    EvalStatus,
    SingleTestResult,
)
from codingeval.datasets.custom import CustomDataset


# ── Fixtures ──────────────────────────────────────────────────────────


@pytest.fixture
def custom_dataset_path(tmp_path: Path) -> Path:
    """Create a minimal custom dataset YAML."""
    yaml_content = """
dataset_name: integration-test
instances:
  - instance_id: test-int-001
    repo: example/repo
    base_commit: abc123
    problem_statement: Fix the bug
    fail_to_pass:
      - tests/test_main.py::test_bug_fixed
    pass_to_pass:
      - tests/test_main.py::test_existing
  - instance_id: test-int-002
    repo: example/repo
    base_commit: def456
    problem_statement: Fix another bug
    fail_to_pass:
      - tests/test_main.py::test_other
"""
    path = tmp_path / "test_dataset.yaml"
    path.write_text(yaml_content)
    return path


# ── Tests ─────────────────────────────────────────────────────────────


def test_custom_dataset_loads(custom_dataset_path: Path):
    """Verify custom dataset loads and filters correctly."""
    ds = CustomDataset(custom_dataset_path)
    ds.load()

    instances = ds.get_instances()
    assert len(instances) == 2
    assert instances[0].instance_id == "test-int-001"
    assert instances[0].fail_to_pass == ["tests/test_main.py::test_bug_fixed"]

    # Filter by ID
    filtered = ds.get_instances(instance_ids=["test-int-002"])
    assert len(filtered) == 1
    assert filtered[0].instance_id == "test-int-002"

    # Limit
    limited = ds.get_instances(limit=1)
    assert len(limited) == 1


def test_agent_output_round_trip():
    """Verify AgentOutput serialization in RunSummary.to_dict()."""
    from codingeval.core.models import InstanceRunResult, RunSummary

    instance = EvalInstance(
        instance_id="rt-001",
        dataset_name="test",
        repo="owner/repo",
        base_commit="abc",
        problem_statement="Fix it",
    )
    agent_out = AgentOutput(
        instance_id="rt-001",
        agent_name="mock-agent",
        patch="diff --git a/f.py b/f.py",
        exit_code=0,
        duration_seconds=15.3,
        cost_usd=0.042,
    )
    eval_result = EvalResult(
        instance_id="rt-001",
        status=EvalStatus.PASSED,
        resolved=True,
        fail_to_pass_results=[
            SingleTestResult(test_name="test_bug", passed=True),
        ],
    )

    summary = RunSummary(
        run_id="rt-run",
        dataset_name="test",
        agent_name="mock-agent",
        total_instances=1,
        resolved=1,
        results=[
            InstanceRunResult(
                instance=instance,
                agent_output=agent_out,
                eval_result=eval_result,
            )
        ],
    )

    d = summary.to_dict()
    # Round-trip through JSON
    serialized = json.dumps(d)
    deserialized = json.loads(serialized)

    assert deserialized["run_id"] == "rt-run"
    assert deserialized["resolve_rate"] == 1.0
    assert deserialized["results"][0]["cost_usd"] == 0.042
    assert deserialized["results"][0]["resolved"] is True


def test_json_reporter_round_trip(tmp_path: Path):
    """Write JSON results, then read and verify via the report CLI path."""
    from codingeval.core.models import InstanceRunResult, RunSummary
    from codingeval.reporters.json_reporter import JSONReporter

    instance = EvalInstance(
        instance_id="jr-001",
        dataset_name="test",
        repo="owner/repo",
        base_commit="abc",
        problem_statement="Fix it",
    )
    summary = RunSummary(
        run_id="json-test",
        dataset_name="test",
        agent_name="mock",
        total_instances=1,
        resolved=1,
        results=[
            InstanceRunResult(
                instance=instance,
                agent_output=AgentOutput(
                    instance_id="jr-001",
                    agent_name="mock",
                    duration_seconds=5.0,
                ),
                eval_result=EvalResult(
                    instance_id="jr-001",
                    status=EvalStatus.PASSED,
                    resolved=True,
                ),
            )
        ],
    )

    reporter = JSONReporter()
    reporter.report(summary, output_dir=str(tmp_path))

    results_file = tmp_path / "json-test" / "results.json"
    assert results_file.exists()

    data = json.loads(results_file.read_text())
    assert data["resolved"] == 1
    assert data["results"][0]["instance_id"] == "jr-001"


def test_claude_code_agent_parses_real_output():
    """Test parsing against the actual Claude Code JSON output format."""
    from codingeval.agents.claude_code import ClaudeCodeAgent

    real_output = json.dumps({
        "type": "result",
        "subtype": "success",
        "is_error": False,
        "duration_ms": 45000,
        "duration_api_ms": 44000,
        "num_turns": 5,
        "result": "I've fixed the issue by updating the validate function.",
        "stop_reason": None,
        "session_id": "ae53ba42-1789-4c22-8352-ec4b1cce9494",
        "total_cost_usd": 0.15,
        "usage": {
            "input_tokens": 5000,
            "cache_creation_input_tokens": 1323,
            "cache_read_input_tokens": 17997,
            "output_tokens": 2000,
        },
        "modelUsage": {
            "claude-sonnet-4-5-20250929": {
                "inputTokens": 5000,
                "outputTokens": 2000,
                "costUSD": 0.15,
            }
        },
    })

    agent = ClaudeCodeAgent()
    output = agent.parse_output(real_output, "", 0, 45.0)

    assert output.cost_usd == 0.15
    assert output.tokens_used == 5000 + 2000 + 17997
    assert output.model_name == "claude-sonnet-4-5-20250929"
    assert output.stdout == "I've fixed the issue by updating the validate function."
    assert output.metadata["num_turns"] == 5
    assert output.metadata["session_id"] == "ae53ba42-1789-4c22-8352-ec4b1cce9494"


def test_registry_round_trip():
    """Verify that all registries return working instances."""
    import codingeval.agents  # noqa: F401
    import codingeval.datasets  # noqa: F401
    import codingeval.evaluators  # noqa: F401
    import codingeval.reporters  # noqa: F401
    from codingeval.agents.registry import get_agent, list_agents
    from codingeval.datasets.registry import get_dataset, list_datasets
    from codingeval.evaluators.registry import get_evaluator, list_evaluators
    from codingeval.reporters.registry import get_reporter, list_reporters

    # Datasets
    for name in list_datasets():
        ds = get_dataset(name)
        assert ds.name == name, f"Dataset {name!r} returned name={ds.name!r}"

    # Agents
    for name in list_agents():
        agent = get_agent(name)
        assert agent.name == name

    # Evaluators
    for name in list_evaluators():
        ev = get_evaluator(name)
        assert ev.name == name

    # Reporters
    for name in list_reporters():
        rep = get_reporter(name)
        assert rep.name == name
