from app.github.pr import PRDescriptionBuilder
from app.github.pr_manager import (
    PRContext,
    PRManager,
)


class FakeGitHubClient:
    def __init__(self, result):
        self.result = result
        self.calls = []

    def create_pull_request(
        self,
        *,
        owner,
        repo,
        title,
        body,
        head,
        base,
    ):
        self.calls.append(
            {
                "owner": owner,
                "repo": repo,
                "title": title,
                "body": body,
                "head": head,
                "base": base,
            }
        )

        return self.result


class FakePullRequestResult:
    def __init__(
        self,
        *,
        success,
        number=None,
        url=None,
        error=None,
    ):
        self.success = success
        self.number = number
        self.url = url
        self.error = error


def make_context():
    return PRContext(
        owner="example",
        repo="repo",
        branch="agent/fix-auth",
        base_branch="main",
        title="Fix authentication",
        summary="Fixed token validation.",
        diff_summary=(
            "app/auth.py | 10 ++++++----\n"
            "1 file changed"
        ),
        test_results="10 passed in 0.42s",
    )


def test_pr_manager_creates_pull_request():
    github = FakeGitHubClient(
        FakePullRequestResult(
            success=True,
            number=42,
            url="https://github.com/example/repo/pull/42",
        )
    )

    manager = PRManager(
        github_client=github,
    )

    result = manager.create_pull_request(
        make_context()
    )

    assert result.success is True
    assert result.pull_request is not None
    assert result.pull_request.number == 42
    assert (
        result.pull_request.url
        == "https://github.com/example/repo/pull/42"
    )

    assert result.description is not None
    assert "Fixed token validation." in (
        result.description.body
    )

    assert len(github.calls) == 1

    call = github.calls[0]

    assert call["owner"] == "example"
    assert call["repo"] == "repo"
    assert call["head"] == "agent/fix-auth"
    assert call["base"] == "main"
    assert call["title"] == "Fix authentication"

    assert "## Summary" in call["body"]
    assert "## Diff Summary" in call["body"]
    assert "## Test Results" in call["body"]
    assert "10 passed" in call["body"]


def test_pr_manager_returns_failure_when_github_fails():
    github = FakeGitHubClient(
        FakePullRequestResult(
            success=False,
            error="Permission denied.",
        )
    )

    manager = PRManager(
        github_client=github,
    )

    result = manager.create_pull_request(
        make_context()
    )

    assert result.success is False
    assert result.error == "Permission denied."

    assert result.description is not None
    assert result.pull_request is not None
    assert result.pull_request.success is False


def test_pr_manager_does_not_call_github_when_description_fails():
    class FailingDescriptionBuilder:
        def build(self, **kwargs):
            raise RuntimeError(
                "description generation failed"
            )

    github = FakeGitHubClient(
        FakePullRequestResult(
            success=True,
            number=1,
        )
    )

    manager = PRManager(
        github_client=github,
        description_builder=FailingDescriptionBuilder(),
    )

    result = manager.create_pull_request(
        make_context()
    )

    assert result.success is False
    assert "description generation failed" in (
        result.error
    )

    assert github.calls == []


def test_pr_manager_uses_custom_description_builder():
    class CustomDescriptionBuilder:
        def build(self, **kwargs):
            return type(
                "Description",
                (),
                {
                    "title": "Custom PR",
                    "body": "Custom generated body",
                },
            )()

    github = FakeGitHubClient(
        FakePullRequestResult(
            success=True,
            number=99,
            url="https://github.com/example/repo/pull/99",
        )
    )

    manager = PRManager(
        github_client=github,
        description_builder=CustomDescriptionBuilder(),
    )

    result = manager.create_pull_request(
        make_context()
    )

    assert result.success is True

    assert github.calls[0]["title"] == "Custom PR"
    assert github.calls[0]["body"] == (
        "Custom generated body"
    )