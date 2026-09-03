from dataclasses import dataclass, field
from typing import List, Optional


@dataclass
class CommandResult:
    command: str
    return_code: int
    stdout: str
    stderr: str
    timed_out: bool = False

    @property
    def success(self) -> bool:
        return self.return_code == 0 and not self.timed_out


@dataclass
class SandboxConfig:
    image: str = "autonomous-coding-agent"
    command_timeout: int = 30

    memory_limit: str = "512m"
    cpu_limit: float = 1.0

    pids_limit: int = 100

    network_enabled: bool = False

    working_dir: str = "/workspace"

    environment: dict = field(default_factory=dict)


@dataclass
class SandboxResult:
    success: bool
    command_results: List[CommandResult]
    error: Optional[str] = None