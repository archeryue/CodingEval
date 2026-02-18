"""Tests for custom YAML dataset."""

import tempfile
from pathlib import Path

import pytest

from codingeval.datasets.custom import CustomDataset


def _write_yaml(content: str) -> str:
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    f.write(content)
    f.flush()
    f.close()
    return f.name


def test_load_custom_dataset():
    yaml_content = """
dataset_name: test-dataset
instances:
  - instance_id: test-001
    repo: owner/repo
    base_commit: abc123
    problem_statement: Fix the bug
    fail_to_pass:
      - test_foo
  - instance_id: test-002
    repo: owner/repo2
    base_commit: def456
    problem_statement: Fix another bug
"""
    path = _write_yaml(yaml_content)
    dataset = CustomDataset(path)
    dataset.load()
    instances = dataset.get_instances()
    assert len(instances) == 2
    assert instances[0].instance_id == "test-001"
    assert instances[0].dataset_name == "test-dataset"
    assert instances[0].fail_to_pass == ["test_foo"]


def test_filter_by_instance_ids():
    yaml_content = """
dataset_name: test
instances:
  - instance_id: a
    problem_statement: Fix A
  - instance_id: b
    problem_statement: Fix B
  - instance_id: c
    problem_statement: Fix C
"""
    path = _write_yaml(yaml_content)
    dataset = CustomDataset(path)
    dataset.load()
    instances = dataset.get_instances(instance_ids=["a", "c"])
    assert len(instances) == 2
    assert {i.instance_id for i in instances} == {"a", "c"}


def test_limit():
    yaml_content = """
dataset_name: test
instances:
  - instance_id: a
    problem_statement: A
  - instance_id: b
    problem_statement: B
  - instance_id: c
    problem_statement: C
"""
    path = _write_yaml(yaml_content)
    dataset = CustomDataset(path)
    dataset.load()
    instances = dataset.get_instances(limit=2)
    assert len(instances) == 2


def test_missing_file():
    dataset = CustomDataset("/nonexistent/path.yaml")
    with pytest.raises(FileNotFoundError):
        dataset.load()


def test_invalid_format():
    yaml_content = "just_a_string: true\n"
    path = _write_yaml(yaml_content)
    dataset = CustomDataset(path)
    with pytest.raises(ValueError, match="missing 'instances' key"):
        dataset.load()
