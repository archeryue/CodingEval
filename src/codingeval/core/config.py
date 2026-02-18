"""Configuration loading and management."""

from __future__ import annotations

from dataclasses import dataclass, field
from pathlib import Path
from typing import Any

import yaml


@dataclass
class AgentConfig:
    """Configuration for an agent adapter."""

    name: str
    command: str = ""
    timeout: int = 300
    env: dict[str, str] = field(default_factory=dict)
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class DatasetConfig:
    """Configuration for a dataset."""

    name: str
    split: str = "test"
    instance_ids: list[str] = field(default_factory=list)
    limit: int | None = None
    options: dict[str, Any] = field(default_factory=dict)


@dataclass
class DockerConfig:
    """Configuration for Docker."""

    enabled: bool = True
    base_image: str = "codingeval-base:latest"
    dockerfile: str = "docker/base/Dockerfile"
    memory_limit: str = "4g"
    cpu_count: int = 2
    network_enabled: bool = True
    cleanup: bool = True


@dataclass
class RunConfig:
    """Top-level run configuration."""

    dataset: DatasetConfig = field(default_factory=lambda: DatasetConfig(name="swebench"))
    agent: AgentConfig = field(default_factory=lambda: AgentConfig(name="claude-code"))
    docker: DockerConfig = field(default_factory=DockerConfig)
    evaluator: str = "swebench"
    reporter: str = "console"
    results_dir: str = "results"
    max_workers: int = 1
    log_level: str = "INFO"

    @classmethod
    def from_yaml(cls, path: str | Path) -> RunConfig:
        """Load configuration from a YAML file."""
        path = Path(path)
        with open(path) as f:
            data = yaml.safe_load(f) or {}
        return cls.from_dict(data)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> RunConfig:
        """Create configuration from a dictionary."""
        config = cls()

        if "dataset" in data:
            ds = data["dataset"]
            config.dataset = DatasetConfig(
                name=ds.get("name", "swebench"),
                split=ds.get("split", "test"),
                instance_ids=ds.get("instance_ids", []),
                limit=ds.get("limit"),
                options=ds.get("options", {}),
            )

        if "agent" in data:
            ag = data["agent"]
            config.agent = AgentConfig(
                name=ag.get("name", "claude-code"),
                command=ag.get("command", ""),
                timeout=ag.get("timeout", 300),
                env=ag.get("env", {}),
                options=ag.get("options", {}),
            )

        if "docker" in data:
            dk = data["docker"]
            config.docker = DockerConfig(
                enabled=dk.get("enabled", True),
                base_image=dk.get("base_image", "codingeval-base:latest"),
                dockerfile=dk.get("dockerfile", "docker/base/Dockerfile"),
                memory_limit=dk.get("memory_limit", "4g"),
                cpu_count=dk.get("cpu_count", 2),
                network_enabled=dk.get("network_enabled", True),
                cleanup=dk.get("cleanup", True),
            )

        config.evaluator = data.get("evaluator", "swebench")
        config.reporter = data.get("reporter", "console")
        config.results_dir = data.get("results_dir", "results")
        config.max_workers = data.get("max_workers", 1)
        config.log_level = data.get("log_level", "INFO")

        return config

    def merge_overrides(
        self,
        dataset_name: str | None = None,
        agent_name: str | None = None,
        limit: int | None = None,
        instance_ids: list[str] | None = None,
        max_workers: int | None = None,
    ) -> None:
        """Apply CLI overrides to the config."""
        if dataset_name:
            self.dataset.name = dataset_name
        if agent_name:
            self.agent.name = agent_name
        if limit is not None:
            self.dataset.limit = limit
        if instance_ids:
            self.dataset.instance_ids = instance_ids
        if max_workers is not None:
            self.max_workers = max_workers
