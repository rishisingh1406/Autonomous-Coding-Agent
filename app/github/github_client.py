from __future__ import annotations

import json
import os
from dataclasses import dataclass
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen


@dataclass
class PullRequestResult:
    """
    Result returned after attempting to create a GitHub PR.
    """

    success: bool
    operation: str
    number: int | None = None
    url: str | None = None
    error: str | None = None


class GitHubClient:
    """
    Minimal GitHub API client.

    Responsibilities:

        - authenticate with GitHub
        - create pull requests

    Git operations remain inside GitClient.
    """

    API_BASE_URL = "https://api.github.com"

    def __init__(
        self,
        token: str | None = None,
        *,
        api_base_url: str = API_BASE_URL,
        timeout: int = 30,
    ):
        self.token = token or os.getenv("GITHUB_TOKEN")

        if not self.token:
            raise ValueError(
                "GitHub token is required. "
                "Set GITHUB_TOKEN or pass token explicitly."
            )

        if timeout < 1:
            raise ValueError(
                "timeout must be at least 1."
            )

        self.api_base_url = api_base_url.rstrip("/")
        self.timeout = timeout

    def create_pull_request(
        self,
        *,
        owner: str,
        repo: str,
        title: str,
        body: str,
        head: str,
        base: str = "main",
    ) -> PullRequestResult:
        """
        Create a pull request through GitHub's REST API.

        Equivalent API operation:

            POST /repos/{owner}/{repo}/pulls
        """

        if not owner.strip():
            raise ValueError("owner cannot be empty.")

        if not repo.strip():
            raise ValueError("repo cannot be empty.")

        if not title.strip():
            raise ValueError(
                "Pull request title cannot be empty."
            )

        if not body.strip():
            raise ValueError(
                "Pull request body cannot be empty."
            )

        if not head.strip():
            raise ValueError(
                "head branch cannot be empty."
            )

        if not base.strip():
            raise ValueError(
                "base branch cannot be empty."
            )

        payload = {
            "title": title,
            "body": body,
            "head": head,
            "base": base,
        }

        url = (
            f"{self.api_base_url}"
            f"/repos/{owner}/{repo}/pulls"
        )

        request = Request(
            url,
            data=json.dumps(payload).encode("utf-8"),
            method="POST",
            headers={
                "Authorization": f"Bearer {self.token}",
                "Accept": "application/vnd.github+json",
                "Content-Type": "application/json",
                "X-GitHub-Api-Version": "2022-11-28",
                "User-Agent": "Autonomous-Coding-Agent",
            },
        )

        try:
            with urlopen(
                request,
                timeout=self.timeout,
            ) as response:
                response_data = json.loads(
                    response.read().decode("utf-8")
                )

            return PullRequestResult(
                success=True,
                operation="create_pull_request",
                number=response_data.get("number"),
                url=response_data.get("html_url"),
            )

        except HTTPError as exc:
            try:
                error_body = exc.read().decode(
                    "utf-8",
                    errors="replace",
                )
            except Exception:
                error_body = ""

            return PullRequestResult(
                success=False,
                operation="create_pull_request",
                error=(
                    f"GitHub API returned HTTP "
                    f"{exc.code}: {error_body}"
                ),
            )

        except URLError as exc:
            return PullRequestResult(
                success=False,
                operation="create_pull_request",
                error=f"GitHub connection failed: {exc}",
            )

        except TimeoutError:
            return PullRequestResult(
                success=False,
                operation="create_pull_request",
                error="GitHub request timed out.",
            )

        except json.JSONDecodeError:
            return PullRequestResult(
                success=False,
                operation="create_pull_request",
                error="GitHub returned invalid JSON.",
            )