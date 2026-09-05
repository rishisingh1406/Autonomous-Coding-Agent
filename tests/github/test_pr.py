import pytest

from app.github.pr import PRDescriptionBuilder


def test_build_pr_description():
    builder = PRDescriptionBuilder()

    result = builder.build(
        title="Fix authentication bug",
        summary="Fixed token validation in the authentication flow.",
        diff_summary=(
            " app/auth.py | 12 ++++++++----\n"
            " 1 file changed, 8 insertions(+), 4 deletions(-)"
        ),
        test_results=(
            "==============================\n"
            "5 passed in 0.42s\n"
            "=============================="
        ),
    )

    assert result.title == "Fix authentication bug"

    assert "## Summary" in result.body
    assert "Fixed token validation" in result.body

    assert "## Diff Summary" in result.body
    assert "1 file changed" in result.body

    assert "## Test Results" in result.body
    assert "5 passed" in result.body

    assert "Autonomous Coding Agent" in result.body


def test_build_pr_description_handles_missing_diff():
    builder = PRDescriptionBuilder()

    result = builder.build(
        title="Fix bug",
        summary="Fixed the bug.",
        diff_summary="",
        test_results="5 passed",
    )

    assert "No diff summary available." in result.body


def test_build_pr_description_handles_missing_tests():
    builder = PRDescriptionBuilder()

    result = builder.build(
        title="Fix bug",
        summary="Fixed the bug.",
        diff_summary="1 file changed",
        test_results="",
    )

    assert "No test results available." in result.body


def test_build_pr_description_rejects_empty_title():
    builder = PRDescriptionBuilder()

    with pytest.raises(ValueError):
        builder.build(
            title="",
            summary="Fixed the bug.",
            diff_summary="1 file changed",
            test_results="5 passed",
        )


def test_build_pr_description_rejects_empty_summary():
    builder = PRDescriptionBuilder()

    with pytest.raises(ValueError):
        builder.build(
            title="Fix bug",
            summary="",
            diff_summary="1 file changed",
            test_results="5 passed",
        )