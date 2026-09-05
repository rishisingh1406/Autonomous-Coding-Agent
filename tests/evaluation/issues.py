from app.evaluation.models import EvaluationIssue


EVALUATION_ISSUES = [
    EvaluationIssue(
        issue_id="issue-001",
        title="Fix average calculation for empty collections",
        body=(
            "The average helper currently raises "
            "ZeroDivisionError when called with an empty "
            "collection. Return 0.0 for an empty collection. "
            "Add or update tests to cover the empty-input case."
        ),
        expected_files=(
            "app/stats.py",
            "tests/test_stats.py",
        ),
        expected_tests=(
            "tests/test_stats.py",
        ),
    ),
    EvaluationIssue(
        issue_id="issue-002",
        title="Normalize usernames before generating greetings",
        body=(
            "The greeting helper should ignore leading and "
            "trailing whitespace in usernames. "
            'greet("  Alice  ") should return '
            '"Hello, Alice!". Add a regression test.'
        ),
        expected_files=(
            "app/greetings.py",
            "tests/test_greetings.py",
        ),
        expected_tests=(
            "tests/test_greetings.py",
        ),
    ),
    EvaluationIssue(
        issue_id="issue-003",
        title="Reject negative values in the statistics helper",
        body=(
            "The statistics helper currently accepts negative "
            "values. Negative values should raise ValueError "
            "with a useful error message. Add a regression test."
        ),
        expected_files=(
            "app/stats.py",
            "tests/test_stats.py",
        ),
        expected_tests=(
            "tests/test_stats.py",
        ),
    ),
]