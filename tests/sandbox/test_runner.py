from pathlib import Path

from app.sandbox.runner import SandboxRunner


def test_runner_captures_successful_pytest_output(
    tmp_path: Path,
):
    test_file = tmp_path / "test_example.py"

    test_file.write_text(
        """
def test_add():
    assert 2 + 3 == 5
""".strip(),
        encoding="utf-8",
    )

    runner = SandboxRunner()

    result = runner.run(
        repo_path=tmp_path,
        command="pytest test_example.py -v",
    )

    assert result.success
    assert result.return_code == 0
    assert "1 passed" in result.stdout
    assert result.timed_out is False


def test_runner_captures_failed_pytest_output(
    tmp_path: Path,
):
    test_file = tmp_path / "test_example.py"

    test_file.write_text(
        """
def test_add():
    assert 2 + 3 == 10
""".strip(),
        encoding="utf-8",
    )

    runner = SandboxRunner()

    result = runner.run(
        repo_path=tmp_path,
        command="pytest test_example.py -v",
    )

    assert not result.success
    assert result.return_code != 0
    assert result.timed_out is False

    failure_output = (
        result.stdout + result.stderr
    )

    assert "FAILED" in failure_output
    assert "assert 5 == 10" in failure_output


def test_runner_captures_missing_test_error(
    tmp_path: Path,
):
    runner = SandboxRunner()

    result = runner.run(
        repo_path=tmp_path,
        command="pytest test_does_not_exist.py -v",
    )

    assert not result.success
    assert result.return_code != 0

    error_output = (
        result.stdout + result.stderr
    )

    assert (
        "file or directory not found"
        in error_output.lower()
    )


def test_runner_returns_structured_command_result(
    tmp_path: Path,
):
    test_file = tmp_path / "test_example.py"

    test_file.write_text(
        """
def test_example():
    assert True
""".strip(),
        encoding="utf-8",
    )

    runner = SandboxRunner()

    result = runner.run(
        repo_path=tmp_path,
        command="pytest test_example.py",
    )

    assert result.command == "pytest test_example.py"
    assert isinstance(result.return_code, int)
    assert isinstance(result.stdout, str)
    assert isinstance(result.stderr, str)
    assert isinstance(result.timed_out, bool)
