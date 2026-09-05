import pytest

from app.agent.fixer import FixGenerator
from app.agent.planner import FileEdit, FixPlan
from app.agent.reflection import FailureFeedback


def make_plan():
    return FixPlan(
        summary="Fix add",
        problem="add returns the wrong result.",
        target_files=["app.py"],
        changes=[
            "Fix app.py",
        ],
        tests_to_run=[
            "tests/test_app.py",
        ],
        rationale="The implementation is incorrect.",
        edits=[],
    )


def make_feedback():
    return FailureFeedback(
        iteration=1,
        error="One or more tests failed.",
        test_output=(
            "FAILED tests/test_app.py::test_add "
            "- AssertionError"
        ),
    )


def test_fix_generator_creates_corrective_file_edit():
    def strategy(
        plan,
        feedback,
    ):
        assert feedback.has_output

        return [
            FileEdit(
                file_path="app.py",
                old_text="return a + b - 1",
                new_text="return a + b",
            )
        ]

    generator = FixGenerator(
        correction_strategy=strategy,
    )

    result = generator.generate(
        plan=make_plan(),
        feedback=make_feedback(),
    )

    assert result.summary == (
        "Corrective fix: Fix add"
    )

    assert len(result.edits) == 1

    assert result.edits[0].file_path == "app.py"

    assert result.edits[0].old_text == (
        "return a + b - 1"
    )

    assert result.edits[0].new_text == (
        "return a + b"
    )


def test_fix_generator_rejects_missing_failure_output():
    generator = FixGenerator(
        correction_strategy=lambda plan, feedback: [],
    )

    feedback = FailureFeedback(
        iteration=1,
        error="Failure",
        test_output="",
    )

    with pytest.raises(ValueError):
        generator.generate(
            plan=make_plan(),
            feedback=feedback,
        )


def test_fix_generator_rejects_empty_correction():
    generator = FixGenerator(
        correction_strategy=lambda plan, feedback: [],
    )

    with pytest.raises(ValueError):
        generator.generate(
            plan=make_plan(),
            feedback=make_feedback(),
        )


def test_fix_generator_preserves_tests():
    def strategy(
        plan,
        feedback,
    ):
        return [
            FileEdit(
                file_path="app.py",
                old_text="old",
                new_text="new",
            )
        ]

    plan = make_plan()

    generator = FixGenerator(
        correction_strategy=strategy,
    )

    result = generator.generate(
        plan=plan,
        feedback=make_feedback(),
    )

    assert result.tests_to_run == [
        "tests/test_app.py"
    ]


def test_fix_generator_preserves_target_files():
    def strategy(
        plan,
        feedback,
    ):
        return [
            FileEdit(
                file_path="app.py",
                old_text="old",
                new_text="new",
            )
        ]

    plan = make_plan()

    generator = FixGenerator(
        correction_strategy=strategy,
    )

    result = generator.generate(
        plan=plan,
        feedback=make_feedback(),
    )

    assert result.target_files == [
        "app.py"
    ]