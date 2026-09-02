from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.agent.planner import FileEdit, FixPlan
from app.sandbox.manager import SandboxManager
from app.sandbox.models import CommandResult


@dataclass
class EditResult:
    """
    Result of applying one proposed edit.
    """

    file_path: str
    success: bool
    error: str | None = None


@dataclass
class ExecutionResult:
    """
    Result of executing a complete FixPlan.
    """

    success: bool
    edits: list[EditResult]
    test_results: list[CommandResult]
    error: str | None = None


class Executor:
    """
    Applies a FixPlan inside an isolated sandbox.

    Planner decides WHAT.
    Executor decides HOW.
    SandboxManager decides WHERE.
    """

    def __init__(
        self,
        sandbox_manager: SandboxManager | None = None,
    ):
        self.sandbox_manager = (
            sandbox_manager
            or SandboxManager()
        )

    def execute(
        self,
        plan: FixPlan,
        workspace: str | Path,
    ) -> ExecutionResult:
        """
        Apply the plan and run its tests.
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

        edits = self._apply_edits(
            plan=plan,
            workspace=workspace,
        )

        failed_edits = [
            edit
            for edit in edits
            if not edit.success
        ]

        if failed_edits:
            return ExecutionResult(
                success=False,
                edits=edits,
                test_results=[],
                error="One or more edits failed.",
            )

        test_results = self._run_tests(
            plan=plan,
            workspace=workspace,
        )

        tests_passed = all(
            result.success
            for result in test_results
        )

        return ExecutionResult(
            success=tests_passed,
            edits=edits,
            test_results=test_results,
            error=None
            if tests_passed
            else "One or more tests failed.",
        )

    def _apply_edits(
        self,
        plan: FixPlan,
        workspace: Path,
    ) -> list[EditResult]:
        """
        Apply every deterministic FileEdit.

        Each edit:
        1. Resolves the target safely.
        2. Verifies the file exists.
        3. Verifies old_text exists exactly once.
        4. Replaces old_text with new_text.
        """

        results: list[EditResult] = []

        for edit in plan.edits:

            target = self._resolve_target(
                workspace=workspace,
                file_path=edit.file_path,
            )

            if target is None:
                results.append(
                    EditResult(
                        file_path=edit.file_path,
                        success=False,
                        error="Target file is outside workspace.",
                    )
                )
                continue

            if not target.exists():
                results.append(
                    EditResult(
                        file_path=edit.file_path,
                        success=False,
                        error="Target file does not exist.",
                    )
                )
                continue

            try:
                content = target.read_text(
                    encoding="utf-8"
                )

            except UnicodeDecodeError:
                results.append(
                    EditResult(
                        file_path=edit.file_path,
                        success=False,
                        error="Target file is not valid UTF-8.",
                    )
                )
                continue

            occurrences = content.count(
                edit.old_text
            )

            if occurrences == 0:
                results.append(
                    EditResult(
                        file_path=edit.file_path,
                        success=False,
                        error=(
                            "The expected old_text was not "
                            "found in the target file."
                        ),
                    )
                )
                continue

            if occurrences > 1:
                results.append(
                    EditResult(
                        file_path=edit.file_path,
                        success=False,
                        error=(
                            "The expected old_text occurs "
                            "multiple times; refusing ambiguous edit."
                        ),
                    )
                )
                continue

            updated_content = content.replace(
                edit.old_text,
                edit.new_text,
                1,
            )

            target.write_text(
                updated_content,
                encoding="utf-8",
            )

            results.append(
                EditResult(
                    file_path=edit.file_path,
                    success=True,
                )
            )

        return results

    def _run_tests(
        self,
        plan: FixPlan,
        workspace: Path,
    ) -> list[CommandResult]:
        """
        Run the tests specified by the plan.
        """

        results: list[CommandResult] = []

        for test in plan.tests_to_run:

            result = self.sandbox_manager.run(
                workspace=workspace,
                command=f"pytest {test}",
            )

            results.append(result)

        return results

    @staticmethod
    def _resolve_target(
        workspace: Path,
        file_path: str,
    ) -> Path | None:
        """
        Resolve a repository-relative path safely.
        """

        workspace = workspace.resolve()

        target = (
            workspace / file_path
        ).resolve()

        try:
            target.relative_to(workspace)
        except ValueError:
            return None

        return target