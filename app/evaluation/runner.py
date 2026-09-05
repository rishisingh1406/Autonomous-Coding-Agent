from __future__ import annotations

import time
from dataclasses import dataclass
from pathlib import Path
from shutil import copytree, rmtree

from app.agent.reflection import ReflectionResult
from app.evaluation.fix_plans import EvaluationFixPlanProvider
from app.evaluation.models import (
    EvaluationIssue,
    EvaluationReport,
    EvaluationResult,
)
from app.repo.context import RepoRetriever
from app.repo.indexer import RepoIndexer
from app.sandbox.manager import SandboxManager


@dataclass
class EvaluationRunner:
    """
    Runs coding issues end-to-end against isolated
    evaluation repositories.

    Pipeline:

        EvaluationIssue
              ↓
        Fresh repository
              ↓
        RepoIndexer
              ↓
        RepoRetriever
              ↓
        Planner
              ↓
        EvaluationFixPlanProvider
              ↓
        Executable FixPlan
              ↓
        ReflectionLoop
              ↓
        Docker + Pytest
              ↓
        Independent verification
              ↓
        EvaluationResult
    """

    planner: object
    reflection_loop: object
    sandbox_manager: SandboxManager

    fixture_repo: str | Path
    workspace_root: str | Path

    top_k: int = 5

    fix_provider: EvaluationFixPlanProvider | None = None

    def __post_init__(self) -> None:
        self.fixture_repo = Path(
            self.fixture_repo
        ).resolve()

        self.workspace_root = Path(
            self.workspace_root
        ).resolve()

        if not self.fixture_repo.exists():
            raise FileNotFoundError(
                f"Fixture repository does not exist: "
                f"{self.fixture_repo}"
            )

        if not self.fixture_repo.is_dir():
            raise ValueError(
                f"Fixture repository is not a directory: "
                f"{self.fixture_repo}"
            )

        if self.top_k < 1:
            raise ValueError(
                "top_k must be at least 1."
            )

        self.workspace_root.mkdir(
            parents=True,
            exist_ok=True,
        )

        if self.fix_provider is None:
            self.fix_provider = (
                EvaluationFixPlanProvider()
            )

    def run_issue(
        self,
        issue: EvaluationIssue,
    ) -> EvaluationResult:
        """
        Run one issue from repository retrieval
        through reflection and independent verification.
        """

        start_time = time.perf_counter()

        workspace = (
            self.workspace_root
            / issue.issue_id
        )

        try:
            # --------------------------------------------------
            # 1. Create a completely fresh repository.
            # --------------------------------------------------

            self._prepare_workspace(
                workspace
            )

            # --------------------------------------------------
            # 2. Index the repository.
            # --------------------------------------------------

            documents = RepoIndexer().index(
                workspace
            )

            # --------------------------------------------------
            # 3. Retrieve relevant repository context.
            # --------------------------------------------------

            retriever = RepoRetriever(
                documents
            )

            context = retriever.search_issue(
                title=issue.title,
                body=issue.body,
                top_k=self.top_k,
            )

            if not context:
                return EvaluationResult(
                    issue_id=issue.issue_id,
                    title=issue.title,
                    success=False,
                    duration_seconds=(
                        time.perf_counter()
                        - start_time
                    ),
                    error=(
                        "Repository retrieval returned "
                        "no relevant context."
                    ),
                )

            # --------------------------------------------------
            # 4. Create the initial FixPlan.
            # --------------------------------------------------

            plan = self.planner.plan(
                issue_title=issue.title,
                issue_body=issue.body,
                context=context,
            )

            # --------------------------------------------------
            # 5. Convert the benchmark plan into an
            #    executable FixPlan containing FileEdits.
            # --------------------------------------------------

            executable_plan = (
                self.fix_provider.apply(
                    plan=plan,
                    issue=issue,
                )
            )

            # --------------------------------------------------
            # 6. Configure an issue-specific FixGenerator.
            #
            #    ReflectionLoop expects a FixGenerator for
            #    corrective iterations.
            # --------------------------------------------------

            self.reflection_loop.fix_generator = (
                EvaluationFixPlanProvider(
                    issue=issue,
                )
            )

            # --------------------------------------------------
            # 7. Run:
            #
            #    edit → pytest → reflection → fix
            # --------------------------------------------------

            reflection_result = (
                self.reflection_loop.run(
                    initial_plan=executable_plan,
                    workspace=workspace,
                )
            )

            # --------------------------------------------------
            # 8. Independently verify the final workspace.
            #
            #    This verification is intentionally outside
            #    ReflectionLoop.
            # --------------------------------------------------

            if reflection_result.success:

                verification = self._verify(
                    issue=issue,
                    workspace=workspace,
                )

                if not verification.success:

                    verification_output = (
                        verification.stderr
                        or verification.stdout
                    )

                    reflection_result = ReflectionResult(
                        success=False,
                        iterations=(
                            reflection_result.iterations
                        ),
                        max_iterations=(
                            reflection_result.max_iterations
                        ),
                        error=(
                            "Independent verification "
                            "failed: "
                            f"{verification_output}"
                        ),
                    )

            duration = (
                time.perf_counter()
                - start_time
            )

            # --------------------------------------------------
            # 9. Convert execution into benchmark metrics.
            # --------------------------------------------------

            return self._build_result(
                issue=issue,
                reflection_result=reflection_result,
                duration=duration,
                workspace=workspace,
            )

        except Exception as exc:

            return EvaluationResult(
                issue_id=issue.issue_id,
                title=issue.title,
                success=False,
                duration_seconds=(
                    time.perf_counter()
                    - start_time
                ),
                error=str(exc),
            )

    def run(
        self,
        issues: list[EvaluationIssue],
    ) -> EvaluationReport:
        """
        Run all issues independently.
        """

        results: list[EvaluationResult] = []

        for issue in issues:

            result = self.run_issue(
                issue
            )

            results.append(
                result
            )

        return EvaluationReport(
            results=results
        )

    def _prepare_workspace(
        self,
        workspace: Path,
    ) -> None:
        """
        Create a completely fresh repository copy.

        Every issue starts from the same initial state.
        """

        if workspace.exists():
            rmtree(workspace)

        copytree(
            self.fixture_repo,
            workspace,
        )

    def _verify(
        self,
        issue: EvaluationIssue,
        workspace: Path,
    ):
        """
        Independently verify the final workspace.

        This deliberately runs outside ReflectionLoop so
        benchmark success is not based solely on the loop's
        own execution result.
        """

        if not issue.expected_tests:

            return self.sandbox_manager.run(
                workspace=workspace,
                command="pytest -v",
            )

        test_commands = []

        for test in issue.expected_tests:

            test_commands.append(
                f"pytest {test} -v"
            )

        command = " && ".join(
            test_commands
        )

        return self.sandbox_manager.run(
            workspace=workspace,
            command=command,
        )

    @staticmethod
    def _get_changed_files(
        workspace: Path,
        reflection_result: ReflectionResult,
    ) -> list[str]:
        """
        Determine files changed during the evaluation.

        Successful edits recorded by the reflection layer
        are used as the source of truth.
        """

        changed_files: list[str] = []

        for iteration in reflection_result.iterations:

            for edit in iteration.execution.edits:

                if (
                    edit.success
                    and edit.file_path
                    not in changed_files
                ):
                    changed_files.append(
                        edit.file_path
                    )

        return changed_files

    @classmethod
    def _build_result(
        cls,
        *,
        issue: EvaluationIssue,
        reflection_result: ReflectionResult,
        duration: float,
        workspace: Path,
    ) -> EvaluationResult:
        """
        Convert the reflection result into benchmark metrics.
        """

        test_output_parts: list[str] = []

        for iteration in reflection_result.iterations:

            execution = iteration.execution

            for command_result in (
                execution.test_results
            ):

                if command_result.stdout:

                    test_output_parts.append(
                        command_result.stdout.strip()
                    )

                if command_result.stderr:

                    test_output_parts.append(
                        command_result.stderr.strip()
                    )

        test_output = "\n".join(
            part
            for part in test_output_parts
            if part
        )

        return EvaluationResult(
            issue_id=issue.issue_id,
            title=issue.title,
            success=reflection_result.success,
            iterations=(
                reflection_result.iteration_count
            ),
            duration_seconds=duration,
            error=reflection_result.error,
            test_output=test_output,
            changed_files=cls._get_changed_files(
                workspace=workspace,
                reflection_result=reflection_result,
            ),
        )