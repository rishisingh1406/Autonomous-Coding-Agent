from pathlib import Path

import pytest

from app.sandbox.manager import SandboxManager
from app.sandbox.models import SandboxConfig
from app.sandbox.runner import SandboxRunner


@pytest.fixture
def demo_repo(tmp_path: Path) -> Path:

    repo = tmp_path / "demo_repo"
    repo.mkdir()

    (repo / "hello.py").write_text(
        "message = 'hello'\n",
        encoding="utf-8",
    )

    return repo


def test_sandbox_can_read_files(demo_repo):

    runner = SandboxRunner()

    result = runner.run(
        command="cat hello.py",
        repo_path=demo_repo,
    )

    assert result.success
    assert "hello" in result.stdout


def test_sandbox_can_write_files(demo_repo):

    runner = SandboxRunner()

    result = runner.run(
        command="echo 'updated' > output.txt",
        repo_path=demo_repo,
    )

    assert result.success

    output_file = demo_repo / "output.txt"

    assert output_file.exists()
    assert output_file.read_text(
        encoding="utf-8"
    ).strip() == "updated"


def test_sandbox_returns_command_failure(demo_repo):

    runner = SandboxRunner()

    result = runner.run(
        command="python -c \"raise Exception('boom')\"",
        repo_path=demo_repo,
    )

    assert not result.success
    assert result.return_code != 0
    assert "boom" in result.stderr


def test_sandbox_timeout(demo_repo):

    config = SandboxConfig(
        command_timeout=2,
    )

    runner = SandboxRunner(config)

    result = runner.run(
        command="sleep 10",
        repo_path=demo_repo,
    )

    assert result.timed_out
    assert not result.success


def test_sandbox_has_no_network(demo_repo):

    runner = SandboxRunner()

    result = runner.run(
        command="python -c \"import urllib.request; urllib.request.urlopen('https://example.com', timeout=2)\"",
        repo_path=demo_repo,
        timeout=5,
    )

    assert not result.success


def test_sandbox_manager_creates_isolated_workspace(demo_repo):

    manager = SandboxManager()

    workspace = manager.create_workspace(
        demo_repo
    )

    try:
        assert workspace.exists()

        original = demo_repo / "hello.py"
        copied = workspace / "hello.py"

        assert copied.exists()
        assert copied.read_text(
            encoding="utf-8"
        ) == original.read_text(
            encoding="utf-8"
        )

    finally:
        manager.cleanup(workspace)