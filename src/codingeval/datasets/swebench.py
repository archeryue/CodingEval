"""SWE-bench dataset loader."""

from __future__ import annotations

import json
import logging
from typing import Any

from codingeval.core.dataset import Dataset
from codingeval.core.models import EvalInstance

logger = logging.getLogger(__name__)

# HuggingFace dataset paths for SWE-bench variants
SWEBENCH_DATASETS = {
    "swebench": "princeton-nlp/SWE-bench",
    "swebench-lite": "princeton-nlp/SWE-bench_Lite",
    "swebench-verified": "princeton-nlp/SWE-bench_Verified",
}


def _parse_json_field(value: Any) -> list[str]:
    """Parse a field that might be a JSON string or already a list."""
    if isinstance(value, list):
        return value
    if isinstance(value, str):
        try:
            parsed = json.loads(value)
            if isinstance(parsed, list):
                return parsed
        except (json.JSONDecodeError, TypeError):
            pass
        return [value] if value else []
    return []


class SWEBenchDataset(Dataset):
    """SWE-bench dataset loaded from HuggingFace."""

    def __init__(self, variant: str = "swebench-lite"):
        self._variant = variant
        self._data: Any | None = None

    @property
    def name(self) -> str:
        return self._variant

    def load(self, **kwargs) -> None:
        """Load the dataset from HuggingFace."""
        from datasets import load_dataset

        hf_path = SWEBENCH_DATASETS.get(self._variant, self._variant)
        logger.info("Loading dataset from %s", hf_path)
        self._data = load_dataset(hf_path)

    def get_instances(
        self,
        split: str = "test",
        instance_ids: list[str] | None = None,
        limit: int | None = None,
    ) -> list[EvalInstance]:
        """Return evaluation instances from the loaded dataset."""
        if self._data is None:
            self.load()

        assert self._data is not None
        if split not in self._data:
            available = list(self._data.keys())
            raise ValueError(f"Split {split!r} not found. Available: {available}")

        data_split = self._data[split]
        instances: list[EvalInstance] = []

        for row in data_split:
            inst_id = row["instance_id"]

            if instance_ids and inst_id not in instance_ids:
                continue

            instance = EvalInstance(
                instance_id=inst_id,
                dataset_name=self._variant,
                repo=row.get("repo", ""),
                base_commit=row.get("base_commit", ""),
                problem_statement=row.get("problem_statement", ""),
                hints_text=row.get("hints_text", ""),
                test_patch=row.get("test_patch", ""),
                gold_patch=row.get("patch", ""),
                fail_to_pass=_parse_json_field(row.get("FAIL_TO_PASS", [])),
                pass_to_pass=_parse_json_field(row.get("PASS_TO_PASS", [])),
                metadata={
                    "created_at": row.get("created_at", ""),
                    "version": row.get("version", ""),
                    "environment_setup_commit": row.get("environment_setup_commit", ""),
                },
            )
            instances.append(instance)

            if limit and len(instances) >= limit:
                break

        logger.info("Loaded %d instances from %s/%s", len(instances), self._variant, split)
        return instances
