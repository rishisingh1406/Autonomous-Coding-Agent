import json

from app.github.github_client import GitHubClient


class FakeResponse:
    def __init__(self, payload):
        self.payload = payload

    def read(self):
        return json.dumps(self.payload).encode("utf-8")

    def __enter__(self):
        return self

    def __exit__(self, exc_type, exc, tb):
        return False


def test_create_pull_request(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["url"] = request.full_url
        captured["method"] = request.method
        captured["headers"] = dict(request.headers)
        captured["timeout"] = timeout

        captured["payload"] = json.loads(
            request.data.decode("utf-8")
        )

        return FakeResponse(
            {
                "number": 42,
                "html_url": (
                    "https://github.com/example/repo/pull/42"
                ),
            }
        )

    monkeypatch.setattr(
        "app.github.github_client.urlopen",
        fake_urlopen,
    )

    client = GitHubClient(
        token="test-token",
    )

    result = client.create_pull_request(
        owner="example",
        repo="repo",
        title="Fix authentication",
        body="## Summary\nFixed authentication.",
        head="agent/fix-auth",
        base="main",
    )

    assert result.success is True
    assert result.number == 42
    assert result.url.endswith("/pull/42")

    assert captured["method"] == "POST"

    assert (
        captured["url"]
        == "https://api.github.com/repos/example/repo/pulls"
    )

    assert captured["payload"] == {
        "title": "Fix authentication",
        "body": "## Summary\nFixed authentication.",
        "head": "agent/fix-auth",
        "base": "main",
    }

    assert captured["timeout"] == 30


def test_create_pull_request_uses_token(monkeypatch):
    captured = {}

    def fake_urlopen(request, timeout):
        captured["authorization"] = request.get_header(
            "Authorization"
        )

        return FakeResponse(
            {
                "number": 1,
                "html_url": "https://github.com/example/repo/pull/1",
            }
        )

    monkeypatch.setattr(
        "app.github.github_client.urlopen",
        fake_urlopen,
    )

    client = GitHubClient(
        token="secret-token",
    )

    client.create_pull_request(
        owner="example",
        repo="repo",
        title="Fix bug",
        body="Tests passed.",
        head="agent/fix",
        base="main",
    )

    assert captured["authorization"] == (
        "Bearer secret-token"
    )


def test_create_pull_request_rejects_empty_title():
    client = GitHubClient(
        token="test-token",
    )

    try:
        client.create_pull_request(
            owner="example",
            repo="repo",
            title="",
            body="body",
            head="agent/fix",
        )
    except ValueError as exc:
        assert "title" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError"
        )


def test_create_pull_request_rejects_empty_head():
    client = GitHubClient(
        token="test-token",
    )

    try:
        client.create_pull_request(
            owner="example",
            repo="repo",
            title="Fix bug",
            body="body",
            head="",
        )
    except ValueError as exc:
        assert "head" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError"
        )


def test_github_client_requires_token(monkeypatch):
    monkeypatch.delenv(
        "GITHUB_TOKEN",
        raising=False,
    )

    try:
        GitHubClient()
    except ValueError as exc:
        assert "GITHUB_TOKEN" in str(exc)
    else:
        raise AssertionError(
            "Expected ValueError"
        )