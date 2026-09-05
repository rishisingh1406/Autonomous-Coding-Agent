from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CommandResult:
    """
    Result of executing one command inside the sandbox.
    """

    command: str
    return_code: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def success(self) -> bool:
        """
        A command succeeds only when it exits with
        return code 0 and does not time out.
        """

        return (
            self.return_code == 0
            and not self.timed_out
        )


@dataclass
class SandboxConfig:
    """
    Security and resource configuration for the
    isolated Docker sandbox.

    The sandbox is intentionally restrictive by default.
    """

    image: str = "autonomous-coding-agent"

    # Execution timeout
    command_timeout: int = 30

    # Docker resource limits
    memory_limit: str = "512m"
    cpu_limit: float = 1.0
    pids_limit: int = 100

    # Network access is disabled by default.
    network_enabled: bool = False

    working_dir: str = "/workspace"

    environment: dict = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        """
        Validate sandbox security configuration early.

        Invalid resource values should fail before Docker
        is invoked.
        """

        if self.command_timeout <= 0:
            raise ValueError(
                "command_timeout must be greater than 0."
            )

        if self.cpu_limit <= 0:
            raise ValueError(
                "cpu_limit must be greater than 0."
            )

        if self.pids_limit <= 0:
            raise ValueError(
                "pids_limit must be greater than 0."
            )

        if not self.memory_limit.strip():
            raise ValueError(
                "memory_limit cannot be empty."
            )

        if not self.working_dir.strip():
            raise ValueError(
                "working_dir cannot be empty."
            )