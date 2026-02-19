#!/usr/bin/env python3
"""Build git bundles for regression test cases.

Run this script once to generate the bundles, then commit them.

    python -m codingeval.regression.repo_builder

Each case is defined as a dict with:
  - name: bundle filename (without .bundle)
  - files: dict of filepath -> content (the initial buggy state)
"""

from __future__ import annotations

import os
import shutil
import subprocess
import tempfile
from pathlib import Path

REPOS_DIR = Path(__file__).parent / "repos"

# ─────────────────────────────────────────────────────────────
# Case 1: fix-single-function — Fix divide-by-zero in calculator
# ─────────────────────────────────────────────────────────────
CASE_FIX_SINGLE_FUNCTION = {
    "name": "fix-single-function",
    "files": {
        "calculator.py": '''\
def add(a, b):
    return a + b


def subtract(a, b):
    return a - b


def multiply(a, b):
    return a * b


def divide(a, b):
    return a / b
''',
        "test_calculator.py": '''\
import pytest
from calculator import add, subtract, multiply, divide


def test_add():
    assert add(2, 3) == 5


def test_subtract():
    assert subtract(5, 3) == 2


def test_multiply():
    assert multiply(3, 4) == 12


def test_divide():
    assert divide(10, 2) == 5.0


def test_divide_by_zero():
    with pytest.raises(ValueError, match="Cannot divide by zero"):
        divide(10, 0)
''',
    },
}

# ─────────────────────────────────────────────────────────────
# Case 2: add-error-handling — Add try/except for invalid JSON
# ─────────────────────────────────────────────────────────────
CASE_ADD_ERROR_HANDLING = {
    "name": "add-error-handling",
    "files": {
        "file_reader.py": '''\
import json


def read_json(filepath):
    """Read and parse a JSON file."""
    with open(filepath) as f:
        return json.load(f)


def read_json_with_default(filepath, default=None):
    """Read a JSON file, returning default if the file contains invalid JSON."""
    with open(filepath) as f:
        data = json.load(f)
    return data
''',
        "test_file_reader.py": '''\
import json
import tempfile
import os

import pytest
from file_reader import read_json, read_json_with_default


def test_read_valid_json():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"key": "value"}, f)
        path = f.name
    try:
        result = read_json(path)
        assert result == {"key": "value"}
    finally:
        os.unlink(path)


def test_read_json_with_default_valid():
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        json.dump({"a": 1}, f)
        path = f.name
    try:
        result = read_json_with_default(path)
        assert result == {"a": 1}
    finally:
        os.unlink(path)


def test_read_json_with_default_invalid():
    """Should return default when file contains invalid JSON."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("not valid json {{{")
        path = f.name
    try:
        result = read_json_with_default(path, default={"fallback": True})
        assert result == {"fallback": True}
    finally:
        os.unlink(path)


def test_read_json_with_default_invalid_no_default():
    """Should return None when file is invalid and no default given."""
    with tempfile.NamedTemporaryFile(mode="w", suffix=".json", delete=False) as f:
        f.write("???")
        path = f.name
    try:
        result = read_json_with_default(path)
        assert result is None
    finally:
        os.unlink(path)
''',
    },
}

# ─────────────────────────────────────────────────────────────
# Case 3: multi-file-import — Add validator, use it in model
# ─────────────────────────────────────────────────────────────
CASE_MULTI_FILE_IMPORT = {
    "name": "multi-file-import",
    "files": {
        "models.py": '''\
class User:
    def __init__(self, name, email):
        self.name = name
        self.email = email

    def __repr__(self):
        return f"User(name={self.name!r}, email={self.email!r})"
''',
        "validators.py": '''\
def validate_name(name):
    """Check that name is non-empty."""
    if not name or not name.strip():
        raise ValueError("Name cannot be empty")
    return name.strip()
''',
        "test_app.py": '''\
import pytest
from models import User
from validators import validate_name, validate_email


def test_valid_user():
    user = User("Alice", "alice@example.com")
    assert user.name == "Alice"


def test_validate_name():
    assert validate_name("Bob") == "Bob"


def test_validate_name_empty():
    with pytest.raises(ValueError):
        validate_name("")


def test_validate_email_valid():
    assert validate_email("user@example.com") == "user@example.com"


def test_validate_email_no_at():
    with pytest.raises(ValueError, match="must contain"):
        validate_email("invalid-email")


def test_validate_email_empty():
    with pytest.raises(ValueError, match="must contain"):
        validate_email("")


def test_user_with_validation():
    """User creation should validate email."""
    user = User("Alice", "alice@example.com")
    validate_email(user.email)
    assert user.email == "alice@example.com"
''',
    },
}

