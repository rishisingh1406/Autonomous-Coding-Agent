from __future__ import annotations

from dataclasses import dataclass


@dataclass(frozen=True)
class GitSafetyPolicy:
    """
    Safety policy for Git operations performed by the agent.

    The agent is restricted to one working branch and cannot
    directly modify protected branches.
    """

    allowed_branch: str

    allowed_remote: str = "origin"

    protected_branches: tuple[str, ...] = (
        "main",
        "master",
    )

    allow_force_push: bool = False

    def __post_init__(self) -> None:
        if not self.allowed_branch.strip():
            raise ValueError(
                "allowed_branch cannot be empty."
            )

        if not self.allowed_remote.strip():
            raise ValueError(
                "allowed_remote cannot be empty."
            )

        if self.allowed_branch in self.protected_branches:
            raise ValueError(
                f"Agent branch cannot be protected branch: "
                f"{self.allowed_branch}"
            )

    def validate_branch(
        self,
        branch: str,
    ) -> None:
        """
        Validate that the branch is allowed for agent operations.
        """

        if not branch.strip():
            raise ValueError(
                "Branch name cannot be empty."
            )

        if branch in self.protected_branches:
            raise PermissionError(
                f"Git operation blocked: "
                f"'{branch}' is a protected branch."
            )

        if branch != self.allowed_branch:
            raise PermissionError(
                f"Git operation blocked: "
                f"branch '{branch}' is not the allowed "
                f"agent branch '{self.allowed_branch}'."
            )

    def validate_remote(
        self,
        remote: str,
    ) -> None:
        """
        Validate that the agent is operating on the
        approved Git remote.
        """

        if not remote.strip():
            raise ValueError(
                "Remote name cannot be empty."
            )

        if remote != self.allowed_remote:
            raise PermissionError(
                f"Git operation blocked: "
                f"remote '{remote}' is not the allowed "
                f"remote '{self.allowed_remote}'."
            )

    def validate_force_push(
        self,
        force: bool,
    ) -> None:
        """
        Prevent force pushes unless explicitly enabled
        by the policy.
        """

        if force and not self.allow_force_push:
            raise PermissionError(
                "Force push is disabled by Git safety policy."
            )