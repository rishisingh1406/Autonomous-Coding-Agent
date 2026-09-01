import shutil
import tempfile
from pathlib import Path

from app.sandbox.models import (
    CommandResult,
    SandboxConfig,
)
from app.sandbox.runner import SandboxRunner


class SandboxManager:
    """
    Creates disposable working copies of repositories.
    """

    def __init__(
        self,
        config: SandboxConfig | None = None,
    ):
        self.config = config or SandboxConfig()
        self.runner = SandboxRunner(self.config)

    def create_workspace(
        self,
        source_repo: str | Path,
    ) -> Path:

        source_repo = Path(source_repo).resolve()

        if not source_repo.exists():
            raise FileNotFoundError(
                f"Source repository does not exist: {source_repo}"
            )

        if not source_repo.is_dir():
            raise ValueError(
                f"Source repository is not a directory: {source_repo}"
            )

        workspace_root = Path(
            tempfile.mkdtemp(
                prefix="coding-agent-"
            )
        )

        destination = workspace_root / "repo"

        shutil.copytree(
            source_repo,
            destination,
            dirs_exist_ok=True,
        )

        return destination

    def run(
        self,
        workspace: str | Path,
        command: str,
        timeout: int | None = None,
    ) -> CommandResult:

        return self.runner.run(
            command=command,
            repo_path=workspace,
            timeout=timeout,
        )

    def cleanup(
        self,
        workspace: str | Path,
    ) -> None:

        workspace = Path(workspace).resolve()

        if "coding-agent-" not in workspace.parent.name:
            raise RuntimeError(
                "Refusing to delete workspace outside "
                "the coding-agent temporary directory."
            )

        shutil.rmtree(
            workspace.parent,
            ignore_errors=True,
        )