from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path

from app.agent.reflection import ReflectionResult
from app.github.diff import DiffSummarizer
from app.github.pr_manager import (
    PRContext,
    PRManager,
    PRManagerResult,
)
from app.github.test_results import PytestResultsFormatter


@dataclass
class PRWorkflow:
    """
    Orchestrates PR creation from a successful reflection result.

    Responsibilities:

        ReflectionResult
            ↓
        DiffSummarizer
            ↓
        PytestResultsFormatter
            ↓
        PRContext
            ↓
        PRManager
            ↓
        Pull Request
    """

    pr_manager: PRManager
    diff_summarizer: DiffSummarizer | None = None
    test_results_formatter: PytestResultsFormatter | None = None

    def __post_init__(self) -> None:
        if self.diff_summarizer is None:
            self.diff_summarizer = DiffSummarizer()

        if self.test_results_formatter is None:
            self.test_results_formatter = (
                PytestResultsFormatter()
            )

    def create_pull_request(
        self,
        *,
        reflection_result: ReflectionResult,
        workspace: str | Path,
        owner: str,
        repo: str,
        branch: str,
        base_branch: str,
        title: str,
        summary: str,
    ) -> PRManagerResult:
        """
        Build the PR context from the existing reflection result
        and create the pull request.

        Tests are NOT executed here.

        The test results come directly from the ReflectionResult
        produced by the existing reflection loop.
        """

        if not reflection_result.success:
            return PRManagerResult(
                success=False,
                error=(
                    "Cannot create pull request because "
                    "the reflection loop did not succeed."
                ),
            )

        workspace = Path(workspace).resolve()

        if not workspace.exists():
            raise FileNotFoundError(
                f"Workspace does not exist: {workspace}"
            )

        if not workspace.is_dir():
            raise ValueError(
                f"Workspace is not a directory: {workspace}"
            )

        assert self.diff_summarizer is not None
        assert self.test_results_formatter is not None

        try:
            diff = self.diff_summarizer.summarize(
                repo_path=workspace,
                base_branch=base_branch,
            )

            test_results = (
                self.test_results_formatter.format(
                    reflection_result
                )
            )

            context = PRContext(
                owner=owner,
                repo=repo,
                branch=branch,
                base_branch=base_branch,
                title=title,
                summary=summary,
                diff_summary=diff.as_text(),
                test_results=test_results,
            )

            return self.pr_manager.create_pull_request(
                context
            )

        except Exception as exc:
            return PRManagerResult(
                success=False,
                error=(
                    "Failed to prepare pull request: "
                    f"{exc}"
                ),
            )