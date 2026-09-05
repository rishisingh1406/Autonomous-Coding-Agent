from __future__ import annotations

from app.evaluation.models import EvaluationReport


class EvaluationMetrics:

    @staticmethod
    def summary(
        report: EvaluationReport,
    ) -> dict[str, float | int]:

        return {
            "total_issues": report.total_issues,
            "successful_issues": (
                report.successful_issues
            ),
            "failed_issues": (
                report.failed_issues
            ),
            "success_rate": (
                report.success_rate
            ),
            "average_iterations": (
                report.average_iterations
            ),
            "average_duration_seconds": (
                report.average_duration_seconds
            ),
        }