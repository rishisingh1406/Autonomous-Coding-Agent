from __future__ import annotations

from dataclasses import dataclass

from app.github.github_client import (
    GitHubClient,
    PullRequestResult,
)
from app.github.pr import (
    PRDescriptionBuilder,
    PullRequestDescription,
)


@dataclass
class PRContext:
    """
    Information required to create an automated pull request.
    """

    owner: str
    repo: str
    branch: str
    base_branch: str
    title: str
    summary: str
    diff_summary: str
    test_results: str


@dataclass
class PRManagerResult:
    """
    Final result of the PR creation workflow.
    """

    success: bool
    description: PullRequestDescription | None = None
    pull_request: PullRequestResult | None = None
    error: str | None = None


class PRManager:
    """
    Coordinates PR description generation and GitHub PR creation.

    Responsibilities:

        1. Build the PR description.
        2. Send the PR to GitHub.
        3. Return a structured result.

    It does not:

        - modify source code
        - run tests
        - create Git branches
        - commit changes
        - push changes
    """

    def __init__(
        self,
        github_client: GitHubClient,
        description_builder: PRDescriptionBuilder | None = None,
    ):
        self.github_client = github_client
        self.description_builder = (
            description_builder
            or PRDescriptionBuilder()
        )

    def create_pull_request(
        self,
        context: PRContext,
    ) -> PRManagerResult:
        """
        Generate the PR description and create the GitHub PR.
        """

        try:
            description = self.description_builder.build(
                title=context.title,
                summary=context.summary,
                diff_summary=context.diff_summary,
                test_results=context.test_results,
            )
        except Exception as exc:
            return PRManagerResult(
                success=False,
                error=(
                    "Failed to generate pull request "
                    f"description: {exc}"
                ),
            )

        result = self.github_client.create_pull_request(
            owner=context.owner,
            repo=context.repo,
            title=description.title,
            body=description.body,
            head=context.branch,
            base=context.base_branch,
        )

        if not result.success:
            return PRManagerResult(
                success=False,
                description=description,
                pull_request=result,
                error=result.error
                or "Failed to create pull request.",
            )

        return PRManagerResult(
            success=True,
            description=description,
            pull_request=result,
        )