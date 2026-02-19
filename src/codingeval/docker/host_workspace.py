"""Host-only workspace — runs everything directly on the host without Docker."""

from __future__ import annotations

import logging
import subprocess
import sys
import tempfile
from pathlib import Path

from codingeval.core.models import EvalInstance

logger = logging.getLogger(__name__)


class HostWorkspace:
    """Workspace that operates entirely on the host filesystem.

    Creates a per-instance virtualenv, installs dependencies, and runs
    tests directly via subprocess.  Same interface as Workspace so the
    Runner / Evaluator can use either transparently.
    """

    def __init__(
        self,
        instance: EvalInstance,
        host_workdir: str | None = None,
    ):
        self.instance = instance
        self._host_workdir = host_workdir or tempfile.mkdtemp(
            prefix=f"codingeval-{instance.instance_id}-"
        )
        self._venv_dir = str(Path(self._host_workdir) / ".venv")
        self._pip = str(Path(self._venv_dir) / "bin" / "pip")
        self._python = str(Path(self._venv_dir) / "bin" / "python")

    @property
    def host_path(self) -> str:
        return self._host_workdir

    @property
    def container_path(self) -> str:
        return self._host_workdir

    @property
    def container(self):
        return None

    def setup(self) -> None:
        """Clone repo, checkout commit, create venv, install deps."""
        self._clone_repo()
        self._create_venv()
        self._install_environment()

    def _clone_repo(self) -> None:
        bundle_path = self.instance.metadata.get("repo_bundle_path")
        if bundle_path:
            repo_url = bundle_path
        else:
            repo_url = f"https://github.com/{self.instance.repo}.git"
        logger.info("Cloning %s to %s", repo_url, self._host_workdir)

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

    def _create_venv(self) -> None:
        """Create a virtualenv inside the workspace."""
        logger.info("Creating venv at %s", self._venv_dir)
        subprocess.run(
            [sys.executable, "-m", "venv", self._venv_dir],
            check=True,
            capture_output=True,
        )
        # Upgrade pip to avoid old-pip issues
        self._run_pip(["install", "--upgrade", "pip", "setuptools", "wheel"])

    def _run_pip(self, args: list[str]) -> subprocess.CompletedProcess:
        """Run pip inside the workspace venv."""
        return subprocess.run(
            [self._pip] + args,
            cwd=self._host_workdir,
            capture_output=True,
            text=True,
        )

    def _install_environment(self) -> None:
        """Install project and test deps into the workspace venv."""
        workdir = Path(self._host_workdir)

        commands: list[list[str]] = []
        has_pyproject = (workdir / "pyproject.toml").exists()
        has_setup_py = (workdir / "setup.py").exists()
        has_setup_cfg = (workdir / "setup.cfg").exists()

        if has_pyproject or has_setup_py or has_setup_cfg:
            commands.append(["install", "-e", "."])

        for req_file in [
            "requirements.txt",
            "requirements-dev.txt",
            "test-requirements.txt",
            "requirements_test.txt",
        ]:
            if (workdir / req_file).exists():
                commands.append(["install", "-r", req_file])

        commands.append(["install", "pytest"])

        for pip_args in commands:
            logger.info("Installing [%s]: pip %s", self.instance.instance_id, " ".join(pip_args))
            result = self._run_pip(pip_args)
            if result.returncode != 0:
                stderr_tail = result.stderr[-500:] if len(result.stderr) > 500 else result.stderr
                logger.warning(
                    "Install failed (exit %d): pip %s\n%s",
                    result.returncode,
                    " ".join(pip_args),
                    stderr_tail,
                )

    def exec_in_container(self, command: str) -> tuple[int, str]:
        """Run a command on the host using the workspace venv.

        Prepends the venv's bin/ to PATH so that ``python`` and ``pytest``
        resolve to the workspace venv.
        """
        import os

        env = dict(os.environ)
        venv_bin = str(Path(self._venv_dir) / "bin")
        env["PATH"] = venv_bin + ":" + env.get("PATH", "")
        env["VIRTUAL_ENV"] = self._venv_dir

        result = subprocess.run(
            ["bash", "-c", command],
            cwd=self._host_workdir,
            capture_output=True,
            text=True,
            timeout=300,
            env=env,
        )
        output = result.stdout + result.stderr
        return result.returncode, output

    def apply_patch(self, patch: str) -> tuple[bool, str]:
        if not patch.strip():
            return True, ""

        patch_path = Path(self._host_workdir) / ".codingeval_patch.diff"
        patch_path.write_text(patch)

        result = subprocess.run(
            ["git", "apply", "--allow-empty", str(patch_path)],
            cwd=self._host_workdir,
            capture_output=True,
            text=True,
        )
        if result.returncode != 0:
            result = subprocess.run(
                ["git", "apply", "--3way", str(patch_path)],
                cwd=self._host_workdir,
                capture_output=True,
                text=True,
            )

        patch_path.unlink(missing_ok=True)
        return result.returncode == 0, result.stdout + result.stderr

    def get_diff(self) -> str:
        result = subprocess.run(
            ["git", "diff"],
            cwd=self._host_workdir,
            capture_output=True,
            text=True,
        )
        return result.stdout if result.returncode == 0 else ""

    def cleanup(self) -> None:
        import shutil

        host_path = Path(self._host_workdir)
        if host_path.exists() and str(host_path).startswith(tempfile.gettempdir()):
            shutil.rmtree(host_path, ignore_errors=True)
