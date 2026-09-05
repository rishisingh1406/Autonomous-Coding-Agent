from __future__ import annotations

import re
import subprocess
from dataclasses import dataclass
from pathlib import Path


@dataclass
class DiffSummary:
    files_changed: int
    insertions: int
    deletions: int
    raw_stat: str

    def as_text(self) -> str:
        return (
            f"Files changed: {self.files_changed}\n"
            f"Insertions: {self.insertions}\n"
            f"Deletions: {self.deletions}\n\n"
            f"{self.raw_stat}"
        )


class DiffSummarizer:
    def __init__(self, timeout: int = 30):
        if timeout < 1:
            raise ValueError("timeout must be at least 1.")

        self.timeout = timeout

    def summarize(
        self,
        repo_path: str | Path,
        *,
        base_branch: str = "main",
    ) -> DiffSummary:
        repo_path = Path(repo_path).resolve()

        if not repo_path.exists():
            raise FileNotFoundError(
                f"Repository path does not exist: {repo_path}"
            )

        result = subprocess.run(
            [
                "git",
                "diff",
                "--stat",
                f"{base_branch}...HEAD",
            ],
            cwd=repo_path,
            capture_output=True,
            text=True,
            timeout=self.timeout,
        )

        if result.returncode != 0:
            raise RuntimeError(
                "Failed to generate diff summary: "
                f"{result.stderr.strip()}"
            )

        raw_stat = result.stdout.strip()

        files_changed = 0
        insertions = 0
        deletions = 0

        if raw_stat:
            lines = raw_stat.splitlines()

            for line in lines:
                if "file changed" in line or "files changed" in line:
                    files_match = re.search(
                        r"(\d+)\s+files?\s+changed",
                        line,
                    )

                    insertions_match = re.search(
                        r"(\d+)\s+insertions?\(\+\)",
                        line,
                    )

                    deletions_match = re.search(
                        r"(\d+)\s+deletions?\(-\)",
                        line,
                    )

                    if files_match:
                        files_changed = int(
                            files_match.group(1)
                        )

                    if insertions_match:
                        insertions = int(
                            insertions_match.group(1)
                        )

                    if deletions_match:
                        deletions = int(
                            deletions_match.group(1)
                        )

        return DiffSummary(
            files_changed=files_changed,
            insertions=insertions,
            deletions=deletions,
            raw_stat=raw_stat or "No changes detected.",
        )