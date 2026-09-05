from pathlib import Path

from app.agent.executor import ExecutionResult, Executor
from app.agent.fixer import FixGenerator
from app.agent.loop import ReflectionLoop
from app.agent.planner import FileEdit, FixPlan
from app.agent.reflection import FailureFeedback


class FakeExecutor:
    """
    Returns predefined execution results.

    This allows us to test reflection orchestration
    without running Docker.
    """

    def __init__(
        self,
        results: list[ExecutionResult],
    ):
        self.results = results
        self.calls = 0

    def execute(
        self,
        plan: FixPlan,
        workspace: str | Path,
    ) -> ExecutionResult:

        result = self.results[self.calls]

        self.calls += 1

        return result


class FakeFixGenerator:
    """
    Produces predefined corrective plans and records
    the failure feedback it receives.
    """

    def __init__(
        self,
        plans: list[FixPlan],
    ):
        self.plans = plans
        self.calls = 0
        self.feedback: list[FailureFeedback] = []

    def generate(
        self,
        plan: FixPlan,
        feedback: FailureFeedback,
    ) -> FixPlan:

        self.feedback.append(feedback)

        result = self.plans[self.calls]

        self.calls += 1

        return result


def make_result(
    success: bool,
    stdout: str = "",
    stderr: str = "",
) -> ExecutionResult:

    return ExecutionResult(
        success=success,
        edits=[],
        test_results=[],
        error=None
        if success
        else "One or more tests failed.",
    )


def make_plan(
    name: str = "initial",
) -> FixPlan:

    return FixPlan(
        summary=name,
        problem="Fix the failing behavior.",
        target_files=["app/example.py"],
        changes=["Fix example.py"],
        tests_to_run=["tests/test_example.py"],
        rationale="Test plan.",
        edits=[],
    )


def test_loop_stops_when_first_execution_passes(
    tmp_path,
):
    executor = FakeExecutor(
        results=[
            make_result(success=True),
        ]
    )

    generator = FakeFixGenerator(
        plans=[]
    )

    loop = ReflectionLoop(
        executor=executor,
        fix_generator=generator,
        max_iterations=3,
    )

    result = loop.run(
        initial_plan=make_plan(),
        workspace=tmp_path,
    )

    assert result.success is True
    assert result.iteration_count == 1
    assert executor.calls == 1
    assert generator.calls == 0


def test_loop_generates_corrective_plan_after_failure(
    tmp_path,
):
    executor = FakeExecutor(
        results=[
            make_result(
                success=False,
            ),
            make_result(
                success=True,
            ),
        ]
    )

    corrected_plan = make_plan(
        name="corrective"
    )

    generator = FakeFixGenerator(
        plans=[
            corrected_plan,
        ]
    )

    loop = ReflectionLoop(
        executor=executor,
        fix_generator=generator,
        max_iterations=3,
    )

    result = loop.run(
        initial_plan=make_plan(),
        workspace=tmp_path,
    )

    assert result.success is True
    assert result.iteration_count == 2

    assert executor.calls == 2
    assert generator.calls == 1

    assert generator.feedback[0].iteration == 1


def test_failure_output_is_passed_to_fix_generator(
    tmp_path,
):
    class OutputExecutor:
        def __init__(self):
            self.calls = 0

        def execute(
            self,
            plan,
            workspace,
        ):
            self.calls += 1

            if self.calls == 1:
                return ExecutionResult(
                    success=False,
                    edits=[],
                    test_results=[],
                    error="pytest failed: assertion error",
                )

            return ExecutionResult(
                success=True,
                edits=[],
                test_results=[],
                error=None,
            )

    executor = OutputExecutor()

    generator = FakeFixGenerator(
        plans=[
            make_plan("corrective"),
        ]
    )

    loop = ReflectionLoop(
        executor=executor,
        fix_generator=generator,
        max_iterations=3,
    )

    result = loop.run(
        initial_plan=make_plan(),
        workspace=tmp_path,
    )

    assert result.success is True
    assert result.iteration_count == 2

    feedback = generator.feedback[0]

    assert feedback.iteration == 1

    assert feedback.error == (
        "pytest failed: assertion error"
    )

    assert (
        "Execution error: "
        "pytest failed: assertion error"
        in feedback.test_output
    )


