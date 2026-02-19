# Architecture

## Overview

CodingEval is a plugin-based evaluation framework built around four abstractions: **Datasets**, **Agents**, **Evaluators**, and **Reporters**. A central **Runner** orchestrates the pipeline, and **Workspaces** provide isolated environments for each evaluation instance.

```
┌──────────────────────────────────────────────────┐
│                  CLI (click)                      │
│           codingeval run / list / report          │
└──────────────────┬───────────────────────────────┘
                   │
          ┌────────▼────────┐
          │   RunConfig     │  ← YAML + CLI overrides
          └────────┬────────┘
                   │
    ┌──────────────▼──────────────┐
    │         Registries          │
    │  Dataset | Agent | Evaluator│ Reporter
    └──────────────┬──────────────┘
                   │
          ┌────────▼────────┐
          │     Runner      │  ← Orchestrates everything
          └────────┬────────┘
                   │
     ┌─────────────┼─────────────┐
     │             │             │
 ┌───▼───┐   ┌────▼────┐   ┌───▼────┐
 │Dataset│   │  Agent  │   │Evaluator│
 └───┬───┘   └────┬────┘   └───┬────┘
     │            │             │
     │       ┌────▼────┐        │
     │       │Workspace│←───────┘
     │       └─────────┘
     │
 ┌───▼────┐
 │Reporter│
 └────────┘
```

## Directory Structure

```
src/codingeval/
├── cli/                    # Command-line interface
│   ├── main.py             # Entry point (click group)
│   ├── run.py              # `codingeval run` command
│   ├── list_cmd.py         # `codingeval list` command
│   └── report.py           # `codingeval report` command
│
├── core/                   # Framework core
│   ├── models.py           # Data models (EvalInstance, AgentOutput, etc.)
│   ├── config.py           # Configuration (RunConfig, AgentConfig, etc.)
│   ├── runner.py           # Pipeline orchestrator
│   ├── agent.py            # AgentAdapter ABC
│   ├── dataset.py          # Dataset ABC
│   ├── evaluator.py        # Evaluator ABC
│   └── reporter.py         # Reporter ABC
│
├── agents/                 # Agent implementations
│   ├── registry.py         # Agent plugin registry
│   ├── claude_code.py      # Claude Code CLI adapter
│   ├── aider.py            # Aider CLI adapter
│   └── subprocess_agent.py # Generic subprocess agent
│
├── datasets/               # Dataset implementations
│   ├── registry.py         # Dataset plugin registry
│   ├── swebench.py         # SWE-bench (HuggingFace)
│   └── custom.py           # Custom YAML datasets
│
├── evaluators/             # Evaluator implementations
│   ├── registry.py         # Evaluator plugin registry
│   └── swebench.py         # SWE-bench test runner
│
├── reporters/              # Reporter implementations
│   ├── registry.py         # Reporter plugin registry
│   ├── console.py          # Rich console output
│   └── json_reporter.py    # JSON file output
│
├── docker/                 # Workspace management
│   ├── manager.py          # Docker client wrapper
│   ├── workspace.py        # Docker-based workspace
│   └── host_workspace.py   # Host-based workspace (no Docker)
│
└── utils/                  # Utilities
    ├── patch.py            # Patch extraction/validation
    ├── git.py              # Git operations
    └── logging.py          # Logging setup
```

## Core Data Models

Defined in `core/models.py`:

```
EvalInstance (frozen)          AgentOutput
├── instance_id               ├── instance_id
├── repo                      ├── agent_name
├── base_commit               ├── patch (git diff)
├── problem_statement         ├── exit_code
├── hints_text                ├── stdout / stderr
├── test_patch                ├── duration_seconds
├── gold_patch                ├── cost_usd
├── fail_to_pass[]            ├── tokens_used
├── pass_to_pass[]            ├── model_name
└── metadata{}                └── metadata{}

EvalResult                    RunSummary
├── instance_id               ├── run_id
├── status (EvalStatus)       ├── dataset_name / agent_name
├── fail_to_pass_results[]    ├── total / resolved / failed
├── pass_to_pass_results[]    ├── errors / timeouts / skipped
├── resolved (bool)           ├── results[]
├── error_message             ├── resolve_rate (property)
└── duration_seconds          └── to_dict()
```

## Plugin System

Each plugin type uses a **registry pattern**. Plugins self-register on import via their `__init__.py`:

```python
# agents/__init__.py
from codingeval.agents.registry import register_agent
from codingeval.agents.claude_code import ClaudeCodeAgent

register_agent("claude-code", ClaudeCodeAgent)
```

**Adding a new agent:**
1. Create `agents/my_agent.py` implementing `AgentAdapter`
2. Register it in `agents/__init__.py`

The same pattern applies for datasets, evaluators, and reporters.

## Agent Adapter Interface