# ─────────────────────────────────────────────────────────────
# Case 4: fix-off-by-one — Fix pagination boundary bug
# ─────────────────────────────────────────────────────────────
CASE_FIX_OFF_BY_ONE = {
    "name": "fix-off-by-one",
    "files": {
        "pagination.py": '''\
def paginate(items, page, per_page=10):
    """Return a page of items.

    Args:
        items: Full list of items.
        page: 1-based page number.
        per_page: Items per page.

    Returns:
        dict with 'items', 'page', 'total_pages', 'has_next', 'has_prev'.
    """
    if page < 1:
        raise ValueError("Page must be >= 1")

    total = len(items)
    total_pages = (total + per_page - 1) // per_page

    start = page * per_page  # BUG: should be (page - 1) * per_page
    end = start + per_page
    page_items = items[start:end]

    return {
        "items": page_items,
        "page": page,
        "total_pages": total_pages,
        "has_next": page < total_pages,
        "has_prev": page > 1,
    }
''',
        "test_pagination.py": '''\
import pytest
from pagination import paginate


def test_first_page():
    items = list(range(1, 26))  # 1..25
    result = paginate(items, page=1, per_page=10)
    assert result["items"] == list(range(1, 11))
    assert result["page"] == 1
    assert result["has_next"] is True
    assert result["has_prev"] is False


def test_second_page():
    items = list(range(1, 26))
    result = paginate(items, page=2, per_page=10)
    assert result["items"] == list(range(11, 21))


def test_last_page():
    items = list(range(1, 26))
    result = paginate(items, page=3, per_page=10)
    assert result["items"] == list(range(21, 26))
    assert result["has_next"] is False
    assert result["has_prev"] is True


def test_total_pages():
    items = list(range(25))
    result = paginate(items, page=1, per_page=10)
    assert result["total_pages"] == 3


def test_single_page():
    items = [1, 2, 3]
    result = paginate(items, page=1, per_page=10)
    assert result["items"] == [1, 2, 3]
    assert result["total_pages"] == 1
    assert result["has_next"] is False
    assert result["has_prev"] is False


def test_invalid_page():
    with pytest.raises(ValueError):
        paginate([], page=0)
''',
    },
}

# ─────────────────────────────────────────────────────────────
# Case 5: search-and-replace — Replace 3 hardcoded URLs with config
# ─────────────────────────────────────────────────────────────
CASE_SEARCH_AND_REPLACE = {
    "name": "search-and-replace",
    "files": {
        "config.py": '''\
"""Application configuration."""


class Config:
    """Central config — URLs should be read from here."""

    API_URL = "https://api.example.com"
    CDN_URL = "https://cdn.example.com"
    AUTH_URL = "https://auth.example.com"


def get_api_url():
    return "https://api.example.com"


def get_cdn_url():
    return "https://cdn.example.com"


def get_auth_url():
    return "https://auth.example.com"
''',
        "test_config.py": '''\
from config import Config, get_api_url, get_cdn_url, get_auth_url


def test_api_url_uses_config():
    """get_api_url should return Config.API_URL, not a hardcoded string."""
    original = Config.API_URL
    Config.API_URL = "https://custom-api.test"
    try:
        assert get_api_url() == "https://custom-api.test"
    finally:
        Config.API_URL = original


def test_cdn_url_uses_config():
    """get_cdn_url should return Config.CDN_URL, not a hardcoded string."""
    original = Config.CDN_URL
    Config.CDN_URL = "https://custom-cdn.test"
    try:
        assert get_cdn_url() == "https://custom-cdn.test"
    finally:
        Config.CDN_URL = original


def test_auth_url_uses_config():
    """get_auth_url should return Config.AUTH_URL, not a hardcoded string."""
    original = Config.AUTH_URL
    Config.AUTH_URL = "https://custom-auth.test"
    try:
        assert get_auth_url() == "https://custom-auth.test"
    finally:
        Config.AUTH_URL = original


def test_default_values():
    """Default config values should be set."""
    assert Config.API_URL == "https://api.example.com"
    assert Config.CDN_URL == "https://cdn.example.com"
    assert Config.AUTH_URL == "https://auth.example.com"
''',
    },
}

