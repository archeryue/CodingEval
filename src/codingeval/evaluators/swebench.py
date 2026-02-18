"""SWE-bench evaluator."""

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
from codingeval.docker.workspace import Workspace

logger = logging.getLogger(__name__)


def _build_test_command(instance: EvalInstance, test_names: list[str]) -> str:
    """Build the right test command for the repo.

    SWE-bench test IDs come in different formats:
      - Django:  "test_foo (module.path.TestClass)" → run via runtests.py
      - pytest:  "tests/test_foo.py::TestClass::test_method" → run via pytest

    Django repos have a tests/runtests.py script that needs to be used.
    """
    repo = instance.repo

    if "django" in repo.lower():
        # Django test format: "test_method (app_label.test_module.TestClass)"
        # Extract the dotted module paths for runtests.py
        modules = set()
        for name in test_names:
            # Parse "test_foo (model_fields.test_durationfield.TestValidation)"
            match = re.search(r"\(([^)]+)\)", name)
            if match:
                parts = match.group(1).rsplit(".", 1)  # "module.path.TestClass"
                modules.add(parts[0])  # "module.path"
            else:
                modules.add(name)

        module_list = " ".join(sorted(modules))
        return f"python tests/runtests.py --verbosity 2 --parallel 1 {module_list} 2>&1"

    # Default: pytest
    # Convert "test_method (module.TestClass)" to pytest node format if needed
    pytest_ids: list[str] = []
    for name in test_names:
        match = re.search(r"^(\w+)\s+\((.+)\.(\w+)\)$", name)
        if match:
            method, mod_path, cls = match.groups()
            file_path = mod_path.replace(".", "/") + ".py"
            pytest_ids.append(f"{file_path}::{cls}::{method}")
        else:
            pytest_ids.append(name)

    return f"python -m pytest {' '.join(pytest_ids)} -x --tb=short 2>&1"


class SWEBenchEvaluator(Evaluator):
    """Evaluator that applies patches and runs tests using the SWE-bench methodology."""

    @property
    def name(self) -> str:
        return "swebench"

    def evaluate(
        self,
        instance: EvalInstance,
        agent_output: AgentOutput,
        workspace: Workspace,
    ) -> EvalResult:
        """Evaluate by applying the test patch and running tests."""
        start_time = time.time()

        try:
            # For HOST-mode agents the working tree already contains the
            # agent's changes (the patch field is just a recording of what
            # changed).  We do NOT re-apply agent_output.patch — we only
            # apply the test patch on top of the agent's modifications.

            # Apply the test patch
            if instance.test_patch:
                success, output = workspace.apply_patch(instance.test_patch)
                if not success:
                    return EvalResult(
                        instance_id=instance.instance_id,
                        status=EvalStatus.ERROR,
                        error_message=f"Failed to apply test patch: {output}",
                        duration_seconds=time.time() - start_time,
                    )

            # Run fail_to_pass tests (should now pass after the fix)
            f2p_results = self._run_tests(instance, workspace, instance.fail_to_pass)

            # Run pass_to_pass tests (should still pass)
            p2p_results = self._run_tests(instance, workspace, instance.pass_to_pass)

            # Determine overall status
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
        workspace: Workspace,
        test_names: list[str],
    ) -> list[SingleTestResult]:
        """Run tests and parse results."""
        if not test_names:
            return []

        cmd = _build_test_command(instance, test_names)
        logger.info("Running tests: %s", cmd[:120])

        exit_code, output = workspace.exec_in_container(cmd)

        # For the overall batch we know pass/fail.  Try to determine
        # per-test results from the output.
        results = self._parse_test_output(test_names, exit_code, output)
        return results

    def _parse_test_output(
        self,
        test_names: list[str],
        exit_code: int,
        output: str,
    ) -> list[SingleTestResult]:
        """Parse test output to get per-test results.

        Looks for "test_name ... ok" or "test_name ... FAIL" patterns.
        Falls back to using exit_code for all tests if parsing fails.
        """
        results: list[SingleTestResult] = []

        for name in test_names:
            # Extract just the method name for matching
            method_match = re.match(r"(\w+)", name)
            method_name = method_match.group(1) if method_match else name

            # Look for Django-style "test_method ... ok" or "test_method ... FAIL"
            passed = None
            if f"{method_name} ..." in output:
                if re.search(rf"{re.escape(method_name)}\s+\.\.\.\s+ok", output):
                    passed = True
                elif re.search(rf"{re.escape(method_name)}\s+\.\.\.\s+FAIL", output):
                    passed = False
                elif re.search(rf"{re.escape(method_name)}\s+\.\.\.\s+ERROR", output):
                    passed = False

            # Also check pytest-style "PASSED" / "FAILED"
            if passed is None:
                if f"{method_name} PASSED" in output:
                    passed = True
                elif f"{method_name} FAILED" in output:
                    passed = False

            # Fallback: use overall exit code
            if passed is None:
                passed = exit_code == 0

            results.append(SingleTestResult(
                test_name=name,
                passed=passed,
                output=output[-1000:] if len(output) > 1000 else output,
            ))

        return results
