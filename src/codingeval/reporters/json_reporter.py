"""JSON file reporter."""

from __future__ import annotations

import json
import logging
from pathlib import Path

from codingeval.core.models import RunSummary
from codingeval.core.reporter import Reporter

logger = logging.getLogger(__name__)


class JSONReporter(Reporter):
    """Reporter that writes results to a JSON file."""

    @property
    def name(self) -> str:
        return "json"

    def report(self, summary: RunSummary, output_dir: str | None = None) -> None:
        if output_dir is None:
            output_dir = "results"

        output_path = Path(output_dir) / summary.run_id
        output_path.mkdir(parents=True, exist_ok=True)

        results_file = output_path / "results.json"
        data = summary.to_dict()

        with open(results_file, "w") as f:
            json.dump(data, f, indent=2)

        logger.info("Results written to %s", results_file)
