from pathlib import Path

from app.agent.executor import Executor
from app.agent.loop import ReflectionLoop
from app.agent.planner import Planner
from app.evaluation.fix_plans import EvaluationFixPlanProvider
from app.evaluation.runner import EvaluationRunner
from app.sandbox.manager import SandboxManager

from tests.evaluation.issues import EVALUATION_ISSUES


def test_three_issues_end_to_end(tmp_path: Path):

    project_root = (
        Path(__file__)
        .resolve()
        .parents[2]
    )

    fixture_repo = (
        project_root
        / "tests"
        / "fixtures"
        / "evaluation_repo"
    )

    sandbox_manager = SandboxManager()

    executor = Executor(
        sandbox_manager=sandbox_manager
    )

    reflection_loop = ReflectionLoop(
        executor=executor,
        max_iterations=3,
    )

    runner = EvaluationRunner(
        planner=Planner(),
        reflection_loop=reflection_loop,
        sandbox_manager=sandbox_manager,
        fixture_repo=fixture_repo,
        workspace_root=(
            tmp_path / "workspaces"
        ),
        fix_provider=EvaluationFixPlanProvider(),
    )

    report = runner.run(
        EVALUATION_ISSUES
    )

    assert report.total_issues == 3
    assert report.successful_issues == 3
    assert report.failed_issues == 0
    assert report.success_rate == 1.0

    for result in report.results:
        assert result.success
        assert result.iterations >= 1
        assert result.duration_seconds > 0
        assert result.changed_files
        assert result.test_output
        assert result.error is None