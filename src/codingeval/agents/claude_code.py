"""Claude Code agent adapter."""

from __future__ import annotations

import json
import logging
from typing import Any

from codingeval.core.agent import AgentAdapter
from codingeval.core.models import AgentOutput, EvalInstance, ExecutionMode

logger = logging.getLogger(__name__)


class ClaudeCodeAgent(AgentAdapter):
    """Adapter for the Claude Code CLI (claude command).

    Runs claude in non-interactive mode (--print) with JSON output.
    The agent edits files directly on the host; the patch is collected
    afterwards via `git diff`.
    """

    def __init__(self):
        self._timeout: int = 1800
        self._max_turns: int = 30
        self._model: str = ""
        self._max_budget_usd: float | None = None
        self._permission_mode: str = "bypassPermissions"
        self._allowed_tools: list[str] = []
        self._system_prompt: str = ""
        self._env: dict[str, str] = {}

    @property
    def name(self) -> str:
        return "claude-code"

    @property
    def execution_mode(self) -> ExecutionMode:
        return ExecutionMode.HOST

    def configure(self, options: dict[str, Any]) -> None:
        self._timeout = options.get("timeout", self._timeout)
        self._max_turns = options.get("max_turns", self._max_turns)
        self._model = options.get("model", self._model)
        self._max_budget_usd = options.get("max_budget_usd", self._max_budget_usd)
        self._permission_mode = options.get("permission_mode", self._permission_mode)
        self._allowed_tools = options.get("allowed_tools", self._allowed_tools)
        self._system_prompt = options.get("system_prompt", self._system_prompt)
        self._env = options.get("env", self._env)

    def build_command(self, instance: EvalInstance, workdir: str) -> list[str]:
        cmd = [
            "claude",
            "--print",
            "--output-format", "json",
            "--max-turns", str(self._max_turns),
            "--permission-mode", self._permission_mode,
        ]
        if self._model:
            cmd.extend(["--model", self._model])
        if self._max_budget_usd is not None:
            cmd.extend(["--max-budget-usd", str(self._max_budget_usd)])
        if self._allowed_tools:
            cmd.extend(["--allowedTools", ",".join(self._allowed_tools)])
        if self._system_prompt:
            cmd.extend(["--system-prompt", self._system_prompt])

        # Prompt is the last positional argument
        prompt = self.build_prompt(instance)
        cmd.append(prompt)
        return cmd

    def build_prompt(self, instance: EvalInstance) -> str:
        parts = [
            "Please fix the following issue in this repository.",
            "",
            "## Issue",
            instance.problem_statement,
        ]
        if instance.hints_text:
            parts.extend(["", "## Hints", instance.hints_text])
        parts.extend([
            "",
            "Make the minimal changes needed to fix the issue. "
            "Do not change any tests. Do not add unnecessary changes.",
        ])
        return "\n".join(parts)

    def parse_output(
        self, stdout: str, stderr: str, exit_code: int, duration: float
    ) -> AgentOutput:
        cost_usd = None
        tokens_used = None
        model_name = None
        result_text = stdout
        metadata: dict[str, Any] = {}

        # Parse the JSON output from `claude --print --output-format json`
        # Format: {"type":"result","subtype":"success","result":"...","total_cost_usd":..., "usage":{...}}
        try:
            data = json.loads(stdout)
            if isinstance(data, dict):
                cost_usd = data.get("total_cost_usd")
                result_text = data.get("result", "")
                metadata["session_id"] = data.get("session_id")
                metadata["num_turns"] = data.get("num_turns")
                metadata["duration_api_ms"] = data.get("duration_api_ms")
                metadata["stop_reason"] = data.get("stop_reason")

                # Extract token counts from usage
                usage = data.get("usage", {})
                if usage:
                    tokens_used = (
                        usage.get("input_tokens", 0)
                        + usage.get("output_tokens", 0)
                        + usage.get("cache_read_input_tokens", 0)
                    )

                # Extract model name from modelUsage keys
                model_usage = data.get("modelUsage", {})
                if model_usage:
                    model_name = next(iter(model_usage), None)

        except (json.JSONDecodeError, TypeError):
            logger.warning("Failed to parse Claude Code JSON output")

        return AgentOutput(
            instance_id="",
            agent_name=self.name,
            patch="",  # Patch is collected via git diff after agent runs
            exit_code=exit_code,
            stdout=result_text,
            stderr=stderr,
            duration_seconds=duration,
            cost_usd=cost_usd,
            tokens_used=tokens_used,
            model_name=model_name,
            metadata=metadata,
        )

    @property
    def prompt_via_stdin(self) -> bool:
        return False

    def get_environment(self) -> dict[str, str]:
        env = dict(self._env)
        # Unset CLAUDECODE to avoid nested-session check when the eval
        # framework itself is running inside a Claude Code session.
        env["CLAUDECODE"] = ""
        return env

    def get_timeout_seconds(self) -> int:
        return self._timeout
