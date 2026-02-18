"""Evaluation runner — orchestrates the full pipeline."""

from __future__ import annotations

import logging
import os
import subprocess
import time
import uuid
from concurrent.futures import ThreadPoolExecutor, as_completed
from datetime import datetime

from rich.console import Console
from rich.progress import (
    BarColumn,
    MofNCompleteColumn,
    Progress,
    SpinnerColumn,
    TextColumn,
    TimeElapsedColumn,
)

from codingeval.core.agent import AgentAdapter
from codingeval.core.config import RunConfig
from codingeval.core.dataset import Dataset
from codingeval.core.evaluator import Evaluator
from codingeval.core.models import (
    AgentOutput,
    EvalInstance,
    EvalResult,
    EvalStatus,
    ExecutionMode,
    InstanceRunResult,
    RunSummary,
)
from codingeval.core.reporter import Reporter
from codingeval.docker.host_workspace import HostWorkspace
from codingeval.docker.manager import DockerManager
from codingeval.docker.workspace import Workspace, WorkspaceManager

logger = logging.getLogger(__name__)


class Runner:
    """Orchestrates dataset loading, agent invocation, and evaluation."""

    def __init__(
        self,
        config: RunConfig,
        dataset: Dataset,
        agent: AgentAdapter,
        evaluator: Evaluator,
        reporter: Reporter,
    ):
        self.config = config
        self.dataset = dataset
        self.agent = agent
        self.evaluator = evaluator
        self.reporter = reporter
        self._use_docker = config.docker.enabled
        if self._use_docker:
            self._docker = DockerManager(config.docker)
            self._workspace_mgr = WorkspaceManager(self._docker)
        else:
            self._docker = None
            self._workspace_mgr = None
        self._console = Console(stderr=True)

    def run(
        self,
        run_id: str | None = None,
        instance_ids: list[str] | None = None,
        limit: int | None = None,
        max_workers: int | None = None,
    ) -> RunSummary:
        """Execute a full evaluation run."""
        run_id = run_id or uuid.uuid4().hex[:12]
        max_workers = max_workers or self.config.max_workers

        self._console.print(f"\n[bold]Starting run [cyan]{run_id}[/cyan][/bold]")
        self._console.print(
            f"  Agent: [green]{self.agent.name}[/green]  "
            f"Dataset: [green]{self.dataset.name}[/green]  "
            f"Workers: [green]{max_workers}[/green]"
        )

        # Load dataset
        self.dataset.load(**self.config.dataset.options)
        instances = self.dataset.get_instances(
            split=self.config.dataset.split,
            instance_ids=instance_ids or self.config.dataset.instance_ids or None,
            limit=limit or self.config.dataset.limit,
        )

        self._console.print(f"  Instances: [green]{len(instances)}[/green]\n")

        summary = RunSummary(
            run_id=run_id,
            dataset_name=self.dataset.name,
            agent_name=self.agent.name,
            total_instances=len(instances),
        )

        # Run instances with progress tracking
        if max_workers <= 1:
            results = self._run_serial(instances)
        else:
            results = self._run_parallel(instances, max_workers)

        # Aggregate results
        for result in results:
            summary.results.append(result)
            if result.eval_result:
                status = result.eval_result.status
                if result.eval_result.resolved:
                    summary.resolved += 1
                elif status == EvalStatus.FAILED:
                    summary.failed += 1
                elif status == EvalStatus.ERROR:
                    summary.errors += 1
                elif status == EvalStatus.TIMEOUT:
                    summary.timeouts += 1
                elif status == EvalStatus.SKIPPED:
                    summary.skipped += 1
            else:
                summary.errors += 1

        summary.completed_at = datetime.now()

        # Report results
        self.reporter.report(summary, output_dir=self.config.results_dir)

        return summary

    def _make_progress(self) -> Progress:
        return Progress(
            SpinnerColumn(),
            TextColumn("[progress.description]{task.description}"),
            BarColumn(),
            MofNCompleteColumn(),
            TextColumn("| resolved:{task.fields[resolved]} failed:{task.fields[failed]}"),
            TimeElapsedColumn(),
            console=self._console,
        )

    def _run_serial(self, instances: list[EvalInstance]) -> list[InstanceRunResult]:
        """Run instances sequentially with a progress bar."""
        results: list[InstanceRunResult] = []
        resolved = 0
        failed = 0

        with self._make_progress() as progress:
            task_id = progress.add_task(
                "Evaluating", total=len(instances), resolved=0, failed=0
            )
            for inst in instances:
                progress.update(
                    task_id,
                    description=f"[cyan]{inst.instance_id}[/cyan]",
                )
                result = self._run_instance(inst)
                results.append(result)

                if result.eval_result and result.eval_result.resolved:
                    resolved += 1
                else:
                    failed += 1

                progress.update(task_id, advance=1, resolved=resolved, failed=failed)

        return results

    def _run_parallel(
        self, instances: list[EvalInstance], max_workers: int
    ) -> list[InstanceRunResult]:
        """Run instances in parallel using a thread pool with progress tracking."""
        results: list[InstanceRunResult] = []
        resolved = 0
        failed = 0

        with self._make_progress() as progress:
            task_id = progress.add_task(
                "Evaluating", total=len(instances), resolved=0, failed=0
            )
            with ThreadPoolExecutor(max_workers=max_workers) as executor:
                futures = {
                    executor.submit(self._run_instance, inst): inst
                    for inst in instances
                }
                for future in as_completed(futures):
                    inst = futures[future]
                    try:
                        result = future.result()
                    except Exception as e:
                        logger.exception("Error running instance %s", inst.instance_id)
                        result = InstanceRunResult(
                            instance=inst,
                            eval_result=EvalResult(
                                instance_id=inst.instance_id,
                                status=EvalStatus.ERROR,
                                error_message=str(e),
                            ),
                        )
                    results.append(result)

                    if result.eval_result and result.eval_result.resolved:
                        resolved += 1
                    else:
                        failed += 1

                    progress.update(task_id, advance=1, resolved=resolved, failed=failed)

        return results

    def _create_workspace(self, instance: EvalInstance) -> HostWorkspace | Workspace:
        """Create a workspace — Docker-backed or host-only."""
        if self._use_docker and self._workspace_mgr:
            return self._workspace_mgr.create_workspace(instance)
        return HostWorkspace(instance)

    def _run_instance(self, instance: EvalInstance) -> InstanceRunResult:
        """Run a single instance: setup workspace, invoke agent, evaluate, cleanup."""
        logger.info("Running instance: %s", instance.instance_id)
        workspace: HostWorkspace | Workspace | None = None

        try:
            # Setup workspace
            workspace = self._create_workspace(instance)
            workspace.setup()

            # Invoke agent
            agent_output = self._invoke_agent(instance, workspace)

            # Collect patch from workspace if agent didn't produce one directly
            if not agent_output.patch:
                if self.agent.execution_mode == ExecutionMode.HOST:
                    agent_output.patch = self._get_host_diff(workspace.host_path)
                else:
                    agent_output.patch = workspace.get_diff()

            # Evaluate
            eval_result = self.evaluator.evaluate(instance, agent_output, workspace)

            return InstanceRunResult(
                instance=instance,
                agent_output=agent_output,
                eval_result=eval_result,
            )

        except Exception as e:
            logger.exception("Error running instance %s", instance.instance_id)
            return InstanceRunResult(
                instance=instance,
                eval_result=EvalResult(
                    instance_id=instance.instance_id,
                    status=EvalStatus.ERROR,
                    error_message=str(e),
                ),
            )
        finally:
            if workspace and self.config.docker.cleanup:
                workspace.cleanup()

    def _invoke_agent(
        self, instance: EvalInstance, workspace: HostWorkspace | Workspace
    ) -> AgentOutput:
        """Invoke the agent on an instance."""
        cmd = self.agent.build_command(instance, workspace.host_path)
        env = self.agent.get_environment()
        timeout = self.agent.get_timeout_seconds()

        # Build environment: inherit current env and merge agent-specific vars
        run_env = dict(os.environ)
        if env:
            for key, value in env.items():
                if value:
                    run_env[key] = value
                else:
                    run_env.pop(key, None)  # empty string = unset

        # Determine whether to pipe the prompt via stdin
        stdin_input = None
        if self.agent.prompt_via_stdin:
            stdin_input = self.agent.build_prompt(instance)

        logger.info("Invoking agent on %s", instance.instance_id)
        start_time = time.time()

        try:
            result = subprocess.run(
                cmd,
                input=stdin_input,
                capture_output=True,
                text=True,
                timeout=timeout,
                cwd=workspace.host_path,
                env=run_env,
            )
            duration = time.time() - start_time

            agent_output = self.agent.parse_output(
                result.stdout, result.stderr, result.returncode, duration
            )
            agent_output.instance_id = instance.instance_id
            return agent_output

        except subprocess.TimeoutExpired:
            duration = time.time() - start_time
            logger.warning(
                "Agent timed out after %.0fs on %s", duration, instance.instance_id
            )
            return AgentOutput(
                instance_id=instance.instance_id,
                agent_name=self.agent.name,
                exit_code=-1,
                stderr=f"Agent timed out after {timeout}s",
                duration_seconds=duration,
            )

    @staticmethod
    def _get_host_diff(workdir: str) -> str:
        """Get git diff from the host filesystem."""
        result = subprocess.run(
            ["git", "diff"],
            cwd=workdir,
            capture_output=True,
            text=True,
        )
        return result.stdout if result.returncode == 0 else ""
