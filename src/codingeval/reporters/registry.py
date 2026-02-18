"""Reporter registry."""

from __future__ import annotations

from codingeval.core.reporter import Reporter

_REPORTERS: dict[str, type[Reporter]] = {}


def register_reporter(name: str, cls: type[Reporter]) -> None:
    """Register a reporter class by name."""
    _REPORTERS[name] = cls


def get_reporter(name: str) -> Reporter:
    """Instantiate and return a reporter by name."""
    if name not in _REPORTERS:
        raise KeyError(f"Unknown reporter: {name!r}. Available: {list(_REPORTERS.keys())}")
    return _REPORTERS[name]()


def list_reporters() -> list[str]:
    """Return all registered reporter names."""
    return list(_REPORTERS.keys())
