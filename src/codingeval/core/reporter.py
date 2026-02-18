"""Abstract base class for reporters."""

from __future__ import annotations

from abc import ABC, abstractmethod

from codingeval.core.models import RunSummary


class Reporter(ABC):
    """Base class for result reporters."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Reporter identifier."""

    @abstractmethod
    def report(self, summary: RunSummary, output_dir: str | None = None) -> None:
        """Generate a report from a run summary."""