# ─────────────────────────────────────────────────────────────
# Case 6: debug-stack-trace — Fix KeyError from stack trace
# ─────────────────────────────────────────────────────────────
CASE_DEBUG_STACK_TRACE = {
    "name": "debug-stack-trace",
    "files": {
        "processor.py": '''\
def process_record(record):
    """Process a data record and return a summary.

    Args:
        record: dict with keys 'name', 'scores', and optionally 'metadata'.

    Returns:
        dict with 'name', 'average', and 'tag'.
    """
    name = record["name"]
    scores = record["scores"]
    average = sum(scores) / len(scores)
    tag = record["metadata"]["tag"]  # BUG: metadata or tag may be missing
    return {"name": name, "average": average, "tag": tag}
''',
        "test_processor.py": '''\
import pytest
from processor import process_record


def test_full_record():
    record = {
        "name": "Alice",
        "scores": [80, 90, 100],
        "metadata": {"tag": "student"},
    }
    result = process_record(record)
    assert result["name"] == "Alice"
    assert result["average"] == 90.0
    assert result["tag"] == "student"


def test_missing_metadata():
    """Should handle missing metadata gracefully."""
    record = {"name": "Bob", "scores": [70, 80]}
    result = process_record(record)
    assert result["name"] == "Bob"
    assert result["average"] == 75.0
    assert result["tag"] is None


def test_missing_tag_in_metadata():
    """Should handle metadata without tag key."""
    record = {"name": "Carol", "scores": [60], "metadata": {}}
    result = process_record(record)
    assert result["tag"] is None


def test_empty_scores():
    """Should handle empty scores gracefully."""
    record = {"name": "Dave", "scores": [], "metadata": {"tag": "test"}}
    result = process_record(record)
    assert result["average"] == 0.0
    assert result["tag"] == "test"
''',
    },
}

# ─────────────────────────────────────────────────────────────
# Case 7: add-new-method — Add O(1) min() to Stack class
# ─────────────────────────────────────────────────────────────
CASE_ADD_NEW_METHOD = {
    "name": "add-new-method",
    "files": {
        "stack.py": '''\
class Stack:
    """A stack data structure with push, pop, peek, and size operations."""

    def __init__(self):
        self._items = []

    def push(self, value):
        self._items.append(value)

    def pop(self):
        if not self._items:
            raise IndexError("Pop from empty stack")
        return self._items.pop()

    def peek(self):
        if not self._items:
            raise IndexError("Peek at empty stack")
        return self._items[-1]

    def size(self):
        return len(self._items)

    def is_empty(self):
        return len(self._items) == 0
''',
        "test_stack.py": '''\
import pytest
from stack import Stack


def test_push_pop():
    s = Stack()
    s.push(1)
    s.push(2)
    assert s.pop() == 2
    assert s.pop() == 1


def test_peek():
    s = Stack()
    s.push(42)
    assert s.peek() == 42
    assert s.size() == 1


def test_is_empty():
    s = Stack()
    assert s.is_empty() is True
    s.push(1)
    assert s.is_empty() is False


def test_pop_empty():
    s = Stack()
    with pytest.raises(IndexError):
        s.pop()


def test_min_single():
    """min() should return the minimum value in the stack."""
    s = Stack()
    s.push(5)
    assert s.min() == 5


def test_min_multiple():
    s = Stack()
    s.push(3)
    s.push(1)
    s.push(2)
    assert s.min() == 1


def test_min_after_pop():
    """min() should update after popping the minimum."""
    s = Stack()
    s.push(3)
    s.push(1)
    assert s.min() == 1
    s.pop()
    assert s.min() == 3


def test_min_empty():
    s = Stack()
    with pytest.raises(IndexError):
        s.min()
''',
    },
}

# ─────────────────────────────────────────────────────────────
# Case 8: fix-test-regression — Fix whitespace normalization
# ─────────────────────────────────────────────────────────────
CASE_FIX_TEST_REGRESSION = {
    "name": "fix-test-regression",
    "files": {
        "string_utils.py": '''\
def normalize_whitespace(text):
    """Collapse multiple whitespace characters into a single space.

    Should preserve leading/trailing whitespace stripping and
    collapse interior runs of spaces/tabs/newlines to a single space.
    """
    # BUG: this also strips interior single spaces between words
    parts = text.split()
    return "".join(parts)
''',
        "test_string_utils.py": '''\
from string_utils import normalize_whitespace


def test_collapse_multiple_spaces():
    assert normalize_whitespace("hello   world") == "hello world"


def test_collapse_tabs():
    assert normalize_whitespace("hello\\tworld") == "hello world"


def test_strip_leading_trailing():
    assert normalize_whitespace("  hello world  ") == "hello world"


def test_mixed_whitespace():
    assert normalize_whitespace("  hello  \\t  world  \\n  foo  ") == "hello world foo"


def test_single_word():
    assert normalize_whitespace("hello") == "hello"


def test_empty_string():
    assert normalize_whitespace("") == ""


def test_preserves_single_spaces():
    """Single spaces between words should be preserved."""
    assert normalize_whitespace("one two three") == "one two three"
''',
    },
}

