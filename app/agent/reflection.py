from __future__ import annotations

from dataclasses import dataclass, field

from app.agent.executor import ExecutionResult


@dataclass
class ReflectionIteration:
    """
    Result of one edit -> test iteration.
    """

    iteration: int
    execution: ExecutionResult

    @property
    def success(self) -> bool:
        return self.execution.success

    @property
    def failure_output(self) -> str:
        """
        Combine structured execution errors with
        stdout/stderr from all test commands.

        This becomes the input to the corrective
        FixGenerator.
        """

        output: list[str] = []

        if self.execution.error:
            output.append(
                f"Execution error: {self.execution.error}"
            )

        for result in self.execution.test_results:

            if result.stdout:
                output.append(
                    f"stdout:\n{result.stdout}"
                )

            if result.stderr:
                output.append(
                    f"stderr:\n{result.stderr}"
                )

        return "\n".join(output)


@dataclass
class FailureFeedback:
    """
    Structured failure information passed to the
    corrective FixGenerator.
    """

    iteration: int
    error: str | None
    test_output: str

    @property
    def has_output(self) -> bool:
        return bool(self.test_output.strip())


@dataclass
class ReflectionResult:
    """
    Final result of the bounded edit -> test -> fix loop.
    """

    success: bool

    iterations: list[ReflectionIteration] = field(
        default_factory=list
    )

    max_iterations: int = 3

    error: str | None = None

    @property
    def iteration_count(self) -> int:
        return len(self.iterations)

    @property
    def last_iteration(
        self,
    ) -> ReflectionIteration | None:
        if not self.iterations:
            return None

        return self.iterations[-1]