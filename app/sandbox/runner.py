from pathlib import Path
import subprocess
from typing import Optional

from app.sandbox.models import CommandResult, SandboxConfig


class SandboxRunner:
    """
    Runs commands inside a disposable Docker container.

    The repository is mounted into the container at /workspace.

    Security guarantees:

    - Network disabled by default.
    - CPU limited.
    - Memory limited.
    - Process count limited.
    - Command execution timeout.
    - All Linux capabilities dropped.
    - Privilege escalation disabled.
    """

    def __init__(
        self,
        config: Optional[SandboxConfig] = None,
    ):
        self.config = config or SandboxConfig()

    def _build_docker_command(
        self,
        command: str,
        repo_path: Path,
    ) -> list[str]:

        docker_command = [
            "docker",
            "run",
            "--rm",

            # Security hardening
            "--cap-drop",
            "ALL",

            "--security-opt",
            "no-new-privileges:true",

            # Resource limits
            "--memory",
            self.config.memory_limit,

            "--cpus",
            str(self.config.cpu_limit),

            "--pids-limit",
            str(self.config.pids_limit),

            # Working directory
            "--workdir",
            self.config.working_dir,
        ]

        # Network is disabled by default.
        #
        # Explicitly allowing network access requires
        # SandboxConfig(network_enabled=True).
        if not self.config.network_enabled:
            docker_command.extend(
                [
                    "--network",
                    "none",
                ]
            )

        # Mount repository
        docker_command.extend(
            [
                "--mount",
                (
                    "type=bind,"
                    f"source={repo_path.resolve()},"
                    f"target={self.config.working_dir}"
                ),
            ]
        )

        # Environment variables
        for key, value in self.config.environment.items():
            docker_command.extend(
                [
                    "--env",
                    f"{key}={value}",
                ]
            )

        docker_command.extend(
            [
                self.config.image,
                "sh",
                "-c",
                command,
            ]
        )

        return docker_command

    def run(
        self,
        command: str,
        repo_path: str | Path,
        timeout: Optional[int] = None,
    ) -> CommandResult:
        """
        Execute an arbitrary command inside the Docker sandbox.
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

        timeout = (
            timeout
            if timeout is not None
            else self.config.command_timeout
        )

        if timeout <= 0:
            raise ValueError(
                "timeout must be greater than 0."
            )

        docker_command = self._build_docker_command(
            command=command,
            repo_path=repo_path,
        )

        try:
            process = subprocess.run(
                docker_command,
                capture_output=True,
                text=True,
                timeout=timeout,
            )

            return CommandResult(
                command=command,
                return_code=process.returncode,
                stdout=process.stdout,
                stderr=process.stderr,
                timed_out=False,
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

            return CommandResult(
                command=command,
                return_code=-1,
                stdout=stdout,
                stderr=stderr,
                timed_out=True,
            )

        except FileNotFoundError:
            raise RuntimeError(
                "Docker is not installed or is not available "
                "in the system PATH."
            )

    def run_tests(
        self,
        repo_path: str | Path,
        test_command: str = "pytest -v",
        timeout: Optional[int] = None,
    ) -> CommandResult:
        """
        Run pytest inside the Docker sandbox.
        """

        return self.run(
            command=test_command,
            repo_path=repo_path,
            timeout=timeout,
        )