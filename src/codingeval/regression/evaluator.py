"""Regression evaluator — pytest-only, tests are pre-bundled in the repo."""

from __future__ import annotations

import logging
import re
import time

from codingeval.core.evaluator import Evaluator
from codingeval.core.models import (
    AgentOutput,
    EvalInstance,
    EvalResult,
    EvalStatus,
    SingleTestResult,
)

logger = logging.getLogger(__name__)


class RegressionEvaluator(Evaluator):
    """Evaluator for regression test cases.

    Unlike SWEBenchEvaluator, this:
    - Uses pytest only (no Django runtests.py)
    - Skips test_patch application (tests are pre-bundled in the repo)
    - Reuses the same test output parsing logic
    """

    @property
    def name(self) -> str:
        return "regression"

    def evaluate(
        self,
        instance: EvalInstance,
        agent_output: AgentOutput,
        workspace,
    ) -> EvalResult:
        """Run pre-bundled pytest tests and check results."""
        start_time = time.time()

        try:
            # No test_patch to apply — tests are already in the repo

            # Run fail_to_pass tests (should pass after the agent's fix)
            f2p_results = self._run_tests(instance, workspace, instance.fail_to_pass)

            # Run pass_to_pass tests (should still pass)
            p2p_results = self._run_tests(instance, workspace, instance.pass_to_pass)

            # Determine overall resolution
            all_f2p_passed = all(r.passed for r in f2p_results) if f2p_results else False
            all_p2p_passed = all(r.passed for r in p2p_results) if p2p_results else True
            resolved = all_f2p_passed and all_p2p_passed

            status = EvalStatus.PASSED if resolved else EvalStatus.FAILED

            return EvalResult(
                instance_id=instance.instance_id,
                status=status,
                fail_to_pass_results=f2p_results,
                pass_to_pass_results=p2p_results,
                resolved=resolved,
                duration_seconds=time.time() - start_time,
            )

        except Exception as e:
            logger.exception("Error evaluating %s", instance.instance_id)
            return EvalResult(
                instance_id=instance.instance_id,
                status=EvalStatus.ERROR,
                error_message=str(e),
                duration_seconds=time.time() - start_time,
            )

    def _run_tests(
        self,
        instance: EvalInstance,
        workspace,
        test_names: list[str],
    ) -> list[SingleTestResult]:
        """Run pytest tests and parse results."""
        if not test_names:
            return []

        cmd = f"python -m pytest {' '.join(test_names)} -x --tb=short 2>&1"
        logger.info("Running tests: %s", cmd[:120])

        exit_code, output = workspace.exec_in_container(cmd)

        return self._parse_test_output(test_names, exit_code, output)

    def _parse_test_output(
        self,
        test_names: list[str],
        exit_code: int,
        output: str,
    ) -> list[SingleTestResult]:
        """Parse pytest output for per-test pass/fail status."""
        results: list[SingleTestResult] = []

        for name in test_names:
            # Extract the test function name for matching
            # Handle formats like "test_file.py::test_func" or "test_file.py::Class::test_func"
            parts = name.split("::")
            method_name = parts[-1] if parts else name

            passed = None

            # pytest verbose output: "test_file.py::test_func PASSED" or "FAILED"
            if f"{method_name} PASSED" in output or f"{name} PASSED" in output:
                passed = True
            elif f"{method_name} FAILED" in output or f"{name} FAILED" in output:
                passed = False

            # Also check compact pytest: ".F" patterns aren't reliable,
            # so fall back to exit code
            if passed is None:
                passed = exit_code == 0

            results.append(SingleTestResult(
                test_name=name,
                passed=passed,
                output=output[-1000:] if len(output) > 1000 else output,
            ))

        return results
