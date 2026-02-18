"""Aider agent adapter."""

from __future__ import annotations

import logging
from typing import Any

from codingeval.core.agent import AgentAdapter
from codingeval.core.models import AgentOutput, EvalInstance, ExecutionMode

logger = logging.getLogger(__name__)


class AiderAgent(AgentAdapter):
    """Adapter for Aider CLI."""

    def __init__(self):
        self._timeout: int = 600
        self._model: str = ""
        self._env: dict[str, str] = {}

    @property
    def name(self) -> str:
        return "aider"

    @property
    def execution_mode(self) -> ExecutionMode:
        return ExecutionMode.HOST

    def configure(self, options: dict[str, Any]) -> None:
        self._timeout = options.get("timeout", self._timeout)
        self._model = options.get("model", self._model)
        self._env = options.get("env", self._env)

    def build_command(self, instance: EvalInstance, workdir: str) -> list[str]:
        cmd = [
            "aider",
            "--yes-always",
            "--no-git",
            "--no-auto-commits",
        ]
        if self._model:
            cmd.extend(["--model", self._model])
        cmd.extend(["--message"])
        return cmd

    def build_prompt(self, instance: EvalInstance) -> str:
        return (
            f"Fix the following issue:\n\n"
            f"{instance.problem_statement}\n\n"
            f"Hints: {instance.hints_text}"
        )

    def parse_output(
        self, stdout: str, stderr: str, exit_code: int, duration: float
    ) -> AgentOutput:
        return AgentOutput(
            instance_id="",
            agent_name=self.name,
            patch="",  # Collected via git diff
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=duration,
        )

    def get_environment(self) -> dict[str, str]:
        return dict(self._env)

    def get_timeout_seconds(self) -> int:
        return self._timeout
