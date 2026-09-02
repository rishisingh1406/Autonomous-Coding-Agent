
from pathlib import Path

import pytest

from app.agent.executor import Executor
from app.agent.planner import FileEdit, FixPlan
from app.sandbox.manager import SandboxManager


@pytest.fixture
def workspace(tmp_path: Path) -> Path:
    repo = tmp_path / "repo"
    repo.mkdir()

    (repo / "app.py").write_text(
        """
def add(a, b):
    return a + b
""".strip(),
        encoding="utf-8",
    )

    return repo


def test_executor_applies_edit(
    workspace,
):
    plan = FixPlan(
        summary="Fix add function",
        problem="Add function needs fixing.",
        target_files=["app.py"],
        changes=[
            "Fix the add function.",
        ],
        tests_to_run=[],
        rationale="app.py contains the implementation.",
        edits=[
            FileEdit(
                file_path="app.py",
                old_text="return a + b",
                new_text="return a + b + 1",
            ),
        ],
    )

    executor = Executor(
        sandbox_manager=SandboxManager()
    )

    result = executor.execute(
        plan=plan,
        workspace=workspace,
    )

    assert result.success
    assert len(result.edits) == 1
    assert result.edits[0].success

    content = (
        workspace / "app.py"
    ).read_text(
        encoding="utf-8"
    )

    assert "return a + b + 1" in content


def test_executor_rejects_missing_target_file(
    workspace,
):
    plan = FixPlan(
        summary="Fix missing file",
        problem="A file needs fixing.",
        target_files=["missing.py"],
        changes=[
            "Fix missing.py.",
        ],
        tests_to_run=[],
        rationale="Test.",
        edits=[
            FileEdit(
                file_path="missing.py",
                old_text="anything",
                new_text="replacement",
            ),
        ],
    )

    executor = Executor(
        sandbox_manager=SandboxManager()
    )

    result = executor.execute(
        plan=plan,
        workspace=workspace,
    )

    assert not result.success
    assert len(result.edits) == 1
    assert not result.edits[0].success
    assert "does not exist" in result.edits[0].error


def test_executor_rejects_path_escape(
    workspace,
):
    plan = FixPlan(
        summary="Malicious path",
        problem="Test path validation.",
        target_files=[
            "../../outside.py",
        ],
        changes=[
            "Modify outside file.",
        ],
        tests_to_run=[],
        rationale="Security test.",
        edits=[
            FileEdit(
                file_path="../../outside.py",
                old_text="secret",
                new_text="modified",
            ),
        ],
    )

    executor = Executor(
        sandbox_manager=SandboxManager()
    )

    result = executor.execute(
        plan=plan,
        workspace=workspace,
    )

    assert not result.success
    assert len(result.edits) == 1
    assert not result.edits[0].success
    assert "outside workspace" in result.edits[0].error


def test_executor_handles_multiple_target_files(
    workspace,
):
    (workspace / "utils.py").write_text(
        "def helper():\n    return 1\n",
        encoding="utf-8",
    )

    plan = FixPlan(
        summary="Update two files",
        problem="Two files need changes.",
        target_files=[
            "app.py",
            "utils.py",
        ],
        changes=[
            "Update app.py.",
            "Update utils.py.",
        ],
        tests_to_run=[],
        rationale="Both files are relevant.",
        edits=[
            FileEdit(
                file_path="app.py",
                old_text="return a + b",
                new_text="return a + b + 1",
            ),
            FileEdit(
                file_path="utils.py",
                old_text="return 1",
                new_text="return 2",
            ),
        ],
    )

    executor = Executor(
        sandbox_manager=SandboxManager()
    )

    result = executor.execute(
        plan=plan,
        workspace=workspace,
    )

    assert result.success
    assert len(result.edits) == 2

    assert all(
        edit.success
        for edit in result.edits
    )

    app_content = (
        workspace / "app.py"
    ).read_text(
        encoding="utf-8"
    )

    utils_content = (
        workspace / "utils.py"
    ).read_text(
        encoding="utf-8"
    )

    assert "return a + b + 1" in app_content
    assert "return 2" in utils_content


def test_executor_rejects_missing_old_text(
    workspace,
):
    plan = FixPlan(
        summary="Invalid edit",
        problem="Test edit validation.",
        target_files=["app.py"],
        changes=[
            "Apply an invalid edit.",
        ],
        tests_to_run=[],
        rationale="Testing safety.",
        edits=[
            FileEdit(
                file_path="app.py",
                old_text="this does not exist",
                new_text="replacement",
            ),
        ],
    )

    executor = Executor(
        sandbox_manager=SandboxManager()
    )

    result = executor.execute(
        plan=plan,
        workspace=workspace,
    )

    assert not result.success
    assert len(result.edits) == 1
    assert not result.edits[0].success
    assert "not found" in result.edits[0].error


def test_executor_rejects_ambiguous_edit(
    workspace,
):
    target = workspace / "app.py"

    target.write_text(
        """
def first():
    return value


def second():
    return value
""".strip(),
        encoding="utf-8",
    )

    plan = FixPlan(
        summary="Ambiguous edit",
        problem="Test duplicate match protection.",
        target_files=["app.py"],
        changes=[
            "Replace one return statement.",
        ],
        tests_to_run=[],
        rationale="Testing safety.",
        edits=[
            FileEdit(
                file_path="app.py",
                old_text="return value",
                new_text="return updated",
            ),
        ],
    )

    executor = Executor(
        sandbox_manager=SandboxManager()
    )

    result = executor.execute(
        plan=plan,
        workspace=workspace,
    )

    assert not result.success
    assert len(result.edits) == 1
    assert not result.edits[0].success
    assert "multiple times" in result.edits[0].error


def test_executor_runs_planned_tests(
    workspace,
):
    (workspace / "test_app.py").write_text(
        """
from app import add


def test_add():
    assert add(2, 3) == 5
""".strip(),
        encoding="utf-8",
    )

    plan = FixPlan(
        summary="Test add",
        problem="Verify add.",
        target_files=["app.py"],
        changes=[
            "No change required.",
        ],
        tests_to_run=[
            "test_app.py",
        ],
        rationale="Verify implementation.",
    )

    executor = Executor(
        sandbox_manager=SandboxManager()
    )

    result = executor.execute(
        plan=plan,
        workspace=workspace,
    )

    assert len(result.test_results) == 1

    # This test requires Docker.
    if result.test_results[0].success:
        assert result.success
