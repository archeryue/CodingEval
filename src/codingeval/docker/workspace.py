"""Workspace management for evaluation instances."""

from __future__ import annotations

import logging
import tempfile
from pathlib import Path

from docker.models.containers import Container

from codingeval.core.models import EvalInstance
from codingeval.docker.manager import DockerManager

logger = logging.getLogger(__name__)

# Map repo-owner/repo-name patterns to install commands.
# Covers the most common SWE-bench repositories.
_INSTALL_HINTS: dict[str, list[str]] = {
    "astropy/astropy": [
        "pip install 'setuptools<70' wheel cython numpy extension_helpers",
        "pip install -e . --no-build-isolation 2>/dev/null || python setup.py develop 2>/dev/null || true",
        "pip install pytest",
    ],
    "django/django": [
        "pip install -e .",
        "pip install pytest pytest-django",
    ],
    "pallets/flask": [
        "pip install -e '.[dev]'",
    ],
    "psf/requests": [
        "pip install -e '.[dev]'",
    ],
    "scikit-learn/scikit-learn": [
        "pip install -e .",
        "pip install pytest",
    ],
    "matplotlib/matplotlib": [
        "pip install -e .",
        "pip install pytest",
    ],
    "sympy/sympy": [
        "pip install -e .",
        "pip install pytest",
    ],
    "pytest-dev/pytest": [
        "pip install -e .",
    ],
    "psf/black": [
        "pip install -e '.[d]'",
    ],
    "pylint-dev/pylint": [
        "pip install -e .",
        "pip install pytest",
    ],
    "pylint-dev/astroid": [
        "pip install -e .",
        "pip install pytest",
    ],
    "sphinx-doc/sphinx": [
        "pip install -e '.[test]'",
    ],
}


def _get_install_commands(repo: str) -> list[str]:
    """Determine install commands for a repository.

    Uses known hints first, falls back to heuristics.
    """
    if repo in _INSTALL_HINTS:
        return _INSTALL_HINTS[repo]

    # Fallback: inspect the repo for common files
    return []