```python
class AgentAdapter(ABC):
    name: str                              # e.g., "claude-code"
    execution_mode: ExecutionMode          # HOST or CONTAINER

    def build_command(instance, workdir) -> list[str]
    def build_prompt(instance) -> str
    def parse_output(stdout, stderr, exit_code, duration) -> AgentOutput
    def configure(options) -> None
    def get_environment() -> dict[str, str]
    def get_timeout_seconds() -> int
```

**HOST mode**: Agent runs on the host filesystem, edits files directly. Patch is collected via `git diff` after the agent finishes.

**CONTAINER mode**: Agent runs inside the Docker container. Patch is extracted from agent output.

## Evaluation Pipeline

The `Runner._run_instance()` method executes the full pipeline for one instance:

```
1. Create Workspace
   ├── Docker mode: Workspace (container + bind mount)
   └── Host mode:   HostWorkspace (virtualenv)

2. workspace.setup()
   ├── git clone repo
   ├── git checkout base_commit
   ├── Start container (Docker) or create venv (host)
   └── Install dependencies (pip install -e ., etc.)

3. _invoke_agent()
   ├── agent.build_command(instance, workdir)
   ├── subprocess.run(cmd, timeout=..., cwd=workdir)
   └── agent.parse_output() → AgentOutput

4. Collect patch
   ├── From agent output (if provided)
   └── From git diff (HOST mode)

5. evaluator.evaluate()
   ├── Apply test_patch to workspace
   ├── Run fail_to_pass tests (should now pass)
   ├── Run pass_to_pass tests (should still pass)
   └── Return EvalResult (resolved = all pass)

6. workspace.cleanup()
   ├── Remove container (Docker)
   └── Delete temp directory
```

## Workspace Architecture

Both workspace types implement the same interface:

```python
class Workspace / HostWorkspace:
    host_path: str              # Path on host filesystem
    container_path: str         # Path in container (or same as host)

    def setup()                 # Clone, checkout, install
    def exec_in_container(cmd)  # Run command → (exit_code, output)
    def apply_patch(patch)      # Apply git patch → (success, output)
    def get_diff()              # Get git diff → str
    def cleanup()               # Remove container/temp files
```

**Docker Workspace** (`workspace.py`):
- Clones repo to a temp directory on the host
- Bind-mounts it into a container at `/testbed`
- Runs install commands and tests inside the container
- Uses `DockerManager` for container lifecycle

**Host Workspace** (`host_workspace.py`):
- Clones repo to a temp directory
- Creates a virtualenv inside it
- Prepends venv `bin/` to PATH for command execution
- No container isolation

### Dependency Installation

The Docker workspace uses a two-tier strategy:

1. **Hardcoded hints** for known repos (Django, Flask, scikit-learn, etc.)
2. **Auto-detection** fallback: inspects `pyproject.toml`, `setup.py`, `requirements*.txt`

```python
# workspace.py
_INSTALL_HINTS = {
    "django/django":    ["pip install -e .", "pip install pytest pytest-django"],
    "astropy/astropy":  ["pip install 'setuptools<70' ...", "pip install -e . --no-build-isolation ..."],
    "sympy/sympy":      ["pip install -e .", "pip install pytest"],
    ...
}
```

## SWE-bench Evaluator

The evaluator (`evaluators/swebench.py`) handles two test framework styles:

**Django repos**: `python tests/runtests.py --verbosity 2 --parallel 1 <modules>`
- Parses test names like `test_foo (app.module.TestClass)` into module paths

**Pytest repos**: `python -m pytest <paths> -x --tb=short`
- Converts test names to pytest node IDs if needed

Test result parsing looks for:
- Django style: `test_name ... ok` / `test_name ... FAIL`
- Pytest style: `test_name PASSED` / `test_name FAILED`
- Fallback: overall exit code

## Configuration

`RunConfig` loads from YAML with CLI overrides:

```
configs/default.yaml          CLI overrides
        │                          │
        └────────┬─────────────────┘
                 │
           RunConfig
           ├── DatasetConfig (name, split, limit, instance_ids)
           ├── AgentConfig   (name, timeout, env, options)
           ├── DockerConfig  (enabled, image, memory, cpu)
           ├── evaluator     (string)
           ├── reporter      (string)
           ├── results_dir   (string)
           └── max_workers   (int)
```

## Concurrency

The runner supports parallel execution via `ThreadPoolExecutor`:

```python
# max_workers=1: sequential with progress bar
runner._run_serial(instances)

# max_workers>1: parallel with thread pool
runner._run_parallel(instances, max_workers)
```

Each instance runs independently with its own workspace. Progress is tracked with Rich progress bars showing resolved/failed counts.

## Docker Base Image

`docker/base/Dockerfile` provides Python 3.11 with:
- Build tools: git, build-essential, pkg-config
- Dev libraries: libffi, libssl, libxml2, libxslt, libjpeg, zlib
- Pre-installed Python packages: pytest, pytest-xdist, coverage, hypothesis, tox, setuptools, wheel

Using Python 3.11 ensures compatibility with older project code that may not support Python 3.12+.
