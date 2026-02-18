"""Generic subprocess-based agent adapter."""

from __future__ import annotations

import logging
from typing import Any

from codingeval.core.agent import AgentAdapter
from codingeval.core.models import AgentOutput, EvalInstance, ExecutionMode

logger = logging.getLogger(__name__)


class SubprocessAgent(AgentAdapter):
    """Generic agent that runs as a subprocess with a configurable command template."""

    def __init__(self):
        self._command_template: str = ""
        self._prompt_template: str = "{problem_statement}"
        self._timeout: int = 300
        self._env: dict[str, str] = {}

    @property
    def name(self) -> str:
        return "subprocess"

    @property
    def execution_mode(self) -> ExecutionMode:
        return ExecutionMode.HOST

    def configure(self, options: dict[str, Any]) -> None:
        self._command_template = options.get("command_template", self._command_template)
        self._prompt_template = options.get("prompt_template", self._prompt_template)
        self._timeout = options.get("timeout", self._timeout)
        self._env = options.get("env", self._env)

    def build_command(self, instance: EvalInstance, workdir: str) -> list[str]:
        cmd = self._command_template.format(
            workdir=workdir,
            instance_id=instance.instance_id,
            repo=instance.repo,
        )
        return cmd.split()

    def build_prompt(self, instance: EvalInstance) -> str:
        return self._prompt_template.format(
            problem_statement=instance.problem_statement,
            hints_text=instance.hints_text,
            repo=instance.repo,
            instance_id=instance.instance_id,
        )

    def parse_output(
        self, stdout: str, stderr: str, exit_code: int, duration: float
    ) -> AgentOutput:
        # Try to extract a diff/patch from stdout
        patch = self._extract_patch(stdout)
        return AgentOutput(
            instance_id="",
            agent_name=self.name,
            patch=patch,
            exit_code=exit_code,
            stdout=stdout,
            stderr=stderr,
            duration_seconds=duration,
        )

    def _extract_patch(self, output: str) -> str:
        """Extract a git diff/patch from the output."""
        lines = output.split("\n")
        patch_lines: list[str] = []
        in_patch = False
        for line in lines:
            if line.startswith("diff --git"):
                in_patch = True
            if in_patch:
                patch_lines.append(line)
        return "\n".join(patch_lines) if patch_lines else ""

    def get_environment(self) -> dict[str, str]:
        return dict(self._env)

    def get_timeout_seconds(self) -> int:
        return self._timeout
