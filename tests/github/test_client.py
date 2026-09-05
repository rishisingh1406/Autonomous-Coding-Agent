from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from app.github.client import GitClient


def run_git(
    repo: Path,
    *args: str,
) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        capture_output=True,
        text=True,
        check=True,
    )


def configure_git(repo: Path) -> None:
    run_git(
        repo,
        "config",
        "user.name",
        "Autonomous Coding Agent",
    )

    run_git(
        repo,
        "config",
        "user.email",
        "agent@example.com",
    )


@pytest.fixture
def git_repository(
    tmp_path: Path,
) -> tuple[Path, Path]:
    remote = tmp_path / "remote.git"

    subprocess.run(
        [
            "git",
            "init",
            "--bare",
            str(remote),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    repo = tmp_path / "repo"

    subprocess.run(
        [
            "git",
            "init",
            str(repo),
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    configure_git(repo)

    initial_file = repo / "README.md"

    initial_file.write_text(
        "# Autonomous Coding Agent\n",
        encoding="utf-8",
    )

    run_git(
        repo,
        "add",
        "README.md",
    )

    run_git(
        repo,
        "commit",
        "-m",
        "initial commit",
    )

    run_git(
        repo,
        "remote",
        "add",
        "origin",
        str(remote),
    )

    run_git(
        repo,
        "branch",
        "-M",
        "main",
    )

    run_git(
        repo,
        "push",
        "-u",
        "origin",
        "main",
    )

    return repo, remote


def test_create_branch(
    git_repository: tuple[Path, Path],
):
    repo, _ = git_repository

    client = GitClient()

    result = client.create_branch(
        repo_path=repo,
        branch_name="agent/issue-123-fix",
    )

    assert result.success

    branch = client.get_current_branch(repo)

    assert branch == "agent/issue-123-fix"


def test_commit_changes(
    git_repository: tuple[Path, Path],
):
    repo, _ = git_repository

    client = GitClient()

    file_path = repo / "app.py"

    file_path.write_text(
        "def add(a, b):\n"
        "    return a + b\n",
        encoding="utf-8",
    )

    result = client.commit_changes(
        repo_path=repo,
        message="fix: add add function",
    )

    assert result.success

    log = run_git(
        repo,
        "log",
        "-1",
        "--pretty=%s",
    )

    assert (
        log.stdout.strip()
        == "fix: add add function"
    )


def test_commit_changes_rejects_empty_commit(
    git_repository: tuple[Path, Path],
):
    repo, _ = git_repository

    client = GitClient()

    result = client.commit_changes(
        repo_path=repo,
        message="nothing changed",
    )

    assert not result.success

    assert result.error == "No changes to commit."


def test_push_branch(
    git_repository: tuple[Path, Path],
):
    repo, remote = git_repository

    client = GitClient()

    branch_name = "agent/issue-123-fix"

    create_result = client.create_branch(
        repo_path=repo,
        branch_name=branch_name,
    )

    assert create_result.success

    file_path = repo / "app.py"

    file_path.write_text(
        "print('hello')\n",
        encoding="utf-8",
    )

    commit_result = client.commit_changes(
        repo_path=repo,
        message="fix: add generated implementation",
    )

    assert commit_result.success

    push_result = client.push_branch(
        repo_path=repo,
        branch_name=branch_name,
    )

    assert push_result.success

    refs = subprocess.run(
        [
            "git",
            "--git-dir",
            str(remote),
            "branch",
        ],
        capture_output=True,
        text=True,
        check=True,
    )

    assert branch_name in refs.stdout


def test_full_branch_commit_push_flow(
    git_repository: tuple[Path, Path],
):
    repo, remote = git_repository

    client = GitClient()

    branch_name = "agent/issue-456-fix"

    branch_result = client.create_branch(
        repo_path=repo,
        branch_name=branch_name,
    )

    assert branch_result.success

    file_path = repo / "solution.py"

    file_path.write_text(
        "def solve():\n"
        "    return 42\n",
        encoding="utf-8",
    )

    commit_result = client.commit_changes(
        repo_path=repo,
        message="fix: implement issue 456",
    )

    assert commit_result.success

    push_result = client.push_branch(
        repo_path=repo,
        branch_name=branch_name,
    )

    assert push_result.success

    branch = client.get_current_branch(repo)

    assert branch == branch_name

    refs = subprocess.run(
        [
            "git",
            "--git-dir",
            str(remote),
            "show-ref",
            "--verify",
            f"refs/heads/{branch_name}",
        ],
        capture_output=True,
        text=True,
    )

    assert refs.returncode == 0


@pytest.mark.parametrize(
    "branch_name",
    [
        "",
        "-bad-branch",
        "bad..branch",
        "bad branch",
        "bad~branch",
        "bad^branch",
        "bad:branch",
        "bad?branch",
        "bad*branch",
        "bad[branch",
        "bad\\branch",
    ],
)
def test_create_branch_rejects_invalid_names(
    git_repository: tuple[Path, Path],
    branch_name: str,
):
    repo, _ = git_repository

    client = GitClient()

    with pytest.raises(ValueError):
        client.create_branch(
            repo_path=repo,
            branch_name=branch_name,
        )