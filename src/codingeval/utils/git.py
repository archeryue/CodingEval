"""Git utility functions."""

from __future__ import annotations

import logging
import subprocess
from pathlib import Path

logger = logging.getLogger(__name__)


def clone_repo(
    repo: str,
    dest: str | Path,
    depth: int | None = 100,
    base_commit: str | None = None,
) -> None:
    """Clone a GitHub repository and optionally check out a specific commit."""
    repo_url = f"https://github.com/{repo}.git"
    dest = str(dest)

    cmd = ["git", "clone"]
    if depth:
        cmd.extend(["--depth", str(depth)])
    cmd.extend([repo_url, dest])

    logger.info("Cloning %s to %s", repo_url, dest)
    subprocess.run(cmd, check=True, capture_output=True)

    if base_commit:
        subprocess.run(
            ["git", "checkout", base_commit],
            cwd=dest,
            check=True,
            capture_output=True,
        )


def get_diff(workdir: str | Path) -> str:
    """Get the current git diff in the working directory."""
    result = subprocess.run(
        ["git", "diff"],
        cwd=str(workdir),
        capture_output=True,
        text=True,
    )
    return result.stdout


def apply_patch(workdir: str | Path, patch: str) -> tuple[bool, str]:
    """Apply a patch to the working directory."""
    result = subprocess.run(
        ["git", "apply", "--allow-empty", "-"],
        input=patch,
        cwd=str(workdir),
        capture_output=True,
        text=True,
    )
    if result.returncode != 0:
        # Try with --3way fallback
        result = subprocess.run(
            ["git", "apply", "--3way", "-"],
            input=patch,
            cwd=str(workdir),
            capture_output=True,
            text=True,
        )
    return result.returncode == 0, result.stderr or result.stdout
