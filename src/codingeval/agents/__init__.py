"""Agent plugins — auto-registers all built-in agents on import."""

from codingeval.agents.aider import AiderAgent
from codingeval.agents.claude_code import ClaudeCodeAgent
from codingeval.agents.registry import register_agent
from codingeval.agents.subprocess_agent import SubprocessAgent

register_agent("claude-code", ClaudeCodeAgent)
register_agent("aider", AiderAgent)
register_agent("subprocess", SubprocessAgent)
