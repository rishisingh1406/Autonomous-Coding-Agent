from __future__ import annotations

import subprocess
from pathlib import Path

from app.agent.executor import (
    EditResult,
    ExecutionResult,
)
from app.agent.reflection import (
    ReflectionIteration,
    ReflectionResult,
)
from app.github.github_client import (
    PullRequestResult,
)
from app.github.pr_manager import (
    PRManagerResult,
)
from app.github.workflow import PRWorkflow
from app.sandbox.models import CommandResult


class FakePRManager:
    """
    Fake PRManager used to verify that PRWorkflow
    constructs the correct PRContext.
    """

    def __init__(self):
        self.context = None

    def create_pull_request(self, context):
        self.context = context

        return PRManagerResult(
            success=True,
            pull_request=PullRequestResult(
                success=True,
                operation="create_pull_request",
                number=42,
                url="https://github.com/test/repo/pull/42",
            ),
        )


def create_successful_reflection() -> ReflectionResult:
    """
    Build a realistic successful ReflectionResult
    containing actual pytest-style execution data.
    """

    command_result = CommandResult(
        command="pytest tests/",
        return_code=0,
        stdout="3 passed in 0.15s",
        stderr="",
    )

    execution = ExecutionResult(
        success=True,
        edits=[
            EditResult(
                file_path="app.py",
                success=True,
            )
        ],
        test_results=[command_result],
    )

    return ReflectionResult(
        success=True,
        iterations=[
            ReflectionIteration(
                iteration=1,
                execution=execution,
            )
        ],
    )


def run_git(
    repo: Path,
    *args: str,
) -> subprocess.CompletedProcess:
    """
    Run a Git command inside the test repository.
    """

    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def commit(
    repo: Path,
    message: str,
) -> None:
    """
    Create a Git commit with test-specific identity.
    """

    run_git(repo, "add", ".")

    run_git(
        repo,
        "-c",
        "user.name=Test User",
        "-c",
        "user.email=test@example.com",
        "commit",
        "-m",
        message,
    )


def test_pr_workflow_creates_complete_pr_context(
    tmp_path: Path,
):
    """
    Verify the complete Day 109 PR preparation flow:

        ReflectionResult
            ↓
        DiffSummarizer
            ↓
        PytestResultsFormatter
            ↓
        PRContext
            ↓
        PRManager
    """

    repo = tmp_path / "repo"
    repo.mkdir()

    # ---------------------------------------------------------
    # Create initial repository state on main.
    # ---------------------------------------------------------

    run_git(
        repo,
        "init",
        "-b",
        "main",
    )

    (repo / "app.py").write_text(
        "print('hello')\n",
        encoding="utf-8",
    )

    commit(
        repo,
        "initial commit",
    )

    # ---------------------------------------------------------
    # Create the agent branch.
    #
    # This is important because DiffSummarizer compares:
    #
    #     main...HEAD
    #
    # HEAD must therefore point to the agent branch.
    # ---------------------------------------------------------

    run_git(
        repo,
        "checkout",
        "-b",
        "agent/fix",
    )

    # ---------------------------------------------------------
    # Simulate the changes produced by the coding agent.
    # ---------------------------------------------------------

    (repo / "app.py").write_text(
        "print('fixed')\n",
        encoding="utf-8",
    )

    commit(
        repo,
        "agent fix",
    )

    # ---------------------------------------------------------
    # Create fake PR manager.
    # ---------------------------------------------------------

    fake_manager = FakePRManager()

    workflow = PRWorkflow(
        pr_manager=fake_manager,
    )

    # ---------------------------------------------------------
    # Execute the workflow.
    # ---------------------------------------------------------

    result = workflow.create_pull_request(
        reflection_result=create_successful_reflection(),
        workspace=repo,
        owner="test",
        repo="repo",
        branch="agent/fix",
        base_branch="main",
        title="Fix application",
        summary="Fixed the application output.",
    )

    # ---------------------------------------------------------
    # Verify PR result.
    # ---------------------------------------------------------

    assert result.success is True

    assert result.pull_request is not None

    assert (
        result.pull_request.url
        == "https://github.com/test/repo/pull/42"
    )

    # ---------------------------------------------------------
    # Verify PRContext.
    # ---------------------------------------------------------

    context = fake_manager.context

    assert context is not None

    assert context.owner == "test"

    assert context.repo == "repo"

    assert context.branch == "agent/fix"

    assert context.base_branch == "main"

    assert context.title == "Fix application"

    assert (
        context.summary
        == "Fixed the application output."
    )

    # ---------------------------------------------------------
    # Verify generated diff summary.
    # ---------------------------------------------------------

    assert "Files changed: 1" in context.diff_summary

    assert "Insertions: 1" in context.diff_summary

    assert "Deletions: 1" in context.diff_summary

    # ---------------------------------------------------------
    # Verify pytest results came from the
    # existing ReflectionResult.
    # ---------------------------------------------------------

    assert "Iteration 1" in context.test_results

    assert (
        "Test command 1: PASSED"
        in context.test_results
    )

    assert (
        "Command: pytest tests/"
        in context.test_results
    )

    assert (
        "Return code: 0"
        in context.test_results
    )

    assert (
        "3 passed in 0.15s"
        in context.test_results
    )


def test_pr_workflow_rejects_failed_reflection(
    tmp_path: Path,
):
    """
    A pull request must never be created when the
    reflection loop has failed.
    """

    fake_manager = FakePRManager()

    workflow = PRWorkflow(
        pr_manager=fake_manager,
    )

    reflection = ReflectionResult(
        success=False,
        iterations=[],
        error="Tests failed.",
    )

    result = workflow.create_pull_request(
        reflection_result=reflection,
        workspace=tmp_path,
        owner="test",
        repo="repo",
        branch="agent/fix",
        base_branch="main",
        title="Fix application",
        summary="Attempted fix.",
    )

    assert result.success is False

    assert (
        "reflection loop did not succeed"
        in result.error
    )

    assert fake_manager.context is None
