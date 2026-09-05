import subprocess

from app.github.diff import DiffSummarizer


def run_git(repo, *args):
    return subprocess.run(
        ["git", *args],
        cwd=repo,
        check=True,
        capture_output=True,
        text=True,
    )


def test_diff_summarizer(tmp_path):
    repo = tmp_path / "repo"
    repo.mkdir()

    run_git(repo, "init", "-b", "main")

    run_git(
        repo,
        "config",
        "user.name",
        "Test User",
    )

    run_git(
        repo,
        "config",
        "user.email",
        "test@example.com",
    )

    app_file = repo / "app.py"

    app_file.write_text(
        "print('hello')\n",
        encoding="utf-8",
    )

    run_git(repo, "add", "-A")

    run_git(
        repo,
        "commit",
        "-m",
        "initial commit",
    )

    run_git(
        repo,
        "switch",
        "-c",
        "agent/fix",
    )

    app_file.write_text(
        "print('hello')\n"
        "print('world')\n",
        encoding="utf-8",
    )

    new_file = repo / "test_app.py"

    new_file.write_text(
        "def test_example():\n"
        "    assert True\n",
        encoding="utf-8",
    )

    # Commit the agent changes so that
    # main...HEAD contains the changes.
    run_git(repo, "add", "-A")

    run_git(
        repo,
        "commit",
        "-m",
        "agent changes",
    )

    summary = DiffSummarizer().summarize(
        repo,
        base_branch="main",
    )

    assert summary.files_changed == 2
    assert summary.insertions == 3
    assert summary.deletions == 0

    text = summary.as_text()

    assert "Files changed: 2" in text
    assert "Insertions: 3" in text
    assert "Deletions: 0" in text


def test_diff_summarizer_rejects_missing_repository(
    tmp_path,
):
    missing = tmp_path / "missing"

    try:
        DiffSummarizer().summarize(missing)
    except FileNotFoundError:
        pass
    else:
        raise AssertionError(
            "Expected FileNotFoundError"
        )