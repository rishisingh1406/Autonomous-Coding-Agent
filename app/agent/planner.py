from __future__ import annotations

from dataclasses import dataclass

from app.repo.context import RetrievalResult


@dataclass
class FixPlan:
    """
    Structured plan describing what needs to change
    to resolve a coding issue.

    The planner decides WHAT should change.
    It does not modify files or execute commands.
    """

    summary: str
    problem: str
    target_files: list[str]
    changes: list[str]
    tests_to_run: list[str]
    rationale: str


class Planner:
    """
    Produces a fix plan from a GitHub issue and
    retrieved repository context.

    This first version is intentionally deterministic.
    The LLM can be plugged into this interface later.
    """

    def plan(
        self,
        issue_title: str,
        issue_body: str = "",
        context: list[RetrievalResult] | None = None,
    ) -> FixPlan:

        if not issue_title.strip():
            raise ValueError("Issue title cannot be empty.")

        context = context or []

        target_files = self._extract_target_files(context)

        changes = self._infer_changes(
            issue_title=issue_title,
            issue_body=issue_body,
            context=context,
        )

        tests = self._infer_tests(context)

        problem = self._build_problem(
            issue_title=issue_title,
            issue_body=issue_body,
            context=context,
        )

        rationale = self._build_rationale(
            context=context,
            target_files=target_files,
        )

        return FixPlan(
            summary=issue_title.strip(),
            problem=problem,
            target_files=target_files,
            changes=changes,
            tests_to_run=tests,
            rationale=rationale,
        )

    @staticmethod
    def _extract_target_files(
        context: list[RetrievalResult],
    ) -> list[str]:

        files: list[str] = []

        for result in context:
            if result.path not in files:
                files.append(result.path)

        return files

    @staticmethod
    def _infer_changes(
        issue_title: str,
        issue_body: str,
        context: list[RetrievalResult],
    ) -> list[str]:

        if not context:
            return [
                "Inspect the repository to identify the implementation "
                "responsible for the reported issue."
            ]

        changes = [
            f"Inspect the relevant implementation in {result.path}"
            for result in context
        ]

        if issue_body.strip():
            changes.append(
                "Implement the smallest change necessary to satisfy "
                "the issue requirements."
            )
        else:
            changes.append(
                "Implement the smallest change necessary to resolve "
                "the reported issue."
            )

        return changes

    @staticmethod
    def _infer_tests(
        context: list[RetrievalResult],
    ) -> list[str]:

        tests: list[str] = []

        for result in context:
            path = result.path.lower()

            if "test" in path:
                if result.path not in tests:
                    tests.append(result.path)

        return tests

    @staticmethod
    def _build_problem(
        issue_title: str,
        issue_body: str,
        context: list[RetrievalResult],
    ) -> str:

        if issue_body.strip():
            return issue_body.strip()

        if context:
            return (
                f"The repository contains relevant code for the issue "
                f"'{issue_title.strip()}'. The implementation must be "
                f"inspected and updated to satisfy the reported behavior."
            )

        return (
            f"The issue '{issue_title.strip()}' requires identifying "
            f"and fixing the responsible implementation."
        )

    @staticmethod
    def _build_rationale(
        context: list[RetrievalResult],
        target_files: list[str],
    ) -> str:

        if not context:
            return (
                "No repository context was retrieved, so the planner "
                "cannot confidently identify the implementation."
            )

        if len(target_files) == 1:
            return (
                f"Repository retrieval identified {target_files[0]} "
                "as the relevant implementation location."
            )

        return (
            "Repository retrieval identified multiple relevant files: "
            + ", ".join(target_files)
            + ". These files should be inspected before making changes."
        )