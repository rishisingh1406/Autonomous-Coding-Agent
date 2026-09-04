from pathlib import Path

import pytest

from app.repo.context import RepoRetriever
from app.repo.indexer      import RepoIndexer


@pytest.fixture
def retriever():

    repo = (
        Path(__file__).parent
        / ".."
        / "fixtures"
        / "demo_repo"
    ).resolve()

    indexer = RepoIndexer()

    documents = indexer.index(
        repo
    )

    return RepoRetriever(
        documents
    )


def test_retriever_finds_user_code(
    retriever,
):

    results = retriever.search(
        "user not found",
        top_k=3,
    )

    assert results

    assert any(
        result.path == "app/users.py"
        for result in results
    )



    assert results

    assert any(
        result.symbol == "get_user"
        for result in results
    )


def test_user_code_ranks_first(
    retriever,
):

    results = retriever.search(
        "UserNotFoundError user not found",
        top_k=5,
    )

    assert results

    assert results[0].path == "app/users.py"


def test_retriever_respects_top_k(
    retriever,
):

    results = retriever.search(
        "user",
        top_k=2,
    )

    assert len(results) <= 2


def test_empty_query_returns_empty(
    retriever,
):

    results = retriever.search(
        "",
        top_k=5,
    )

    assert results == []


def test_issue_search(
    retriever,
):

    results = retriever.search_issue(
        title="Users endpoint returns 500",
        body=(
            "When a requested user does not "
            "exist, the endpoint raises an error."
        ),
        labels=[
            "bug",
            "users",
        ],
        top_k=3,
    )

    assert results

    assert any(
        result.path == "app/users.py"
        for result in results
    )


def test_context_formatting(
    retriever,
):

    results = retriever.search(
        "get user missing",
        top_k=2,
    )

    context = retriever.format_context(
        results
    )

    assert "### Context 1" in context

    assert "File:" in context

    assert "Lines:" in context

    assert "```" in context