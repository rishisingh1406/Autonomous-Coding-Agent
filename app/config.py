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