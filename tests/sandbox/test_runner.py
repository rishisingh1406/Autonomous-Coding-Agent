from pathlib import Path

from app.sandbox.runner import SandboxRunner


def test_runner_executes_pytest_successfully(
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

    result = runner.run_tests(
        repo_path=tmp_path,
        test_command="pytest test_example.py -v",
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

    result = runner.run_tests(
        repo_path=tmp_path,
        test_command="pytest test_example.py -v",
    )

    assert not result.success
    assert result.return_code != 0
    assert result.timed_out is False

    failure_output = (
        result.stdout + result.stderr
    )

    assert "FAILED" in failure_output
    assert "assert (2 + 3) == 10" in failure_output


def test_runner_captures_pytest_collection_error(
    tmp_path: Path,
):
    test_file = tmp_path / "test_example.py"

    test_file.write_text(
        """
def test_broken():
    assert True
""".strip(),
        encoding="utf-8",
    )

    runner = SandboxRunner()

    result = runner.run_tests(
        repo_path=tmp_path,
        test_command="pytest test_does_not_exist.py -v",
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


def test_runner_returns_structured_pytest_result(
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

    result = runner.run_tests(
        repo_path=tmp_path,
        test_command="pytest test_example.py",
    )

    assert result.command == "pytest test_example.py"
    assert isinstance(result.return_code, int)
    assert isinstance(result.stdout, str)
    assert isinstance(result.stderr, str)
    assert isinstance(result.timed_out, bool)
    assert isinstance(result.success, bool)


def test_runner_captures_pytest_stderr(
    tmp_path: Path,
):
    test_file = tmp_path / "test_example.py"

    test_file.write_text(
        """
def test_example():
    assert False
""".strip(),
        encoding="utf-8",
    )

    runner = SandboxRunner()

    result = runner.run_tests(
        repo_path=tmp_path,
        test_command="pytest test_example.py -v",
    )

    assert not result.success

    combined_output = (
        result.stdout + result.stderr
    )

    assert "FAILED" in combined_output
    assert "test_example.py" in combined_output


def test_network_is_disabled_by_default(
    tmp_path: Path,
):
    runner = SandboxRunner()

    docker_command = runner._build_docker_command(
        command="pytest -v",
        repo_path=tmp_path,
    )

    assert "--network" in docker_command
    assert "none" in docker_command


def test_network_can_be_explicitly_enabled(
    tmp_path: Path,
):
    from app.sandbox.models import SandboxConfig

    config = SandboxConfig(
        network_enabled=True,
    )

    runner = SandboxRunner(config)

    docker_command = runner._build_docker_command(
        command="pytest -v",
        repo_path=tmp_path,
    )

    assert "--network" not in docker_command


def test_docker_command_contains_resource_limits(
    tmp_path: Path,
):
    from app.sandbox.models import SandboxConfig

    config = SandboxConfig(
        memory_limit="256m",
        cpu_limit=0.5,
        pids_limit=50,
    )

    runner = SandboxRunner(config)

    docker_command = runner._build_docker_command(
        command="pytest -v",
        repo_path=tmp_path,
    )

    assert "--memory" in docker_command
    assert "256m" in docker_command

    assert "--cpus" in docker_command
    assert "0.5" in docker_command

    assert "--pids-limit" in docker_command
    assert "50" in docker_command


def test_docker_command_drops_all_capabilities(
    tmp_path: Path,
):
    runner = SandboxRunner()

    docker_command = runner._build_docker_command(
        command="pytest -v",
        repo_path=tmp_path,
    )

    assert "--cap-drop" in docker_command
    assert "ALL" in docker_command


def test_docker_command_disables_privilege_escalation(
    tmp_path: Path,
):
    runner = SandboxRunner()

    docker_command = runner._build_docker_command(
        command="pytest -v",
        repo_path=tmp_path,
    )

    assert "--security-opt" in docker_command
    assert "no-new-privileges:true" in docker_command


def test_invalid_command_timeout_is_rejected():
    from app.sandbox.models import SandboxConfig

    try:
        SandboxConfig(command_timeout=0)
        assert False, (
            "Expected ValueError for invalid timeout."
        )
    except ValueError as exc:
        assert "command_timeout" in str(exc)


def test_invalid_cpu_limit_is_rejected():
    from app.sandbox.models import SandboxConfig

    try:
        SandboxConfig(cpu_limit=0)
        assert False, (
            "Expected ValueError for invalid CPU limit."
        )
    except ValueError as exc:
        assert "cpu_limit" in str(exc)


def test_invalid_pids_limit_is_rejected():
    from app.sandbox.models import SandboxConfig

    try:
        SandboxConfig(pids_limit=0)
        assert False, (
            "Expected ValueError for invalid PID limit."
        )
    except ValueError as exc:
        assert "pids_limit" in str(exc)