def test_loop_stops_at_max_iterations(
    tmp_path,
):
    executor = FakeExecutor(
        results=[
            make_result(success=False),
            make_result(success=False),
            make_result(success=False),
        ]
    )

    generator = FakeFixGenerator(
        plans=[
            make_plan("fix-1"),
            make_plan("fix-2"),
        ]
    )

    loop = ReflectionLoop(
        executor=executor,
        fix_generator=generator,
        max_iterations=3,
    )

    result = loop.run(
        initial_plan=make_plan(),
        workspace=tmp_path,
    )

    assert result.success is False
    assert result.iteration_count == 3

    assert executor.calls == 3
    assert generator.calls == 2

    assert result.error == (
        "Maximum reflection iterations "
        "reached without passing tests."
    )


def test_loop_applies_corrective_edit_and_passes(
    tmp_path,
):
    """
    End-to-end reflection test.

    Initial implementation:
        add(2, 3) -> 5

    Test expects:
        add(2, 3) == 6

    Initial FixPlan intentionally changes the code
    incorrectly:

        return a + b
        ->
        return a + b - 1

    pytest fails.

    FixGenerator receives the failure feedback and
    produces a corrective FileEdit:

        return a + b - 1
        ->
        return a + b + 1

    pytest then passes and the loop stops.
    """

    workspace = tmp_path / "repo"
    workspace.mkdir()

    source = workspace / "app.py"

    source.write_text(
        """
def add(a, b):
    return a + b
""".strip(),
        encoding="utf-8",
    )

    test_file = workspace / "test_app.py"

    test_file.write_text(
        """
from app import add


def test_add():
    assert add(2, 3) == 6
""".strip(),
        encoding="utf-8",
    )

    class TestSandboxManager:
        """
        Local test double for SandboxManager.

        The production implementation runs Docker.
        This integration test only needs to verify the
        reflection architecture and real pytest behavior.
        """

        def run(
            self,
            workspace,
            command,
        ):
            import subprocess

            result = subprocess.run(
                command,
                cwd=workspace,
                shell=True,
                capture_output=True,
                text=True,
            )

            from app.sandbox.models import CommandResult

            return CommandResult(
                command=command,
                return_code=result.returncode,
                stdout=result.stdout,
                stderr=result.stderr,
                timed_out=False,
            )

    executor = Executor(
        sandbox_manager=TestSandboxManager(),
    )

    initial_plan = make_plan(
        name="Initial incorrect implementation",
    )

    initial_plan.target_files = [
        "app.py",
    ]

    initial_plan.tests_to_run = [
        "test_app.py",
    ]

    initial_plan.edits = [
        FileEdit(
            file_path="app.py",
            old_text="return a + b",
            new_text="return a + b - 1",
        ),
    ]

    def correction_strategy(
        plan,
        feedback,
    ):
        """
        Deterministic correction strategy used only
        to prove the FixGenerator contract.

        A future LLM-backed strategy will replace this.
        """

        assert feedback.has_output

        assert "FAILED" in feedback.test_output

        return [
            FileEdit(
                file_path="app.py",
                old_text="return a + b - 1",
                new_text="return a + b + 1",
            ),
        ]

    generator = FixGenerator(
        correction_strategy=correction_strategy,
    )

    loop = ReflectionLoop(
        executor=executor,
        fix_generator=generator,
        max_iterations=3,
    )

    result = loop.run(
        initial_plan=initial_plan,
        workspace=workspace,
    )

    assert result.success is True

    assert result.iteration_count == 2

    assert len(result.iterations) == 2

    assert result.iterations[0].success is False
    assert result.iterations[1].success is True

    final_source = source.read_text(
        encoding="utf-8",
    )

    assert "return a + b + 1" in final_source
