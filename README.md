# CodingEval

Evaluation framework for CLI-based coding agents. Tests how well AI agents fix real-world bugs by running them against [SWE-bench](https://www.swebench.com/) instances in isolated Docker containers, then verifying fixes with the project's own test suite.

## Quick Start

```bash
# Install
python3 -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"

# Build the Docker base image
docker build -t codingeval-base:latest docker/base/

# Run evaluation (5 SWE-bench Lite instances with Claude Code)
codingeval run --config configs/default.yaml --limit 5

# Run without Docker (uses host virtualenvs instead)
codingeval run --config configs/default.yaml --limit 5 --no-docker
```

## How It Works

1. **Clone** a real open-source repo at the commit where a bug existed
2. **Install** the project's dependencies in an isolated environment
3. **Invoke** the coding agent with the bug report as a prompt
4. **Collect** the agent's code changes via `git diff`
5. **Apply** the test patch and run the test suite
6. **Report** whether the agent's fix passes all tests

```
codingeval run --agent claude-code --dataset swebench-lite --limit 10
```

## Supported Agents

| Agent | Command | Description |
|-------|---------|-------------|
| `claude-code` | `claude --print` | Claude Code CLI in non-interactive mode |
| `aider` | `aider --yes-always` | Aider CLI |
| `subprocess` | configurable | Any CLI tool via command template |

## Supported Datasets

| Dataset | Source | Description |
|---------|--------|-------------|
| `swebench` | HuggingFace | Full SWE-bench (~2k instances) |
| `swebench-lite` | HuggingFace | Lighter subset (~300 instances) |
| `swebench-verified` | HuggingFace | Verified subset |
| `custom` | YAML file | Your own test cases |

## CLI Reference

### `codingeval run`

```
Options:
  -c, --config PATH      YAML config file
  -d, --dataset NAME     Dataset name (e.g., swebench-lite)
  -a, --agent NAME       Agent name (e.g., claude-code)
  -n, --limit N          Max instances to evaluate
  -i, --instance ID      Specific instance ID (repeatable)
  -w, --max-workers N    Parallel workers
  --run-id ID            Custom run identifier
  --log-level LEVEL      INFO, DEBUG, WARNING, etc.
  --dry-run              Validate setup without running
  --no-docker            Run on host instead of Docker
```

### `codingeval list`

```bash
codingeval list datasets    # Show available datasets
codingeval list agents      # Show available agents
codingeval list evaluators  # Show available evaluators
codingeval list reporters   # Show available reporters
```

### `codingeval report`

```bash
codingeval report results/my-run/results.json
```

## Configuration

Default config (`configs/default.yaml`):

```yaml
dataset:
  name: swebench-lite
  split: test
  limit: null

agent:
  name: claude-code
  timeout: 600
  env: {}
  options: {}

docker:
  base_image: codingeval-base:latest
  memory_limit: 4g
  cpu_count: 2
  network_enabled: true
  cleanup: true

evaluator: swebench
reporter: console
results_dir: results
max_workers: 1
```

Agent-specific configs are in `configs/agents/`. See `configs/agents/claude_code.yaml` for Claude Code options (model, max_turns, budget, permissions).

## Custom Datasets

Create a YAML file with your test cases:

```yaml
dataset_name: my-tests
instances:
  - instance_id: bug-001
    repo: owner/repo
    base_commit: abc123
    problem_statement: |
      Description of the bug to fix.
    fail_to_pass:
      - tests/test_foo.py::test_the_fix
    pass_to_pass:
      - tests/test_foo.py::test_existing
```

Run with: `codingeval run --dataset custom -c config.yaml`

## Results

Results are saved as JSON in `results/<run-id>/results.json`:

```json
{
  "run_id": "my-run",
  "resolve_rate": 0.3,
  "total_instances": 10,
  "resolved": 3,
  "failed": 7,
  "results": [
    {
      "instance_id": "django__django-11049",
      "status": "passed",
      "resolved": true,
      "agent_duration": 22.0,
      "cost_usd": 0.12
    }
  ]
}
```

## Development

```bash
# Install dev dependencies
pip install -e ".[dev]"

# Run tests
pytest tests/ -v

# Lint
ruff check src/ tests/

# Type check
mypy src/
```

## Architecture

See [ARCHITECTURE.md](ARCHITECTURE.md) for detailed design documentation.

## Requirements

- Python 3.10+
- Docker (recommended) or host-based execution
- A coding agent CLI (e.g., `claude` for Claude Code)
