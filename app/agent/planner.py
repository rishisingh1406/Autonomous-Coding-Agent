from __future__ import annotations

from dataclasses import dataclass, field

from app.repo.context import RetrievalResult


@dataclass
class FileEdit:
    """
    A deterministic edit to apply to a repository file.
    """

    file_path: str
    old_text: str
    new_text: str


@dataclass
class FixPlan:
    """
    Structured plan describing what needs to change
    to resolve a coding issue.
    """

    summary: str
    problem: str
    target_files: list[str]
    changes: list[str]
    tests_to_run: list[str]
    rationale: str
    edits: list[FileEdit] = field(default_factory=list)


class Planner:
    """
    Deterministic planner that converts an issue and
    retrieved repository context into a FixPlan.

    The planner decides WHAT should change.
    """

    def plan(
        self,
        issue_title: str,
        issue_body: str = "",
        context: list[RetrievalResult] | None = None,
    ) -> FixPlan:

        if not issue_title.strip():
            raise ValueError(
                "Issue title cannot be empty."
            )

        context = context or []

        target_files = []
        changes = []
        tests_to_run = []

        for result in context:

            path = result.document.path

            if path not in target_files:
                target_files.append(path)

            if path.startswith("tests/"):
                if path not in tests_to_run:
                    tests_to_run.append(path)

        problem = issue_body.strip()

        if not problem:
            problem = issue_title.strip()

        if target_files:
            changes = [
                f"Inspect and modify {path} to address the issue."
                for path in target_files
            ]
        else:
            changes = [
                "Identify the implementation file responsible for the issue."
            ]

        rationale = (
            "Target files were selected from repository context "
            "retrieved for the issue."
        )

        return FixPlan(
            summary=issue_title.strip(),
            problem=problem,
            target_files=target_files,
            changes=changes,
            tests_to_run=tests_to_run,
            rationale=rationale,
        )
