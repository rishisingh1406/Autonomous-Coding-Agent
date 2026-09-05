from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class GitCommandResult:
    """
    Structured result from a Git command.
    """

    command: list[str]
    return_code: int
    stdout: str
    stderr: str

    @property
    def success(self) -> bool:
        return self.return_code == 0


@dataclass
class GitOperationResult:
    """
    Structured result from a higher-level Git operation.
    """

    success: bool
    operation: str
    output: str = ""
    error: str | None = None


class GitClient:
    """
    Handles Git operations for the autonomous coding agent.

    Responsibilities:

        - create agent branches
        - stage changes
        - create commits
        - push branches to the remote

    The client does not decide WHAT code should change.
    It only manages repository state after the agent
    has completed its implementation and verification.
    """

    DEFAULT_REMOTE = "origin"

    def __init__(
        self,
        command_timeout: int = 30,
    ):
        if command_timeout < 1:
            raise ValueError(
                "command_timeout must be at least 1."
            )

        self.command_timeout = command_timeout

    def _run(
        self,
        repo_path: str | Path,
        args: list[str],
    ) -> GitCommandResult:
        """
        Execute a Git command safely.

        Git arguments are passed as a list rather than through
        a shell, preventing shell interpretation of branch names,
        commit messages, and paths.
        """

        repo_path = Path(repo_path).resolve()

        if not repo_path.exists():
            raise FileNotFoundError(
                f"Repository path does not exist: {repo_path}"
            )

        if not repo_path.is_dir():
            raise ValueError(
                f"Repository path must be a directory: {repo_path}"
            )

        command = [
            "git",
            *args,
        ]

        try:
            process = subprocess.run(
                command,
                cwd=repo_path,
                capture_output=True,
                text=True,
                timeout=self.command_timeout,
            )

            return GitCommandResult(
                command=command,
                return_code=process.returncode,
                stdout=process.stdout,
                stderr=process.stderr,
            )

        except FileNotFoundError:
            raise RuntimeError(
                "Git is not installed or is not available "
                "in the system PATH."
            )

        except subprocess.TimeoutExpired as exc:
            stdout = exc.stdout or ""
            stderr = exc.stderr or ""

            if isinstance(stdout, bytes):
                stdout = stdout.decode(
                    "utf-8",
                    errors="replace",
                )

            if isinstance(stderr, bytes):
                stderr = stderr.decode(
                    "utf-8",
                    errors="replace",
                )

            return GitCommandResult(
                command=command,
                return_code=-1,
                stdout=stdout,
                stderr=(
                    stderr
                    or "Git command timed out."
                ),
            )

    def get_current_branch(
        self,
        repo_path: str | Path,
    ) -> str:
        """
        Return the currently checked-out branch.
        """

        result = self._run(
            repo_path,
            [
                "branch",
                "--show-current",
            ],
        )

        if not result.success:
            raise RuntimeError(
                "Failed to determine current branch: "
                f"{result.stderr.strip()}"
            )

        branch = result.stdout.strip()

        if not branch:
            raise RuntimeError(
                "Repository is not currently on a named branch."
            )

        return branch

    def create_branch(
        self,
        repo_path: str | Path,
        branch_name: str,
    ) -> GitOperationResult:
        """
        Create and checkout a new branch.

        Equivalent to:

            git switch -c <branch>
        """

        self._validate_branch_name(branch_name)

        result = self._run(
            repo_path,
            [
                "switch",
                "-c",
                branch_name,
            ],
        )

        if not result.success:
            return GitOperationResult(
                success=False,
                operation="create_branch",
                output=result.stdout,
                error=result.stderr.strip()
                or "Failed to create branch.",
            )

        return GitOperationResult(
            success=True,
            operation="create_branch",
            output=result.stdout.strip(),
        )

    def commit_changes(
        self,
        repo_path: str | Path,
        message: str,
    ) -> GitOperationResult:
        """
        Stage all repository changes and create a commit.

        Equivalent to:

            git add -A
            git commit -m "<message>"
        """

        if not message.strip():
            raise ValueError(
                "Commit message cannot be empty."
            )

        add_result = self._run(
            repo_path,
            [
                "add",
                "-A",
            ],
        )

        if not add_result.success:
            return GitOperationResult(
                success=False,
                operation="commit_changes",
                output=add_result.stdout,
                error=add_result.stderr.strip()
                or "Failed to stage changes.",
            )

        staged_result = self._run(
            repo_path,
            [
                "diff",
                "--cached",
                "--quiet",
            ],
        )

        if staged_result.return_code == 0:
            return GitOperationResult(
                success=False,
                operation="commit_changes",
                output="",
                error="No changes to commit.",
            )

        if staged_result.return_code != 1:
            return GitOperationResult(
                success=False,
                operation="commit_changes",
                output=staged_result.stdout,
                error=(
                    staged_result.stderr.strip()
                    or "Failed to inspect staged changes."
                ),
            )

        commit_result = self._run(
            repo_path,
            [
                "commit",
                "-m",
                message,
            ],
        )

        if not commit_result.success:
            return GitOperationResult(
                success=False,
                operation="commit_changes",
                output=commit_result.stdout,
                error=commit_result.stderr.strip()
                or "Failed to create commit.",
            )

        return GitOperationResult(
            success=True,
            operation="commit_changes",
            output=(
                commit_result.stdout.strip()
                or commit_result.stderr.strip()
            ),
        )

    def push_branch(
        self,
        repo_path: str | Path,
        branch_name: str,
        remote: str = DEFAULT_REMOTE,
    ) -> GitOperationResult:
        """
        Push a branch to the configured Git remote.

        Equivalent to:

            git push -u origin <branch>
        """

        self._validate_branch_name(branch_name)

        if not remote.strip():
            raise ValueError(
                "Remote name cannot be empty."
            )

        result = self._run(
            repo_path,
            [
                "push",
                "--set-upstream",
                remote,
                branch_name,
            ],
        )

        if not result.success:
            return GitOperationResult(
                success=False,
                operation="push_branch",
                output=result.stdout,
                error=result.stderr.strip()
                or "Failed to push branch.",
            )

        return GitOperationResult(
            success=True,
            operation="push_branch",
            output=(
                result.stdout.strip()
                or result.stderr.strip()
            ),
        )

    @staticmethod
    def _validate_branch_name(
        branch_name: str,
    ) -> None:
        """
        Validate a branch name before passing it to Git.
        """

        if not branch_name.strip():
            raise ValueError(
                "Branch name cannot be empty."
            )

        if branch_name.startswith("-"):
            raise ValueError(
                "Branch name cannot start with '-'."
            )

        if branch_name.endswith("/"):
            raise ValueError(
                "Branch name cannot end with '/'."
            )

        if ".." in branch_name:
            raise ValueError(
                "Branch name cannot contain '..'."
            )

        if branch_name.startswith("/") or branch_name.endswith("/"):
            raise ValueError(
                "Branch name cannot start or end with '/'."
            )

        if re.search(r"[\x00-\x20~^:?*\\\[]", branch_name):
            raise ValueError(
                "Branch name contains invalid Git characters."
            )