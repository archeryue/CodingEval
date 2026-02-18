"""Tests for agent adapters."""

import json

from codingeval.agents.claude_code import ClaudeCodeAgent
from codingeval.agents.subprocess_agent import SubprocessAgent
from codingeval.core.models import EvalInstance, ExecutionMode


def _make_instance() -> EvalInstance:
    return EvalInstance(
        instance_id="test-001",
        dataset_name="test",
        repo="owner/repo",
        base_commit="abc123",
        problem_statement="Fix the bug",
        hints_text="Check main.py",
    )


def test_claude_code_name():
    agent = ClaudeCodeAgent()
    assert agent.name == "claude-code"


def test_claude_code_execution_mode():
    agent = ClaudeCodeAgent()
    assert agent.execution_mode == ExecutionMode.HOST


def test_claude_code_prompt_not_via_stdin():
    agent = ClaudeCodeAgent()
    assert agent.prompt_via_stdin is False


def test_claude_code_build_command():
    agent = ClaudeCodeAgent()
    instance = _make_instance()
    cmd = agent.build_command(instance, "/tmp/workspace")
    assert cmd[0] == "claude"
    assert "--print" in cmd
    assert "--output-format" in cmd
    assert "--permission-mode" in cmd
    # Last arg should be the prompt (contains issue text)
    assert "Fix the bug" in cmd[-1]


def test_claude_code_build_command_with_model():
    agent = ClaudeCodeAgent()
    agent.configure({"model": "sonnet"})
    cmd = agent.build_command(_make_instance(), "/tmp/workspace")
    assert "--model" in cmd
    idx = cmd.index("--model")
    assert cmd[idx + 1] == "sonnet"


def test_claude_code_build_prompt():
    agent = ClaudeCodeAgent()
    instance = _make_instance()
    prompt = agent.build_prompt(instance)
    assert "Fix the bug" in prompt
    assert "Check main.py" in prompt


def test_claude_code_build_prompt_no_hints():
    instance = EvalInstance(
        instance_id="test-002",
        dataset_name="test",
        repo="owner/repo",
        base_commit="abc123",
        problem_statement="Fix the bug",
    )
    agent = ClaudeCodeAgent()
    prompt = agent.build_prompt(instance)
    assert "Fix the bug" in prompt
    assert "Hints" not in prompt


def test_claude_code_parse_output_plain():
    agent = ClaudeCodeAgent()
    output = agent.parse_output("some output", "", 0, 10.0)
    assert output.agent_name == "claude-code"
    assert output.exit_code == 0
    assert output.duration_seconds == 10.0


def test_claude_code_parse_output_json():
    agent = ClaudeCodeAgent()
    json_output = json.dumps({
        "type": "result",
        "subtype": "success",
        "result": "Fixed the bug",
        "total_cost_usd": 0.05,
        "num_turns": 3,
        "session_id": "abc-123",
        "usage": {"input_tokens": 500, "output_tokens": 200, "cache_read_input_tokens": 300},
        "modelUsage": {"claude-opus-4-6": {"inputTokens": 500, "outputTokens": 200}},
    })
    output = agent.parse_output(json_output, "", 0, 10.0)
    assert output.cost_usd == 0.05
    assert output.tokens_used == 1000  # 500 + 200 + 300
    assert output.model_name == "claude-opus-4-6"
    assert output.stdout == "Fixed the bug"
    assert output.metadata["session_id"] == "abc-123"
    assert output.metadata["num_turns"] == 3


def test_claude_code_configure():
    agent = ClaudeCodeAgent()
    agent.configure({"timeout": 900, "model": "opus", "max_turns": 50})
    assert agent.get_timeout_seconds() == 900
    assert agent._model == "opus"
    assert agent._max_turns == 50


def test_claude_code_env_unsets_claudecode():
    agent = ClaudeCodeAgent()
    env = agent.get_environment()
    assert env["CLAUDECODE"] == ""


def test_subprocess_agent_name():
    agent = SubprocessAgent()
    assert agent.name == "subprocess"


def test_subprocess_agent_prompt_via_stdin():
    agent = SubprocessAgent()
    assert agent.prompt_via_stdin is True


def test_subprocess_agent_configure():
    agent = SubprocessAgent()
    agent.configure({
        "command_template": "my-agent --dir {workdir}",
        "timeout": 120,
        "env": {"MY_VAR": "value"},
    })
    assert agent.get_timeout_seconds() == 120
    assert agent.get_environment() == {"MY_VAR": "value"}


def test_subprocess_extract_patch():
    agent = SubprocessAgent()
    output = "some preamble\ndiff --git a/file.py b/file.py\n--- a/file.py\n+++ b/file.py\n@@ -1 +1 @@\n-old\n+new"
    patch = agent._extract_patch(output)
    assert patch.startswith("diff --git")
    assert "+new" in patch
