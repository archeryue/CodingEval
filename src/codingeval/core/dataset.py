"""Abstract base class for datasets."""

from __future__ import annotations

from abc import ABC, abstractmethod

from codingeval.core.models import EvalInstance


class Dataset(ABC):
    """Base class for evaluation datasets."""

    @property
    @abstractmethod
    def name(self) -> str:
        """Dataset identifier."""

    @abstractmethod
    def load(self, **kwargs) -> None:
        """Load the dataset from its source."""

    @abstractmethod
    def get_instances(
        self,
        split: str = "test",
        instance_ids: list[str] | None = None,
        limit: int | None = None,
    ) -> list[EvalInstance]:
        """Return evaluation instances, optionally filtered."""
