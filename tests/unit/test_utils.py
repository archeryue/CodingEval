"""Tests for utility modules."""

from codingeval.utils.patch import extract_patch_from_output, validate_patch


def test_extract_patch_from_output():
    output = (
        "Thinking about the issue...\n"
        "diff --git a/file.py b/file.py\n"
        "--- a/file.py\n"
        "+++ b/file.py\n"
        "@@ -1 +1 @@\n"
        "-old\n"
        "+new\n"
    )
    patch = extract_patch_from_output(output)
    assert patch.startswith("diff --git")
    assert "-old" in patch
    assert "+new" in patch


def test_extract_patch_no_patch():
    output = "Just some regular output\nno patch here"
    patch = extract_patch_from_output(output)
    assert patch == ""


def test_validate_patch_valid():
    patch = "diff --git a/file.py b/file.py\n--- a/file.py\n+++ b/file.py"
    assert validate_patch(patch) is True


def test_validate_patch_empty():
    assert validate_patch("") is False
    assert validate_patch("   ") is False


def test_validate_patch_invalid():
    assert validate_patch("not a patch") is False
