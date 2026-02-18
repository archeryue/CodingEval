"""Dataset registry."""

from __future__ import annotations

from typing import Callable

from codingeval.core.dataset import Dataset

# Maps name -> factory callable that returns a Dataset instance.
_DATASETS: dict[str, Callable[[], Dataset]] = {}


def register_dataset(name: str, factory: Callable[[], Dataset]) -> None:
    """Register a dataset factory by name.

    ``factory`` can be a class (called with no args) or a zero-arg callable
    that returns a Dataset instance, e.g. ``lambda: SWEBenchDataset("swebench")``.
    """
    _DATASETS[name] = factory


def get_dataset(name: str) -> Dataset:
    """Instantiate and return a dataset by name."""
    if name not in _DATASETS:
        raise KeyError(f"Unknown dataset: {name!r}. Available: {list(_DATASETS.keys())}")
    return _DATASETS[name]()


def list_datasets() -> list[str]:
    """Return all registered dataset names."""
    return list(_DATASETS.keys())
