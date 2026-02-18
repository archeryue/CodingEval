"""Tests for core data models."""

from datetime import datetime

from codingeval.core.models import (
    AgentOutput,
    EvalInstance,
    EvalResult,
    EvalStatus,
    ExecutionMode,
    InstanceRunResult,
    RunSummary,
    SingleTestResult,
)


def test_eval_instance_frozen():
    instance = EvalInstance(
        instance_id="test-001",
        dataset_name="test",
        repo="owner/repo",
        base_commit="abc123",
        problem_statement="Fix the bug",
    )
    assert instance.instance_id == "test-001"
    assert instance.dataset_name == "test"
    assert instance.repo == "owner/repo"
    assert instance.hints_text == ""
    assert instance.fail_to_pass == []
    assert instance.metadata == {}


def test_eval_instance_with_all_fields():
    instance = EvalInstance(
        instance_id="test-002",
        dataset_name="swebench",
        repo="django/django",
        base_commit="abc123",
        problem_statement="Fix issue",
        hints_text="Check models.py",
        test_patch="diff --git a/test.py",
        gold_patch="diff --git a/fix.py",
        fail_to_pass=["test_foo"],
        pass_to_pass=["test_bar"],
        metadata={"version": "1.0"},
    )
    assert instance.fail_to_pass == ["test_foo"]
    assert instance.pass_to_pass == ["test_bar"]
    assert instance.metadata["version"] == "1.0"


def test_agent_output():
    output = AgentOutput(
        instance_id="test-001",
        agent_name="claude-code",
        patch="diff --git a/fix.py",
        exit_code=0,
        duration_seconds=42.5,
        cost_usd=0.05,
    )
    assert output.instance_id == "test-001"
    assert output.cost_usd == 0.05


def test_eval_result():
    result = EvalResult(
        instance_id="test-001",
        status=EvalStatus.PASSED,
        resolved=True,
        fail_to_pass_results=[
            SingleTestResult(test_name="test_foo", passed=True),
        ],
    )
    assert result.resolved is True
    assert result.status == EvalStatus.PASSED
    assert len(result.fail_to_pass_results) == 1


def test_eval_status_values():
    assert EvalStatus.PASSED.value == "passed"
    assert EvalStatus.FAILED.value == "failed"
    assert EvalStatus.ERROR.value == "error"
    assert EvalStatus.TIMEOUT.value == "timeout"


def test_execution_mode_values():
    assert ExecutionMode.HOST.value == "host"
    assert ExecutionMode.CONTAINER.value == "container"


def test_run_summary_resolve_rate():
    summary = RunSummary(
        run_id="test-run",
        dataset_name="test",
        agent_name="test-agent",
        total_instances=10,
        resolved=3,
        failed=5,
        errors=2,
    )
    assert summary.resolve_rate == 0.3


def test_run_summary_resolve_rate_zero():
    summary = RunSummary(
        run_id="test-run",
        dataset_name="test",
        agent_name="test-agent",
        total_instances=0,
    )
    assert summary.resolve_rate == 0.0


def test_run_summary_to_dict():
    instance = EvalInstance(
        instance_id="test-001",
        dataset_name="test",
        repo="owner/repo",
        base_commit="abc123",
        problem_statement="Fix it",
    )
    agent_output = AgentOutput(
        instance_id="test-001",
        agent_name="test-agent",
        duration_seconds=10.0,
        cost_usd=0.01,
    )
    eval_result = EvalResult(
        instance_id="test-001",
        status=EvalStatus.PASSED,
        resolved=True,
    )
    summary = RunSummary(
        run_id="test-run",
        dataset_name="test",
        agent_name="test-agent",
        total_instances=1,
        resolved=1,
        results=[
            InstanceRunResult(
                instance=instance,
                agent_output=agent_output,
                eval_result=eval_result,
            )
        ],
    )

    d = summary.to_dict()
    assert d["run_id"] == "test-run"
    assert d["resolved"] == 1
    assert d["resolve_rate"] == 1.0
    assert len(d["results"]) == 1
    assert d["results"][0]["instance_id"] == "test-001"
    assert d["results"][0]["resolved"] is True
