"""Agent adapter registry."""

from __future__ import annotations

from codingeval.core.agent import AgentAdapter

_AGENTS: dict[str, type[AgentAdapter]] = {}


def register_agent(name: str, cls: type[AgentAdapter]) -> None:
    """Register an agent adapter class by name."""
    _AGENTS[name] = cls


def get_agent(name: str) -> AgentAdapter:
    """Instantiate and return an agent adapter by name."""
    if name not in _AGENTS:
        raise KeyError(f"Unknown agent: {name!r}. Available: {list(_AGENTS.keys())}")
    return _AGENTS[name]()


def list_agents() -> list[str]:
    """Return all registered agent names."""
    return list(_AGENTS.keys())
