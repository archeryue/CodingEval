"""Custom YAML-based dataset loader."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from codingeval.core.dataset import Dataset
from codingeval.core.models import EvalInstance

logger = logging.getLogger(__name__)


class CustomDataset(Dataset):
    """Dataset loaded from a YAML file."""

    def __init__(self, path: str | Path | None = None):
        self._path = Path(path) if path else None
        self._instances: list[EvalInstance] = []

    @property
    def name(self) -> str:
        return "custom"

    def load(self, **kwargs) -> None:
        """Load instances from the YAML file."""
        path = kwargs.get("path") or self._path
        if path is None:
            raise ValueError("No path provided for custom dataset")

        path = Path(path)
        if not path.exists():
            raise FileNotFoundError(f"Dataset file not found: {path}")

        with open(path) as f:
            data = yaml.safe_load(f)

        if not data or "instances" not in data:
            raise ValueError(f"Invalid dataset file: {path} (missing 'instances' key)")

        self._instances = []
        for item in data["instances"]:
            instance = EvalInstance(
                instance_id=item["instance_id"],
                dataset_name=data.get("dataset_name", "custom"),
                repo=item.get("repo", ""),
                base_commit=item.get("base_commit", ""),
                problem_statement=item.get("problem_statement", ""),
                hints_text=item.get("hints_text", ""),
                test_patch=item.get("test_patch", ""),
                gold_patch=item.get("gold_patch", ""),
                fail_to_pass=item.get("fail_to_pass", []),
                pass_to_pass=item.get("pass_to_pass", []),
                metadata=item.get("metadata", {}),
            )
            self._instances.append(instance)

        logger.info("Loaded %d instances from %s", len(self._instances), path)

    def get_instances(
        self,
        split: str = "test",
        instance_ids: list[str] | None = None,
        limit: int | None = None,
    ) -> list[EvalInstance]:
        """Return instances, optionally filtered."""
        if not self._instances:
            self.load()

        instances = self._instances
        if instance_ids:
            instances = [i for i in instances if i.instance_id in instance_ids]
        if limit:
            instances = instances[:limit]
        return instances
