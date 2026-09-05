from __future__ import annotations

from app.agent.fixer import FixGenerator
from app.agent.planner import FileEdit, FixPlan
from app.agent.reflection import FailureFeedback
from app.evaluation.models import EvaluationIssue


class EvaluationFixPlanProvider(FixGenerator):
    """
    Deterministic FixGenerator used by the Day 110 evaluation
    benchmark.

    The production Planner decides WHAT should change.

    This benchmark provider supplies deterministic FileEdit
    operations so the current agent can be evaluated
    end-to-end without requiring an LLM.

    A future LLM-powered FixGenerator can replace this provider.
    """

    def __init__(
        self,
        issue: EvaluationIssue | None = None,
    ):
        self.issue = issue

    def generate(
        self,
        plan: FixPlan,
        feedback: FailureFeedback,
    ) -> FixPlan:
        """
        Generate the corrective FixPlan requested by ReflectionLoop.

        The benchmark issue is supplied when the provider is created.
        """

        if self.issue is None:
            raise ValueError(
                "EvaluationFixPlanProvider requires an evaluation issue."
            )

        return self.apply(
            plan=plan,
            issue=self.issue,
        )

    def apply(
        self,
        plan: FixPlan,
        issue: EvaluationIssue,
    ) -> FixPlan:

        if issue.issue_id == "issue-001":
            return self._fix_empty_average(plan)

        if issue.issue_id == "issue-002":
            return self._fix_username_normalization(plan)

        if issue.issue_id == "issue-003":
            return self._fix_negative_values(plan)

        raise ValueError(
            f"Unknown evaluation issue: {issue.issue_id}"
        )

    @staticmethod
    def _fix_empty_average(
        plan: FixPlan,
    ) -> FixPlan:

        return FixPlan(
            summary=plan.summary,
            problem=plan.problem,
            target_files=plan.target_files,
            changes=plan.changes,
            tests_to_run=["tests/test_stats.py"],
            rationale=plan.rationale,
            edits=[
                FileEdit(
                    file_path="app/stats.py",
                    old_text=(
                        "def average(values: list[float]) -> float:\n"
                        "    return sum(values) / len(values)"
                    ),
                    new_text=(
                        "def average(values: list[float]) -> float:\n"
                        "    if not values:\n"
                        "        return 0.0\n"
                        "    return sum(values) / len(values)"
                    ),
                ),
                FileEdit(
                    file_path="tests/test_stats.py",
                    old_text=(
                        "def test_average_handles_single_value():\n"
                        "    assert average([5]) == 5\n"
                    ),
                    new_text=(
                        "def test_average_handles_single_value():\n"
                        "    assert average([5]) == 5\n\n\n"
                        "def test_average_handles_empty_collection():\n"
                        "    assert average([]) == 0.0\n"
                    ),
                ),
            ],
        )

    @staticmethod
    def _fix_username_normalization(
        plan: FixPlan,
    ) -> FixPlan:

        return FixPlan(
            summary=plan.summary,
            problem=plan.problem,
            target_files=plan.target_files,
            changes=plan.changes,
            tests_to_run=["tests/test_greetings.py"],
            rationale=plan.rationale,
            edits=[
                FileEdit(
                    file_path="app/greetings.py",
                    old_text=(
                        "def greet(username: str) -> str:\n"
                        "    return f\"Hello, {username}!\""
                    ),
                    new_text=(
                        "def greet(username: str) -> str:\n"
                        "    username = username.strip()\n"
                        "    return f\"Hello, {username}!\""
                    ),
                ),
                FileEdit(
                    file_path="tests/test_greetings.py",
                    old_text=(
                        "def test_greet_returns_greeting():\n"
                        "    assert greet(\"Alice\") == \"Hello, Alice!\"\n"
                    ),
                    new_text=(
                        "def test_greet_returns_greeting():\n"
                        "    assert greet(\"Alice\") == \"Hello, Alice!\"\n\n\n"
                        "def test_greet_normalizes_username():\n"
                        "    assert greet(\"  Alice  \") == \"Hello, Alice!\"\n"
                    ),
                ),
            ],
        )

    @staticmethod
    def _fix_negative_values(
        plan: FixPlan,
    ) -> FixPlan:

        return FixPlan(
            summary=plan.summary,
            problem=plan.problem,
            target_files=plan.target_files,
            changes=plan.changes,
            tests_to_run=["tests/test_stats.py"],
            rationale=plan.rationale,
            edits=[
                FileEdit(
                    file_path="app/stats.py",
                    old_text=(
                        "def average(values: list[float]) -> float:\n"
                        "    return sum(values) / len(values)"
                    ),
                    new_text=(
                        "def average(values: list[float]) -> float:\n"
                        "    if any(value < 0 for value in values):\n"
                        "        raise ValueError(\n"
                        "            \"values must not contain negative numbers\"\n"
                        "        )\n"
                        "    return sum(values) / len(values)"
                    ),
                ),
                FileEdit(
                    file_path="tests/test_stats.py",
                    old_text=(
                        "def test_average_handles_single_value():\n"
                        "    assert average([5]) == 5\n"
                    ),
                    new_text=(
                        "def test_average_handles_single_value():\n"
                        "    assert average([5]) == 5\n\n\n"
                        "def test_average_rejects_negative_values():\n"
                        "    import pytest\n\n"
                        "    with pytest.raises(ValueError, match=\"negative\"):\n"
                        "        average([1, -2, 3])\n"
                    ),
                ),
            ],
        )