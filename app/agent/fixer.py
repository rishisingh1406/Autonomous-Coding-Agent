from __future__ import annotations

from collections.abc import Callable

from app.agent.planner import FileEdit, FixPlan
from app.agent.reflection import FailureFeedback


CorrectionStrategy = Callable[
    [FixPlan, FailureFeedback],
    list[FileEdit],
]


class FixGenerator:
    """
    Generates a corrective FixPlan from failure feedback.

    The correction strategy is intentionally injectable.

    Today:
        deterministic/test strategy

    Later:
        LLM-powered failure analysis + code generation

    This keeps the reflection loop independent from
    the specific intelligence used to generate fixes.
    """

    def __init__(
        self,
        correction_strategy: CorrectionStrategy,
    ):
        self.correction_strategy = correction_strategy

    def generate(
        self,
        plan: FixPlan,
        feedback: FailureFeedback,
    ) -> FixPlan:
        """
        Generate the next corrective FixPlan.
        """

        if not feedback.has_output:
            raise ValueError(
                "Cannot generate a corrective plan without "
                "test failure output."
            )

        edits = self.correction_strategy(
            plan,
            feedback,
        )

        if not edits:
            raise ValueError(
                "Correction strategy produced no file edits."
            )

        return FixPlan(
            summary=(
                f"Corrective fix: {plan.summary}"
            ),

            problem=(
                f"{plan.problem}\n\n"
                "Previous attempt failed with:\n"
                f"{feedback.test_output}"
            ),

            target_files=list(
                plan.target_files
            ),

            changes=[
                (
                    f"Apply corrective edit to {edit.file_path}."
                )
                for edit in edits
            ],

            tests_to_run=list(
                plan.tests_to_run
            ),

            rationale=(
                "Generated from the previous FixPlan and "
                "captured test failure feedback."
            ),

            edits=edits,
        )