"""Patch utility functions."""

from __future__ import annotations


def extract_patch_from_output(output: str) -> str:
    """Extract a git diff/patch from agent output text."""
    lines = output.split("\n")
    patch_lines: list[str] = []
    in_patch = False

    for line in lines:
        if line.startswith("diff --git"):
            in_patch = True
        if in_patch:
            patch_lines.append(line)

    return "\n".join(patch_lines) if patch_lines else ""


def validate_patch(patch: str) -> bool:
    """Check if a string looks like a valid git patch."""
    if not patch.strip():
        return False
    return "diff --git" in patch or patch.startswith("---")