# ─────────────────────────────────────────────────────────────
# Case 9: refactor-extract — Extract duplicated validation to helper
# ─────────────────────────────────────────────────────────────
CASE_REFACTOR_EXTRACT = {
    "name": "refactor-extract",
    "files": {
        "report.py": '''\
def generate_sales_report(records):
    """Generate a sales summary from records.

    Each record has 'amount' (must be positive) and 'region'.
    """
    total = 0
    for r in records:
        amount = r["amount"]
        if not isinstance(amount, (int, float)):
            raise TypeError(f"Amount must be numeric, got {type(amount).__name__}")
        if amount < 0:
            raise ValueError(f"Amount must be non-negative, got {amount}")
        total += amount
    return {"total": total, "count": len(records)}


def generate_expense_report(records):
    """Generate an expense summary from records.

    Each record has 'amount' (must be positive) and 'category'.
    """
    total = 0
    for r in records:
        amount = r["amount"]
        if not isinstance(amount, (int, float)):
            raise TypeError(f"Amount must be numeric, got {type(amount).__name__}")
        if amount < 0:
            raise ValueError(f"Amount must be non-negative, got {amount}")
        total += amount
    return {"total": total, "count": len(records)}


def generate_combined_report(sales_records, expense_records):
    """Generate a combined report."""
    sales = generate_sales_report(sales_records)
    expenses = generate_expense_report(expense_records)
    return {
        "sales_total": sales["total"],
        "expense_total": expenses["total"],
        "net": sales["total"] - expenses["total"],
    }
''',
        "test_report.py": '''\
import pytest
from report import (
    generate_sales_report,
    generate_expense_report,
    generate_combined_report,
    validate_amount,
)


def test_sales_report():
    records = [{"amount": 100, "region": "US"}, {"amount": 200, "region": "EU"}]
    result = generate_sales_report(records)
    assert result["total"] == 300
    assert result["count"] == 2


def test_expense_report():
    records = [{"amount": 50, "category": "travel"}, {"amount": 30, "category": "food"}]
    result = generate_expense_report(records)
    assert result["total"] == 80


def test_combined_report():
    sales = [{"amount": 500, "region": "US"}]
    expenses = [{"amount": 200, "category": "ops"}]
    result = generate_combined_report(sales, expenses)
    assert result["net"] == 300


def test_validate_amount_valid():
    """validate_amount should accept valid positive numbers."""
    assert validate_amount(100) == 100
    assert validate_amount(0) == 0
    assert validate_amount(3.14) == 3.14


def test_validate_amount_negative():
    with pytest.raises(ValueError, match="non-negative"):
        validate_amount(-5)


def test_validate_amount_non_numeric():
    with pytest.raises(TypeError, match="numeric"):
        validate_amount("abc")


def test_sales_invalid_amount():
    with pytest.raises(TypeError):
        generate_sales_report([{"amount": "bad"}])


def test_expense_negative_amount():
    with pytest.raises(ValueError):
        generate_expense_report([{"amount": -10}])
''',
    },
}

