
from app.agent.executor import EditResult, ExecutionResult
from app.agent.reflection import (
    ReflectionIteration,
    ReflectionResult,
)
from app.github.test_results import PytestResultsFormatter
from app.sandbox.models import CommandResult


def test_formats_successful_test_results():
    command_result = CommandResult(
        command="pytest tests/",
        return_code=0,
        stdout="2 passed in 0.12s",
        stderr="",
    )

    execution = ExecutionResult(
        success=True,
        edits=[
            EditResult(
                file_path="app.py",
                success=True,
            )
        ],
        test_results=[command_result],
    )

    reflection = ReflectionResult(
        success=True,
        iterations=[
            ReflectionIteration(
                iteration=1,
                execution=execution,
            )
        ],
    )

    result = PytestResultsFormatter().format(
        reflection
    )

    assert "Iteration 1" in result
    assert "Test command 1: PASSED" in result
    assert "Command: pytest tests/" in result
    assert "Return code: 0" in result
    assert "2 passed in 0.12s" in result


def test_formats_failed_test_results():
    command_result = CommandResult(
        command="pytest tests/",
        return_code=1,
        stdout="1 failed, 2 passed",
        stderr="AssertionError: expected 2, got 3",
    )

    execution = ExecutionResult(
        success=False,
        edits=[
            EditResult(
                file_path="app.py",
                success=True,
            )
        ],
        test_results=[command_result],
        error="One or more tests failed.",
    )

    reflection = ReflectionResult(
        success=False,
        iterations=[
            ReflectionIteration(
                iteration=1,
                execution=execution,
            )
        ],
        error="Tests failed.",
    )

    result = PytestResultsFormatter().format(
        reflection
    )

    assert "Iteration 1" in result
    assert "Test command 1: FAILED" in result
    assert "Command: pytest tests/" in result
    assert "Return code: 1" in result
    assert "1 failed, 2 passed" in result
    assert "AssertionError: expected 2, got 3" in result


def test_formats_multiple_reflection_iterations():
    first_result = CommandResult(
        command="pytest tests/",
        return_code=1,
        stdout="1 failed",
        stderr="AssertionError",
    )

    second_result = CommandResult(
        command="pytest tests/",
        return_code=0,
        stdout="3 passed in 0.15s",
        stderr="",
    )

    first_execution = ExecutionResult(
        success=False,
        edits=[],
        test_results=[first_result],
        error="One or more tests failed.",
    )

    second_execution = ExecutionResult(
        success=True,
        edits=[],
        test_results=[second_result],
    )

    reflection = ReflectionResult(
        success=True,
        iterations=[
            ReflectionIteration(
                iteration=1,
                execution=first_execution,
            ),
            ReflectionIteration(
                iteration=2,
                execution=second_execution,
            ),
        ],
    )

    result = PytestResultsFormatter().format(
        reflection
    )

    assert "Iteration 1" in result
    assert "Iteration 2" in result
    assert "Test command 1: FAILED" in result
    assert "Test command 1: PASSED" in result
    assert "1 failed" in result
    assert "3 passed in 0.15s" in result


def test_handles_no_iterations():
    reflection = ReflectionResult(
        success=False,
        iterations=[],
    )

    result = PytestResultsFormatter().format(
        reflection
    )

    assert result == "No tests were executed."


def test_handles_iteration_without_tests():
    execution = ExecutionResult(
        success=False,
        edits=[],
        test_results=[],
        error="One or more edits failed.",
    )

    reflection = ReflectionResult(
        success=False,
        iterations=[
            ReflectionIteration(
                iteration=1,
                execution=execution,
            )
        ],
    )

    result = PytestResultsFormatter().format(
        reflection
    )

    assert "Iteration 1" in result
    assert (
        "Execution error: One or more edits failed."
        in result
    )
    assert "No test commands were executed." in result
