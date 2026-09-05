import pytest

from app.github.safety import GitSafetyPolicy


def test_allowed_agent_branch_is_accepted():
    policy = GitSafetyPolicy(
        allowed_branch="agent/issue-001",
    )

    policy.validate_branch(
        "agent/issue-001"
    )


def test_main_branch_is_blocked():
    policy = GitSafetyPolicy(
        allowed_branch="agent/issue-001",
    )

    with pytest.raises(PermissionError):
        policy.validate_branch("main")


def test_master_branch_is_blocked():
    policy = GitSafetyPolicy(
        allowed_branch="agent/issue-001",
    )

    with pytest.raises(PermissionError):
        policy.validate_branch("master")


def test_other_agent_branch_is_blocked():
    policy = GitSafetyPolicy(
        allowed_branch="agent/issue-001",
    )

    with pytest.raises(PermissionError):
        policy.validate_branch(
            "agent/issue-002"
        )


def test_allowed_remote_is_accepted():
    policy = GitSafetyPolicy(
        allowed_branch="agent/issue-001",
        allowed_remote="origin",
    )

    policy.validate_remote("origin")


def test_unapproved_remote_is_blocked():
    policy = GitSafetyPolicy(
        allowed_branch="agent/issue-001",
        allowed_remote="origin",
    )

    with pytest.raises(PermissionError):
        policy.validate_remote("upstream")


def test_force_push_is_blocked_by_default():
    policy = GitSafetyPolicy(
        allowed_branch="agent/issue-001",
    )

    with pytest.raises(PermissionError):
        policy.validate_force_push(True)


def test_force_push_can_be_explicitly_allowed():
    policy = GitSafetyPolicy(
        allowed_branch="agent/issue-001",
        allow_force_push=True,
    )

    policy.validate_force_push(True)


def test_empty_branch_is_rejected():
    with pytest.raises(ValueError):
        GitSafetyPolicy(
            allowed_branch="",
        )


def test_protected_branch_cannot_be_agent_branch():
    with pytest.raises(ValueError):
        GitSafetyPolicy(
            allowed_branch="main",
        )