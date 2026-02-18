"""Tests for configuration loading."""

import tempfile
from pathlib import Path

from codingeval.core.config import AgentConfig, DatasetConfig, DockerConfig, RunConfig


def test_run_config_defaults():
    config = RunConfig()
    assert config.dataset.name == "swebench"
    assert config.agent.name == "claude-code"
    assert config.evaluator == "swebench"
    assert config.reporter == "console"
    assert config.max_workers == 1


def test_run_config_from_dict():
    data = {
        "dataset": {"name": "swebench-lite", "split": "dev", "limit": 5},
        "agent": {"name": "aider", "timeout": 120},
        "evaluator": "swebench",
        "max_workers": 4,
    }
    config = RunConfig.from_dict(data)
    assert config.dataset.name == "swebench-lite"
    assert config.dataset.split == "dev"
    assert config.dataset.limit == 5
    assert config.agent.name == "aider"
    assert config.agent.timeout == 120
    assert config.max_workers == 4


def test_run_config_from_yaml():
    yaml_content = """
dataset:
  name: swebench-lite
  split: test
  limit: 10

agent:
  name: claude-code
  timeout: 300

max_workers: 2
"""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
        f.write(yaml_content)
        f.flush()

        config = RunConfig.from_yaml(f.name)

    assert config.dataset.name == "swebench-lite"
    assert config.dataset.limit == 10
    assert config.agent.name == "claude-code"
    assert config.max_workers == 2


def test_merge_overrides():
    config = RunConfig()
    config.merge_overrides(
        dataset_name="custom",
        agent_name="aider",
        limit=5,
        instance_ids=["id-001", "id-002"],
        max_workers=8,
    )
    assert config.dataset.name == "custom"
    assert config.agent.name == "aider"
    assert config.dataset.limit == 5
    assert config.dataset.instance_ids == ["id-001", "id-002"]
    assert config.max_workers == 8


def test_merge_overrides_none_values():
    config = RunConfig()
    original_dataset = config.dataset.name
    original_agent = config.agent.name

    config.merge_overrides()

    assert config.dataset.name == original_dataset
    assert config.agent.name == original_agent


def test_docker_config_defaults():
    config = DockerConfig()
    assert config.base_image == "codingeval-base:latest"
    assert config.memory_limit == "4g"
    assert config.cpu_count == 2
    assert config.network_enabled is True
    assert config.cleanup is True