class Workspace:
    """Manages the workspace for a single evaluation instance.

    The workspace consists of:
    - A host directory (bind-mounted) where the repo is cloned
    - A Docker container where tests run

    ``setup()`` clones the repo, starts the container, and installs
    the project's dependencies so that ``exec_in_container`` can run
    the test suite.
    """

    def __init__(
        self,
        instance: EvalInstance,
        docker_manager: DockerManager,
        host_workdir: str | None = None,
    ):
        self.instance = instance
        self._docker = docker_manager
        self._host_workdir = host_workdir or tempfile.mkdtemp(
            prefix=f"codingeval-{instance.instance_id}-"
        )
        self._container: Container | None = None
        self._container_workdir = "/testbed"

    @property
    def host_path(self) -> str:
        return self._host_workdir

    @property
    def container_path(self) -> str:
        return self._container_workdir

    @property
    def container(self) -> Container | None:
        return self._container

    def setup(self) -> None:
        """Set up the workspace: clone repo, checkout commit, start container, install deps."""
        self._clone_repo()
        self._start_container()
        self._install_environment()

    def _clone_repo(self) -> None:
        """Clone the repository and check out the base commit."""
        import subprocess

        bundle_path = self.instance.metadata.get("repo_bundle_path")
        if bundle_path:
            repo_url = bundle_path
        else:
            repo_url = f"https://github.com/{self.instance.repo}.git"
        logger.info("Cloning %s to %s", repo_url, self._host_workdir)

        # Full clone — SWE-bench base commits can be far back in history
        subprocess.run(
            ["git", "clone", repo_url, self._host_workdir],
            check=True,
            capture_output=True,
        )

        if self.instance.base_commit:
            logger.info("Checking out %s", self.instance.base_commit)
            subprocess.run(
                ["git", "checkout", self.instance.base_commit],
                cwd=self._host_workdir,
                check=True,
                capture_output=True,
            )

    def _start_container(self) -> None:
        """Create and start the Docker container with the workspace mounted."""
        volumes = {
            self._host_workdir: {"bind": self._container_workdir, "mode": "rw"},
        }
        self._container = self._docker.create_container(
            name=f"codingeval-{self.instance.instance_id}",
            volumes=volumes,
        )
        self._docker.start_container(self._container)

    def _install_environment(self) -> None:
        """Install the project and its test dependencies inside the container."""
        repo = self.instance.repo

        # Try known install hints first
        commands = _get_install_commands(repo)

        # Fallback: detect from repo contents
        if not commands:
            commands = self._detect_install_commands()

        if not commands:
            logger.warning("No install commands determined for %s — tests may fail", repo)
            return

        for cmd in commands:
            logger.info("Installing [%s]: %s", self.instance.instance_id, cmd)
            exit_code, output = self.exec_in_container(cmd)
            if exit_code != 0:
                logger.warning(
                    "Install command failed (exit %d) for %s: %s\n%s",
                    exit_code,
                    self.instance.instance_id,
                    cmd,
                    output[-500:] if len(output) > 500 else output,
                )

    def _detect_install_commands(self) -> list[str]:
        """Heuristically detect how to install the project."""
        commands: list[str] = []
        workdir = Path(self._host_workdir)

        # Check for pyproject.toml or setup.py
        has_pyproject = (workdir / "pyproject.toml").exists()
        has_setup_py = (workdir / "setup.py").exists()
        has_setup_cfg = (workdir / "setup.cfg").exists()
        has_requirements = (workdir / "requirements.txt").exists()
        has_requirements_dev = (workdir / "requirements-dev.txt").exists()
        has_test_requirements = (workdir / "test-requirements.txt").exists()

        if has_pyproject or has_setup_py or has_setup_cfg:
            commands.append("pip install -e .")
        elif has_requirements:
            commands.append("pip install -r requirements.txt")

        # Additional test deps
        if has_requirements_dev:
            commands.append("pip install -r requirements-dev.txt")
        if has_test_requirements:
            commands.append("pip install -r test-requirements.txt")

        # Ensure pytest is available
        commands.append("pip install pytest")

        return commands

    def exec_in_container(self, command: str) -> tuple[int, str]:
        """Execute a command inside the container."""
        if self._container is None:
            raise RuntimeError("Container not started. Call setup() first.")
        return self._docker.exec_in_container(
            self._container, command, workdir=self._container_workdir
        )

    def apply_patch(self, patch: str) -> tuple[bool, str]:
        """Apply a patch to the workspace.

        Writes the patch to a file on the host side of the bind mount so
        the container can read it without shell-escaping issues.
        """
        if not patch.strip():
            return True, ""

        # Write patch file on the host — visible inside the container
        # via the bind mount at /testbed/.codingeval_patch.diff
        patch_host_path = Path(self._host_workdir) / ".codingeval_patch.diff"
        patch_host_path.write_text(patch)

        patch_container_path = f"{self._container_workdir}/.codingeval_patch.diff"

        # Apply the patch
        exit_code, output = self.exec_in_container(
            f"cd {self._container_workdir} && git apply --allow-empty {patch_container_path}"
        )

        if exit_code != 0:
            # Try with --3way as fallback
            exit_code, output = self.exec_in_container(
                f"cd {self._container_workdir} && git apply --3way {patch_container_path}"
            )

        # Clean up the patch file
        patch_host_path.unlink(missing_ok=True)

        return exit_code == 0, output

    def get_diff(self) -> str:
        """Get the current git diff of the workspace."""
        exit_code, output = self.exec_in_container("cd /testbed && git diff")
        return output if exit_code == 0 else ""

    def cleanup(self) -> None:
        """Remove the container and clean up temporary files."""
        if self._container:
            try:
                self._docker.remove_container(self._container)
            except Exception:
                logger.warning(
                    "Failed to remove container for %s", self.instance.instance_id
                )
            self._container = None

        # Clean up host directory
        import shutil

        host_path = Path(self._host_workdir)
        if host_path.exists() and str(host_path).startswith(tempfile.gettempdir()):
            shutil.rmtree(host_path, ignore_errors=True)


class WorkspaceManager:
    """Factory for creating and managing workspaces."""

    def __init__(self, docker_manager: DockerManager):
        self._docker = docker_manager
        self._workspaces: dict[str, Workspace] = {}

    def create_workspace(
        self, instance: EvalInstance, host_workdir: str | None = None
    ) -> Workspace:
        """Create a workspace for an instance."""
        workspace = Workspace(instance, self._docker, host_workdir)
        self._workspaces[instance.instance_id] = workspace
        return workspace

    def get_workspace(self, instance_id: str) -> Workspace | None:
        return self._workspaces.get(instance_id)

    def cleanup_all(self) -> None:
        """Clean up all workspaces."""
        for workspace in self._workspaces.values():
            workspace.cleanup()
        self._workspaces.clear()
