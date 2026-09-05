from __future__ import annotations

from dataclasses import dataclass

from app.agent.reflection import ReflectionResult
from app.sandbox.models import CommandResult


@dataclass
class PytestResultsFormatter:
    """
    Converts actual sandbox test execution results
    into a readable format for a pull request description.
    """

    def format(
        self,
        reflection_result: ReflectionResult,
    ) -> str:
        if not reflection_result.iterations:
            return "No tests were executed."

        output: list[str] = []

        for iteration in reflection_result.iterations:
            output.append(
                f"Iteration {iteration.iteration}"
            )

            execution = iteration.execution

            if execution.error:
                output.append(
                    f"Execution error: {execution.error}"
                )

            if not execution.test_results:
                output.append(
                    "No test commands were executed."
                )
                continue

            for index, result in enumerate(
                execution.test_results,
                start=1,
            ):
                output.append(
                    self._format_command_result(
                        index=index,
                        result=result,
                    )
                )

        return "\n".join(output)

    @staticmethod
    def _format_command_result(
        *,
        index: int,
        result: CommandResult,
    ) -> str:
        status = (
            "PASSED"
            if result.success
            else "FAILED"
        )

        output: list[str] = [
            f"Test command {index}: {status}",
            f"Command: {result.command}",
            f"Return code: {result.return_code}",
        ]

        if result.timed_out:
            output.append("Timed out: True")

        if result.stdout:
            output.append(
                f"stdout:\n{result.stdout.strip()}"
            )

        if result.stderr:
            output.append(
                f"stderr:\n{result.stderr.strip()}"
            )

        return "\n".join(output)
