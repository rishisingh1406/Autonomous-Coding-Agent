from __future__ import annotations

from dataclasses import dataclass, field


@dataclass(frozen=True)
class EvaluationIssue:
    """
    A coding issue used for end-to-end evaluation.
    """

    issue_id: str
    title: str
    body: str

    expected_files: tuple[str, ...] = ()

    expected_tests: tuple[str, ...] = ()


@dataclass
class EvaluationResult:
    """
    Result of running one issue through the agent.
    """

    issue_id: str
    title: str

    success: bool

    iterations: int = 0

    duration_seconds: float = 0.0

    error: str | None = None

    test_output: str = ""

    changed_files: list[str] = field(
        default_factory=list
    )


@dataclass
class EvaluationReport:
    """
    Aggregate results for a complete evaluation run.
    """

    results: list[EvaluationResult] = field(
        default_factory=list
    )

    @property
    def total_issues(self) -> int:
        return len(self.results)

    @property
    def successful_issues(self) -> int:
        return sum(
            result.success
            for result in self.results
        )

    @property
    def failed_issues(self) -> int:
        return (
            self.total_issues
            - self.successful_issues
        )

    @property
    def success_rate(self) -> float:
        if not self.results:
            return 0.0

        return (
            self.successful_issues
            / self.total_issues
        )

    @property
    def average_iterations(self) -> float:
        if not self.results:
            return 0.0

        return sum(
            result.iterations
            for result in self.results
        ) / self.total_issues

    @property
    def average_duration_seconds(self) -> float:
        if not self.results:
            return 0.0

        return sum(
            result.duration_seconds
            for result in self.results
        ) / self.total_issues