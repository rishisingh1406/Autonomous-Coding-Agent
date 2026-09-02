from __future__ import annotations

import ast
import hashlib
from pathlib import Path

from pydantic import BaseModel, Field


SUPPORTED_EXTENSIONS = {
    ".py": "python",
    ".js": "javascript",
    ".jsx": "javascript",
    ".ts": "typescript",
    ".tsx": "typescript",
    ".java": "java",
    ".go": "go",
    ".rs": "rust",
    ".c": "c",
    ".h": "c",
    ".cpp": "cpp",
    ".cc": "cpp",
    ".cxx": "cpp",
    ".hpp": "cpp",
}


IGNORED_DIRECTORIES = {
    ".git",
    ".hg",
    ".svn",
    "__pycache__",
    ".pytest_cache",
    ".mypy_cache",
    ".ruff_cache",
    ".venv",
    "venv",
    "env",
    "node_modules",
    "dist",
    "build",
    ".idea",
    ".vscode",
}


class RepoDocument(BaseModel):
    """
    Searchable unit of repository context.
    """

    id: str

    path: str

    language: str

    content: str

    start_line: int

    end_line: int

    symbol: str | None = None

    symbol_type: str | None = None

    metadata: dict = Field(default_factory=dict)


class RepoIndexer:
    """
    Indexes source files inside a repository.

    Python files are parsed with AST.

    Other supported languages are split into
    overlapping line-based chunks.
    """

    def __init__(
        self,
        chunk_size: int = 80,
        chunk_overlap: int = 15,
        max_file_size: int = 500_000,
    ):
        self.chunk_size = chunk_size
        self.chunk_overlap = chunk_overlap
        self.max_file_size = max_file_size

    def index(
        self,
        repo_path: str | Path,
    ) -> list[RepoDocument]:

        repo_path = Path(repo_path).resolve()

        if not repo_path.exists():
            raise FileNotFoundError(
                f"Repository does not exist: {repo_path}"
            )

        if not repo_path.is_dir():
            raise ValueError(
                f"Repository path is not a directory: {repo_path}"
            )

        documents: list[RepoDocument] = []

        for file_path in self._iter_source_files(
            repo_path
        ):

            relative_path = file_path.relative_to(
                repo_path
            )

            # IMPORTANT:
            # Always store repository paths using
            # forward slashes so the representation is
            # platform-independent.
            relative_path_str = relative_path.as_posix()

            language = SUPPORTED_EXTENSIONS[
                file_path.suffix.lower()
            ]

            try:
                content = file_path.read_text(
                    encoding="utf-8"
                )

            except UnicodeDecodeError:
                continue

            if not content.strip():
                continue

            if (
                len(content.encode("utf-8"))
                > self.max_file_size
            ):
                continue

            if language == "python":

                file_documents = (
                    self._index_python_file(
                        relative_path=relative_path_str,
                        content=content,
                    )
                )

            else:

                file_documents = (
                    self._index_generic_file(
                        relative_path=relative_path_str,
                        content=content,
                        language=language,
                    )
                )

            documents.extend(file_documents)

        return documents

    def _iter_source_files(
        self,
        repo_path: Path,
    ):
        for path in repo_path.rglob("*"):

            if not path.is_file():
                continue

            if (
                path.suffix.lower()
                not in SUPPORTED_EXTENSIONS
            ):
                continue

            relative_parts = path.relative_to(
                repo_path
            ).parts

            if any(
                directory in IGNORED_DIRECTORIES
                for directory in relative_parts
            ):
                continue

            yield path

    def _index_python_file(
        self,
        relative_path: str,
        content: str,
    ) -> list[RepoDocument]:

        lines = content.splitlines()

        try:
            tree = ast.parse(content)

        except SyntaxError:

            return self._index_generic_file(
                relative_path=relative_path,
                content=content,
                language="python",
            )

        documents: list[RepoDocument] = []

        module_context = (
            self._extract_module_context(
                tree=tree,
                lines=lines,
            )
        )

        if module_context:

            start_line = min(
                line_number
                for line_number, _ in module_context
            )

            end_line = max(
                line_number
                for line_number, _ in module_context
            )

            module_content = "\n".join(
                content_line
                for _, content_line in module_context
            )

            documents.append(
                self._create_document(
                    path=relative_path,
                    language="python",
                    content=module_content,
                    start_line=start_line,
                    end_line=end_line,
                    symbol=None,
                    symbol_type="module",
                )
            )

        for node in ast.walk(tree):

            if not isinstance(
                node,
                (
                    ast.FunctionDef,
                    ast.AsyncFunctionDef,
                    ast.ClassDef,
                ),
            ):
                continue

            if not hasattr(node, "lineno"):
                continue

            start_line = node.lineno

            end_line = getattr(
                node,
                "end_lineno",
                node.lineno,
            )

            code = "\n".join(
                lines[start_line - 1:end_line]
            )

            if not code.strip():
                continue

            symbol = getattr(
                node,
                "name",
                None,
            )

            documents.append(
                self._create_document(
                    path=relative_path,
                    language="python",
                    content=code,
                    start_line=start_line,
                    end_line=end_line,
                    symbol=symbol,
                    symbol_type=self._symbol_type(node),
                )
            )

        if not documents:

            return self._index_generic_file(
                relative_path=relative_path,
                content=content,
                language="python",
            )

        return documents

    def _extract_module_context(
        self,
        tree: ast.Module,
        lines: list[str],
    ) -> list[tuple[int, str]]:

        results: list[tuple[int, str]] = []

        for node in tree.body:

            include = isinstance(
                node,
                (
                    ast.Import,
                    ast.ImportFrom,
                    ast.Assign,
                    ast.AnnAssign,
                ),
            )

            if not include:
                continue

            start_line = getattr(
                node,
                "lineno",
                None,
            )

            end_line = getattr(
                node,
                "end_lineno",
                start_line,
            )

            if start_line is None:
                continue

            for line_number in range(
                start_line,
                end_line + 1,
            ):

                if 1 <= line_number <= len(lines):

                    results.append(
                        (
                            line_number,
                            lines[line_number - 1],
                        )
                    )

        return results

    def _index_generic_file(
        self,
        relative_path: str,
        content: str,
        language: str,
    ) -> list[RepoDocument]:

        lines = content.splitlines()

        documents: list[RepoDocument] = []

        step = max(
            1,
            self.chunk_size - self.chunk_overlap,
        )

        for start_index in range(
            0,
            len(lines),
            step,
        ):

            end_index = min(
                start_index + self.chunk_size,
                len(lines),
            )

            chunk_lines = lines[
                start_index:end_index
            ]

            chunk = "\n".join(
                chunk_lines
            )

            if not chunk.strip():
                continue

            documents.append(
                self._create_document(
                    path=relative_path,
                    language=language,
                    content=chunk,
                    start_line=start_index + 1,
                    end_line=end_index,
                    symbol=None,
                    symbol_type="chunk",
                )
            )

            if end_index >= len(lines):
                break

        return documents

    @staticmethod
    def _symbol_type(
        node: ast.AST,
    ) -> str:

        if isinstance(node, ast.ClassDef):
            return "class"

        if isinstance(
            node,
            ast.AsyncFunctionDef,
        ):
            return "async_function"

        return "function"

    @staticmethod
    def _create_document(
        path: str,
        language: str,
        content: str,
        start_line: int,
        end_line: int,
        symbol: str | None,
        symbol_type: str | None,
    ) -> RepoDocument:

        raw_id = (
            f"{path}:"
            f"{start_line}:"
            f"{end_line}:"
            f"{content}"
        )

        document_id = hashlib.sha1(
            raw_id.encode("utf-8")
        ).hexdigest()

        return RepoDocument(
            id=document_id,
            path=path,
            language=language,
            content=content,
            start_line=start_line,
            end_line=end_line,
            symbol=symbol,
            symbol_type=symbol_type,
        )