"""Evaluator registry."""

from __future__ import annotations

from codingeval.core.evaluator import Evaluator

_EVALUATORS: dict[str, type[Evaluator]] = {}


def register_evaluator(name: str, cls: type[Evaluator]) -> None:
    """Register an evaluator class by name."""
    _EVALUATORS[name] = cls


def get_evaluator(name: str) -> Evaluator:
    """Instantiate and return an evaluator by name."""
    if name not in _EVALUATORS:
        raise KeyError(f"Unknown evaluator: {name!r}. Available: {list(_EVALUATORS.keys())}")
    return _EVALUATORS[name]()


def list_evaluators() -> list[str]:
    """Return all registered evaluator names."""
    return list(_EVALUATORS.keys())
