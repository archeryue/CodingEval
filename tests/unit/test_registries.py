"""Tests for plugin registries."""

import codingeval.agents  # noqa: F401
import codingeval.datasets  # noqa: F401
import codingeval.evaluators  # noqa: F401
import codingeval.reporters  # noqa: F401
from codingeval.agents.registry import get_agent, list_agents
from codingeval.datasets.registry import get_dataset, list_datasets
from codingeval.evaluators.registry import get_evaluator, list_evaluators
from codingeval.reporters.registry import get_reporter, list_reporters


def test_list_datasets():
    names = list_datasets()
    assert "swebench" in names
    assert "swebench-lite" in names
    assert "custom" in names


def test_list_agents():
    names = list_agents()
    assert "claude-code" in names
    assert "aider" in names
    assert "subprocess" in names


def test_list_evaluators():
    names = list_evaluators()
    assert "swebench" in names


def test_list_reporters():
    names = list_reporters()
    assert "console" in names
    assert "json" in names


def test_get_dataset():
    dataset = get_dataset("custom")
    assert dataset.name == "custom"


def test_get_agent():
    agent = get_agent("claude-code")
    assert agent.name == "claude-code"


def test_get_evaluator():
    evaluator = get_evaluator("swebench")
    assert evaluator.name == "swebench"


def test_get_reporter():
    reporter = get_reporter("console")
    assert reporter.name == "console"


def test_get_unknown_dataset():
    import pytest

    with pytest.raises(KeyError, match="Unknown dataset"):
        get_dataset("nonexistent")


def test_get_unknown_agent():
    import pytest

    with pytest.raises(KeyError, match="Unknown agent"):
        get_agent("nonexistent")
