from pathlib import Path

from app.agent.planner import FixPlan, Planner
from app.repo.context import RepoRetriever
from app.repo.indexer import RepoIndexer


FIXTURE_REPO = (
    Path(__file__).resolve().parents[1]
    / "fixtures"
    / "demo_repo"
)


def build_context():
    documents = RepoIndexer().index(FIXTURE_REPO)

    retriever = RepoRetriever(documents)

    return retriever.search_issue(
        title="Fix missing user behavior",
        body="get_user should return None when the user does not exist.",
        top_k=5,
    )


def test_planner_returns_fix_plan():

    planner = Planner()

    context = build_context()

    plan = planner.plan(
        issue_title="Fix missing user behavior",
        issue_body=(
            "get_user should return None "
            "when the user does not exist."
        ),
        context=context,
    )

    assert isinstance(plan, FixPlan)


def test_planner_identifies_target_files():

    planner = Planner()

    context = build_context()

    plan = planner.plan(
        issue_title="Fix missing user behavior",
        issue_body=(
            "get_user should return None "
            "when the user does not exist."
        ),
        context=context,
    )

    assert plan.target_files

    assert any(
        "users.py" in path
        for path in plan.target_files
    )


def test_planner_preserves_issue_problem():

    planner = Planner()

    context = build_context()

    plan = planner.plan(
        issue_title="Fix missing user behavior",
        issue_body="Return None for missing users.",
        context=context,
    )

    assert plan.problem == "Return None for missing users."


def test_planner_generates_changes():

    planner = Planner()

    context = build_context()

    plan = planner.plan(
        issue_title="Fix missing user behavior",
        issue_body="Return None for missing users.",
        context=context,
    )

    assert plan.changes
    assert all(
        isinstance(change, str)
        for change in plan.changes
    )


def test_planner_detects_test_files():

    planner = Planner()

    context = build_context()

    plan = planner.plan(
        issue_title="Fix user behavior",
        issue_body="Fix the missing user behavior.",
        context=context,
    )

    assert any(
        "test" in path.lower()
        for path in plan.tests_to_run
    )


def test_planner_requires_issue_title():

    planner = Planner()

    try:
        planner.plan(
            issue_title="",
            issue_body="Something is broken.",
        )
    except ValueError as exc:
        assert "Issue title" in str(exc)
    else:
        raise AssertionError(
            "Planner should reject an empty issue title."
        )


def test_planner_handles_missing_context():

    planner = Planner()

    plan = planner.plan(
        issue_title="Fix authentication bug",
        issue_body="Authentication is failing.",
        context=[],
    )

    assert isinstance(plan, FixPlan)

    assert plan.target_files == []

    assert plan.changes

    assert plan.tests_to_run == []