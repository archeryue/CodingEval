"""Regression dataset — loads bundled test cases from package directory."""

from __future__ import annotations

import logging
from pathlib import Path

import yaml

from codingeval.core.dataset import Dataset
from codingeval.core.models import EvalInstance

logger = logging.getLogger(__name__)

_PACKAGE_DIR = Path(__file__).parent


class RegressionDataset(Dataset):
    """Dataset backed by local git bundles for fast, offline regression testing."""

    def __init__(self):
        self._instances: list[EvalInstance] = []

    @property
    def name(self) -> str:
        return "regression"

    def load(self, **kwargs) -> None:
        """Load instances from cases.yaml, resolving bundle paths to absolute."""
        cases_path = _PACKAGE_DIR / "cases.yaml"
        if not cases_path.exists():
            raise FileNotFoundError(f"Regression cases file not found: {cases_path}")

        with open(cases_path) as f:
            data = yaml.safe_load(f)

        if not data or "instances" not in data:
            raise ValueError(f"Invalid cases file: {cases_path} (missing 'instances' key)")

        repos_dir = _PACKAGE_DIR / "repos"

        self._instances = []
        for item in data["instances"]:
            metadata = dict(item.get("metadata", {}))

            # Resolve bundle filename to absolute path
            bundle = metadata.get("bundle")
            if bundle:
                bundle_abs = str(repos_dir / bundle)
                metadata["repo_bundle_path"] = bundle_abs

            instance = EvalInstance(
                instance_id=item["instance_id"],
                dataset_name=data.get("dataset_name", "regression"),
                repo=item.get("repo", ""),
                base_commit=item.get("base_commit", ""),
                problem_statement=item.get("problem_statement", ""),
                hints_text=item.get("hints_text", ""),
                test_patch=item.get("test_patch", ""),
                gold_patch=item.get("gold_patch", ""),
                fail_to_pass=item.get("fail_to_pass", []),
                pass_to_pass=item.get("pass_to_pass", []),
                metadata=metadata,
            )
            self._instances.append(instance)

        logger.info("Loaded %d regression instances", len(self._instances))

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
