from __future__ import annotations

import re
from dataclasses import dataclass

from rank_bm25 import BM25Okapi

from app.repo.indexer import RepoDocument


@dataclass
class RetrievalResult:
    document: RepoDocument
    score: float

    @property
    def path(self) -> str:
        return self.document.path

    @property
    def content(self) -> str:
        return self.document.content

    @property
    def symbol(self) -> str | None:
        return self.document.symbol

    @property
    def symbol_type(self) -> str | None:
        return self.document.symbol_type

    @property
    def start_line(self) -> int:
        return self.document.start_line

    @property
    def end_line(self) -> int:
        return self.document.end_line


class RepoRetriever:
    """
    BM25-based repository code retriever.

    Responsible for finding the most relevant pieces
    of source code for a coding-agent task.
    """

    def __init__(
        self,
        documents: list[RepoDocument] | None = None,
    ):
        self.documents: list[RepoDocument] = []

        self._bm25: BM25Okapi | None = None

        if documents:
            self.build(documents)

    def build(
        self,
        documents: list[RepoDocument],
    ) -> None:

        self.documents = list(documents)

        if not self.documents:
            self._bm25 = None
            return

        tokenized_documents = [
            self._tokenize(
                self._document_text(document)
            )
            for document in self.documents
        ]

        self._bm25 = BM25Okapi(
            tokenized_documents
        )

    def search(
        self,
        query: str,
        top_k: int = 5,
    ) -> list[RetrievalResult]:

        if not query or not query.strip():
            return []

        if not self.documents:
            return []

        if self._bm25 is None:
            return []

        query_tokens = self._tokenize(
            query
        )

        if not query_tokens:
            return []

        top_k = min(
            max(top_k, 1),
            len(self.documents),
        )

        scores = self._bm25.get_scores(
            query_tokens
        )

        ranked_indexes = sorted(
            range(len(scores)),
            key=lambda index: scores[index],
            reverse=True,
        )

        results: list[RetrievalResult] = []

        for index in ranked_indexes[:top_k]:

            results.append(
                RetrievalResult(
                    document=self.documents[index],
                    score=float(scores[index]),
                )
            )

        return results

    def search_issue(
        self,
        title: str,
        body: str = "",
        labels: list[str] | None = None,
        top_k: int = 5,
    ) -> list[RetrievalResult]:

        """
        Search using the complete GitHub issue.

        The query combines:
        - issue title
        - issue body
        - issue labels
        """

        parts: list[str] = []

        if title:
            parts.append(title)

        if body:
            parts.append(body)

        if labels:
            parts.extend(labels)

        query = "\n".join(parts)

        return self.search(
            query=query,
            top_k=top_k,
        )

    def format_context(
        self,
        results: list[RetrievalResult],
    ) -> str:

        if not results:
            return (
                "No relevant repository "
                "context found."
            )

        sections: list[str] = []

        for number, result in enumerate(
            results,
            start=1,
        ):

            document = result.document

            section = (
                f"### Context {number}\n"
                f"File: {document.path}\n"
                f"Lines: "
                f"{document.start_line}-"
                f"{document.end_line}\n"
            )

            if document.symbol:
                section += (
                    f"Symbol: {document.symbol}\n"
                )

            if document.symbol_type:
                section += (
                    f"Type: "
                    f"{document.symbol_type}\n"
                )

            section += (
                "\n"
                "```\n"
                f"{document.content}\n"
                "```"
            )

            sections.append(section)

        return "\n\n".join(sections)

    @staticmethod
    def _document_text(
        document: RepoDocument,
    ) -> str:

        metadata = [
            document.path,
            document.language,
            document.symbol or "",
            document.symbol_type or "",
        ]

        return (
            " ".join(metadata)
            + " "
            + document.content
        )

    @staticmethod
    def _tokenize(
        text: str,
    ) -> list[str]:

        # Break camelCase:
        #
        # getUser -> get User
        #
        text = re.sub(
            r"([a-z0-9])([A-Z])",
            r"\1 \2",
            text,
        )

        # Break snake_case:
        #
        # get_user -> get user
        #
        text = text.replace(
            "_",
            " ",
        )

        text = text.lower()

        return re.findall(
            r"[a-zA-Z0-9]+",
            text,
        )