# ─────────────────────────────────────────────────────────────
# Case 10: fix-yaml-config — Fix values in config.yaml
# ─────────────────────────────────────────────────────────────
CASE_FIX_YAML_CONFIG = {
    "name": "fix-yaml-config",
    "files": {
        "app.py": '''\
import yaml
from pathlib import Path


def load_config(config_path=None):
    """Load application config from YAML file."""
    if config_path is None:
        config_path = Path(__file__).parent / "config.yaml"
    with open(config_path) as f:
        return yaml.safe_load(f)


def get_database_url(config=None):
    """Get database URL from config."""
    if config is None:
        config = load_config()
    db = config["database"]
    return f"{db[\'driver\']}://{db[\'host\']}:{db[\'port\']}/{db[\'name\']}"


def is_debug_mode(config=None):
    """Check if debug mode is enabled."""
    if config is None:
        config = load_config()
    return config["app"]["debug"]


def get_log_level(config=None):
    """Get the configured log level."""
    if config is None:
        config = load_config()
    return config["app"]["log_level"]
''',
        "config.yaml": '''\
app:
  name: myapp
  debug: true
  log_level: DEBUG
  max_connections: 10

database:
  driver: postgresql
  host: localhost
  port: 5432
  name: myapp_db

features:
  enable_cache: true
  enable_notifications: false
''',
        "test_app.py": '''\
import tempfile
import os

import yaml
from app import load_config, get_database_url, is_debug_mode, get_log_level


def _write_config(data):
    f = tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False)
    yaml.dump(data, f)
    f.close()
    return f.name


def test_load_default_config():
    """Default config.yaml should have production-safe values."""
    config = load_config()
    assert config["app"]["debug"] is False, "debug should be False in default config"
    assert config["app"]["log_level"] == "WARNING", "log_level should be WARNING"


def test_database_url():
    config = {
        "database": {
            "driver": "postgresql",
            "host": "db.example.com",
            "port": 5432,
            "name": "prod_db",
        },
        "app": {"debug": False, "log_level": "WARNING"},
    }
    assert get_database_url(config) == "postgresql://db.example.com:5432/prod_db"


def test_debug_mode():
    path = _write_config({
        "app": {"debug": True, "log_level": "DEBUG"},
        "database": {"driver": "sqlite", "host": "", "port": 0, "name": "test.db"},
    })
    try:
        config = load_config(path)
        assert is_debug_mode(config) is True
    finally:
        os.unlink(path)


def test_log_level_from_file():
    path = _write_config({
        "app": {"debug": False, "log_level": "ERROR"},
        "database": {"driver": "sqlite", "host": "", "port": 0, "name": "test.db"},
    })
    try:
        config = load_config(path)
        assert get_log_level(config) == "ERROR"
    finally:
        os.unlink(path)


def test_features_present():
    config = load_config()
    assert "features" in config
    assert config["features"]["enable_cache"] is True
''',
    },
}

# ─────────────────────────────────────────────────────────────
# All cases
# ─────────────────────────────────────────────────────────────
ALL_CASES = [
    CASE_FIX_SINGLE_FUNCTION,
    CASE_ADD_ERROR_HANDLING,
    CASE_MULTI_FILE_IMPORT,
    CASE_FIX_OFF_BY_ONE,
    CASE_SEARCH_AND_REPLACE,
    CASE_DEBUG_STACK_TRACE,
    CASE_ADD_NEW_METHOD,
    CASE_FIX_TEST_REGRESSION,
    CASE_REFACTOR_EXTRACT,
    CASE_FIX_YAML_CONFIG,
]


def build_bundle(case: dict, output_dir: Path) -> Path:
    """Create a git repo from case files and export as a bundle."""
    name = case["name"]
    bundle_path = output_dir / f"{name}.bundle"

    with tempfile.TemporaryDirectory() as tmpdir:
        repo_dir = Path(tmpdir) / name

        # Create repo
        repo_dir.mkdir()
        subprocess.run(
            ["git", "init"], cwd=repo_dir, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "config", "user.email", "test@codingeval.dev"],
            cwd=repo_dir, check=True, capture_output=True,
        )
        subprocess.run(
            ["git", "config", "user.name", "CodingEval"],
            cwd=repo_dir, check=True, capture_output=True,
        )

        # Write files
        for filepath, content in case["files"].items():
            full_path = repo_dir / filepath
            full_path.parent.mkdir(parents=True, exist_ok=True)
            full_path.write_text(content)

        # Commit
        subprocess.run(
            ["git", "add", "."], cwd=repo_dir, check=True, capture_output=True
        )
        subprocess.run(
            ["git", "commit", "-m", f"Initial state for {name}"],
            cwd=repo_dir, check=True, capture_output=True,
        )

        # Get commit hash
        result = subprocess.run(
            ["git", "rev-parse", "HEAD"],
            cwd=repo_dir, check=True, capture_output=True, text=True,
        )
        commit_hash = result.stdout.strip()

        # Bundle
        subprocess.run(
            ["git", "bundle", "create", str(bundle_path), "--all"],
            cwd=repo_dir, check=True, capture_output=True,
        )

    print(f"  {name}: {bundle_path.name} (commit {commit_hash[:8]})")
    return bundle_path


def build_all():
    """Build all bundles and print commit hashes for cases.yaml."""
    print(f"Building {len(ALL_CASES)} bundles in {REPOS_DIR}")
    REPOS_DIR.mkdir(parents=True, exist_ok=True)

    for case in ALL_CASES:
        build_bundle(case, REPOS_DIR)

    print(f"\nDone. Bundles written to {REPOS_DIR}")


if __name__ == "__main__":
    build_all()
