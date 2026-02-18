"""Abstract base class for evaluators."""

from __future__ import annotations

from abc import ABC, abstractmethod
from typing import TYPE_CHECKING

from codingeval.core.models import AgentOutput, EvalInstance, EvalResult

if TYPE_CHECKING:
    from codingeval.docker.workspace import Workspace


class Evaluator(ABC):
    """Base class for evaluation strategies."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Evaluator identifier."""

    @abstractmethod
    def evaluate(
        self,
        instance: EvalInstance,
        agent_output: AgentOutput,
        workspace: Workspace,
    ) -> EvalResult:
        """Evaluate an agent's output against the expected result."""
