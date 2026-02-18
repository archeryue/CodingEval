"""Core data models for the evaluation framework."""

from __future__ import annotations

from dataclasses import dataclass, field
from datetime import datetime
from enum import Enum
from typing import Any


class ExecutionMode(str, Enum):
    """How an agent executes relative to the workspace."""

    HOST = "host"
    CONTAINER = "container"


class EvalStatus(str, Enum):
    """Status of an evaluation result."""

    PASSED = "passed"
    FAILED = "failed"
    ERROR = "error"
    TIMEOUT = "timeout"
    SKIPPED = "skipped"


@dataclass(frozen=True)
class EvalInstance:
    """A single evaluation instance from a dataset."""

    instance_id: str
    dataset_name: str
    repo: str
    base_commit: str
    problem_statement: str
    hints_text: str = ""
    test_patch: str = ""
    gold_patch: str = ""
    fail_to_pass: list[str] = field(default_factory=list)
    pass_to_pass: list[str] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class AgentOutput:
    """Output produced by an agent for a single instance."""

    instance_id: str
    agent_name: str
    patch: str = ""
    exit_code: int = -1
    stdout: str = ""
    stderr: str = ""
    duration_seconds: float = 0.0
    cost_usd: float | None = None
    tokens_used: int | None = None
    model_name: str | None = None
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class SingleTestResult:
    """Result of running a single test."""

    test_name: str
    passed: bool
    output: str = ""


@dataclass
class EvalResult:
    """Result of evaluating an agent's output for a single instance."""

    instance_id: str
    status: EvalStatus
    fail_to_pass_results: list[SingleTestResult] = field(default_factory=list)
    pass_to_pass_results: list[SingleTestResult] = field(default_factory=list)
    resolved: bool = False
    error_message: str = ""
    duration_seconds: float = 0.0
    metadata: dict[str, Any] = field(default_factory=dict)


@dataclass
class InstanceRunResult:
    """Complete result for a single instance: agent output + eval result."""

    instance: EvalInstance
    agent_output: AgentOutput | None = None
    eval_result: EvalResult | None = None


@dataclass
class RunSummary:
    """Summary of a full evaluation run."""

    run_id: str
    dataset_name: str
    agent_name: str
    started_at: datetime = field(default_factory=datetime.now)
    completed_at: datetime | None = None
    total_instances: int = 0
    resolved: int = 0
    failed: int = 0
    errors: int = 0
    timeouts: int = 0
    skipped: int = 0
    results: list[InstanceRunResult] = field(default_factory=list)
    metadata: dict[str, Any] = field(default_factory=dict)

    @property
    def resolve_rate(self) -> float:
        if self.total_instances == 0:
            return 0.0
        return self.resolved / self.total_instances

    def to_dict(self) -> dict[str, Any]:
        return {
            "run_id": self.run_id,
            "dataset_name": self.dataset_name,
            "agent_name": self.agent_name,
            "started_at": self.started_at.isoformat(),
            "completed_at": self.completed_at.isoformat() if self.completed_at else None,
            "total_instances": self.total_instances,
            "resolved": self.resolved,
            "failed": self.failed,
            "errors": self.errors,
            "timeouts": self.timeouts,
            "skipped": self.skipped,
            "resolve_rate": self.resolve_rate,
            "results": [
                {
                    "instance_id": r.instance.instance_id,
                    "status": r.eval_result.status.value if r.eval_result else "error",
                    "resolved": r.eval_result.resolved if r.eval_result else False,
                    "agent_duration": r.agent_output.duration_seconds
                    if r.agent_output
                    else None,
                    "eval_duration": r.eval_result.duration_seconds
                    if r.eval_result
                    else None,
                    "cost_usd": r.agent_output.cost_usd if r.agent_output else None,
                    "error_message": r.eval_result.error_message
                    if r.eval_result
                    else "",
                }
                for r in self.results
            ],
            "metadata": self.metadata,
        }
