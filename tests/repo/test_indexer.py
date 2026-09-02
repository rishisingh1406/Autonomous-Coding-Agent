from pathlib import Path

import pytest

from app.repo.indexer import RepoIndexer


@pytest.fixture
def demo_repo() -> Path:
    return (
        Path(__file__).parent
        / ".."
        / "fixtures"
        / "demo_repo"
    ).resolve()


def test_indexer_finds_python_files(
    demo_repo,
):

    indexer = RepoIndexer()

    documents = indexer.index(
        demo_repo
    )

    paths = {
        document.path
        for document in documents
    }

    assert "app/users.py" in paths
    assert "app/payments.py" in paths
    assert "app/auth.py" in paths
    assert "tests/test_users.py" in paths


def test_indexer_extracts_functions(
    demo_repo,
):

    indexer = RepoIndexer()

    documents = indexer.index(
        demo_repo
    )

    symbols = {
        document.symbol
        for document in documents
        if document.symbol
    }

    assert "get_user" in symbols
    assert "create_user" in symbols
    assert "delete_user" in symbols


def test_indexer_extracts_classes(
    demo_repo,
):

    indexer = RepoIndexer()

    documents = indexer.index(
        demo_repo
    )

    classes = [
        document
        for document in documents
        if document.symbol == "UserNotFoundError"
    ]

    assert len(classes) == 1

    assert classes[0].symbol_type == "class"


def test_indexer_preserves_line_numbers(
    demo_repo,
):

    indexer = RepoIndexer()

    documents = indexer.index(
        demo_repo
    )

    get_user_documents = [
        document
        for document in documents
        if document.symbol == "get_user"
    ]

    assert len(get_user_documents) == 1

    document = get_user_documents[0]

    assert document.start_line > 0

    assert document.end_line >= document.start_line


def test_indexer_ignores_git_directory(
    demo_repo,
):

    # The fixture itself may already be inside a Git
    # repository, so .git may already exist.
    #
    # We don't need to create it. We only need to verify
    # that the indexer ignores it.

    git_directory = demo_repo / ".git"

    if not git_directory.exists():
        git_directory.mkdir()

    secret_file = (
        git_directory
        / "secret.py"
    )

    secret_file.write_text(
        "password = 'secret'",
        encoding="utf-8",
    )

    indexer = RepoIndexer()

    documents = indexer.index(
        demo_repo
    )

    paths = [
        document.path
        for document in documents
    ]

    assert not any(
        ".git" in path
        for path in paths
    )