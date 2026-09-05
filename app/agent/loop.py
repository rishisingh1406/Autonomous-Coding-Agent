from __future__ import annotations

from pathlib import Path

from app.agent.executor import Executor
from app.agent.fixer import FixGenerator
from app.agent.planner import FixPlan
from app.agent.reflection import (
    FailureFeedback,
    ReflectionIteration,
    ReflectionResult,
)


class ReflectionLoop:
    """
    Coordinates the bounded:

        edit -> test -> failure analysis -> fix

    reflection cycle.

    Responsibilities:

        ReflectionLoop
            orchestration + iteration control

        Executor
            deterministic edits + test execution

        FixGenerator
            failure analysis + next FixPlan

        SandboxManager
            isolated Docker execution

        Planner
            initial FixPlan creation
    """

    def __init__(
        self,
        executor: Executor | None = None,
        fix_generator: FixGenerator | None = None,
        max_iterations: int = 3,
    ):
        if max_iterations < 1:
            raise ValueError(
                "max_iterations must be at least 1."
            )

        self.executor = executor or Executor()

        self.fix_generator = fix_generator

        self.max_iterations = max_iterations

    def run(
        self,
        initial_plan: FixPlan,
        workspace: str | Path,
    ) -> ReflectionResult:
        """
        Execute the bounded edit -> test -> fix loop.

        The loop terminates when:

        1. Tests pass.
        2. max_iterations is reached.
        3. FixPlan generation fails.
        """

        workspace = Path(workspace).resolve()

        if not workspace.exists():
            raise FileNotFoundError(
                f"Workspace does not exist: {workspace}"
            )

        if not workspace.is_dir():
            raise ValueError(
                f"Workspace is not a directory: {workspace}"
            )

        iterations: list[ReflectionIteration] = []

        current_plan = initial_plan

        for iteration_number in range(
            1,
            self.max_iterations + 1,
        ):

            execution = self.executor.execute(
                plan=current_plan,
                workspace=workspace,
            )

            iteration = ReflectionIteration(
                iteration=iteration_number,
                execution=execution,
            )

            iterations.append(iteration)

            if execution.success:
                return ReflectionResult(
                    success=True,
                    iterations=iterations,
                    max_iterations=self.max_iterations,
                )

            if iteration_number >= self.max_iterations:
                return ReflectionResult(
                    success=False,
                    iterations=iterations,
                    max_iterations=self.max_iterations,
                    error=(
                        "Maximum reflection iterations "
                        "reached without passing tests."
                    ),
                )

            if self.fix_generator is None:
                return ReflectionResult(
                    success=False,
                    iterations=iterations,
                    max_iterations=self.max_iterations,
                    error=(
                        "Execution failed, but no "
                        "FixGenerator was configured."
                    ),
                )

            feedback = FailureFeedback(
                iteration=iteration_number,
                error=execution.error,
                test_output=iteration.failure_output,
            )

            try:
                current_plan = self.fix_generator.generate(
                    plan=current_plan,
                    feedback=feedback,
                )

            except Exception as exc:
                return ReflectionResult(
                    success=False,
                    iterations=iterations,
                    max_iterations=self.max_iterations,
                    error=(
                        "Failed to generate corrective "
                        f"FixPlan: {exc}"
                    ),
                )

        return ReflectionResult(
            success=False,
            iterations=iterations,
            max_iterations=self.max_iterations,
            error="Reflection loop exited unexpectedly.",
        )