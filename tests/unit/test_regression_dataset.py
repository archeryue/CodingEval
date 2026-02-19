"""Tests for the regression dataset and evaluator."""

import subprocess
import tempfile
from pathlib import Path
from unittest.mock import patch

import pytest

from codingeval.regression.dataset import RegressionDataset


def test_load_regression_dataset():
    """Should load all 10 regression instances."""
    dataset = RegressionDataset()
    dataset.load()
    instances = dataset.get_instances()
    assert len(instances) == 10


def test_dataset_name():
    dataset = RegressionDataset()
    assert dataset.name == "regression"


def test_instance_ids():
    """Every instance should have a regression-XXX prefix."""
    dataset = RegressionDataset()
    dataset.load()
    for inst in dataset.get_instances():
        assert inst.instance_id.startswith("regression-"), inst.instance_id


def test_bundle_paths_resolved():
    """All instances should have absolute repo_bundle_path in metadata."""
    dataset = RegressionDataset()
    dataset.load()
    for inst in dataset.get_instances():
        bundle_path = inst.metadata.get("repo_bundle_path")
        assert bundle_path is not None, f"{inst.instance_id} missing repo_bundle_path"
        assert Path(bundle_path).is_absolute(), f"{inst.instance_id} path not absolute"


def test_bundles_exist():
    """All referenced bundles should exist on disk."""
    dataset = RegressionDataset()
    dataset.load()
    for inst in dataset.get_instances():
        bundle_path = Path(inst.metadata["repo_bundle_path"])
        assert bundle_path.exists(), f"Missing bundle: {bundle_path}"


def test_filter_by_instance_id():
    dataset = RegressionDataset()
    dataset.load()
    instances = dataset.get_instances(
        instance_ids=["regression-001-fix-single-function"]
    )
    assert len(instances) == 1
    assert instances[0].instance_id == "regression-001-fix-single-function"


def test_limit():
    dataset = RegressionDataset()
    dataset.load()
    instances = dataset.get_instances(limit=3)
    assert len(instances) == 3


def test_fail_to_pass_populated():
    """Every instance should have at least one fail_to_pass test."""
    dataset = RegressionDataset()
    dataset.load()
    for inst in dataset.get_instances():
        assert len(inst.fail_to_pass) > 0, f"{inst.instance_id} has no fail_to_pass"


def test_problem_statement_nonempty():
    """Every instance should have a non-empty problem statement."""
    dataset = RegressionDataset()
    dataset.load()
    for inst in dataset.get_instances():
        assert inst.problem_statement.strip(), f"{inst.instance_id} has empty problem_statement"


def test_bundles_are_valid_git_bundles():
    """Each bundle should be cloneable."""
    dataset = RegressionDataset()
    dataset.load()
    for inst in dataset.get_instances():
        bundle_path = inst.metadata["repo_bundle_path"]
        result = subprocess.run(
            ["git", "bundle", "verify", bundle_path],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, (
            f"Invalid bundle for {inst.instance_id}: {result.stderr}"
        )


def test_clone_from_bundle():
    """Should be able to clone a repo from a bundle."""
    dataset = RegressionDataset()
    dataset.load()
    inst = dataset.get_instances(instance_ids=["regression-001-fix-single-function"])[0]
    bundle_path = inst.metadata["repo_bundle_path"]

    with tempfile.TemporaryDirectory() as tmpdir:
        result = subprocess.run(
            ["git", "clone", bundle_path, tmpdir + "/repo"],
            capture_output=True, text=True,
        )
        assert result.returncode == 0, f"Clone failed: {result.stderr}"
        assert Path(tmpdir, "repo", "calculator.py").exists()
        assert Path(tmpdir, "repo", "test_calculator.py").exists()


def test_dataset_name_field():
    """Instances should have dataset_name='regression'."""
    dataset = RegressionDataset()
    dataset.load()
    for inst in dataset.get_instances():
        assert inst.dataset_name == "regression"
