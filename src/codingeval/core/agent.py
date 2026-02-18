"""Abstract base class for agent adapters."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import Any

from codingeval.core.models import AgentOutput, EvalInstance, ExecutionMode


class AgentAdapter(ABC):
    """Base class for CLI agent adapters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Agent identifier."""

    @property
    @abstractmethod
    def execution_mode(self) -> ExecutionMode:
        """Whether the agent runs on the host or inside a container."""

    @abstractmethod
    def build_command(self, instance: EvalInstance, workdir: str) -> list[str]:
        """Build the command to invoke the agent."""

    @abstractmethod
    def build_prompt(self, instance: EvalInstance) -> str:
        """Build the prompt to send to the agent."""

    @abstractmethod
    def parse_output(
        self, stdout: str, stderr: str, exit_code: int, duration: float
    ) -> AgentOutput:
        """Parse the agent's raw output into an AgentOutput."""

    def get_environment(self) -> dict[str, str]:
        """Return environment variables for agent execution."""
        return {}

    def get_timeout_seconds(self) -> int:
        """Return timeout in seconds for agent execution."""
        return 300

    @property
    def prompt_via_stdin(self) -> bool:
        """Whether the prompt should be piped via stdin.

        If False, the prompt is expected to be included in the command
        (e.g. as a positional argument). Override in subclasses.
        """
        return True

    def configure(self, options: dict[str, Any]) -> None:
        """Apply configuration options to the agent."""
