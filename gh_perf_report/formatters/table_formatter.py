"""Format reports as rich console tables."""

from typing import List, Optional

from rich.console import Console
from rich.table import Table
from rich.text import Text

from ..processors.models import (
    WorkflowReport,
    JobResult,
    ComparisonResult,
    JobConclusion,
)
from .color_scheme import ColorScheme


class TableFormatter:
    """Format reports as rich console tables."""

    def __init__(self, console: Optional[Console] = None):
        """
        Initialize formatter.

        Args:
            console: Optional Rich console instance
        """
        self.console = console or Console()
        self.colors = ColorScheme()

    def print_workflow_report(self, report: WorkflowReport) -> None:
        """Print single workflow run report."""
        # Print header
        self.console.print(f"\n[{self.colors.HEADER}]Workflow Run Report[/{self.colors.HEADER}]")
        self.console.print(f"Repo: {report.repo}")
        self.console.print(f"Run ID: {report.run_id}")
        self.console.print(f"Workflow: {report.workflow_name}")
        self.console.print(f"Branch: {report.branch}")
        self.console.print(
            f"Status: {self._colorize_status(report.status, report.conclusion)}"
        )
        self.console.print(f"Created: {report.created_at}\n")

        # Determine max number of stages across all jobs
        max_stages = 0
        for job in report.jobs:
            if job.device_perf_metrics and job.device_perf_metrics.stages:
                max_stages = max(max_stages, len(job.device_perf_metrics.stages))

        # Create table
        table = Table(
            title="Benchmark Results",
            show_header=True,
            header_style=self.colors.TABLE_HEADER,
        )
        table.add_column("Job", style=self.colors.JOB_NAME, no_wrap=False, max_width=40)
        table.add_column("Status", justify="center", width=10)
        table.add_column("Samples/sec", justify="right", width=12)

        # Add dynamic stage columns under "Device Perf" parent header
        if max_stages > 0:
            # First stage column shows the parent header
            table.add_column("Device Perf\nStage 1 (ms)", justify="right", width=12)
            # Subsequent stage columns align under the parent
            for i in range(1, max_stages):
                table.add_column(f"\nStage {i+1} (ms)", justify="right", width=12)
            # Add total column if there are multiple stages
            if max_stages > 1:
                table.add_column("\nTotal (ms)", justify="right", width=10)

        table.add_column("Error", style=self.colors.ERROR, no_wrap=False, max_width=35)

        # Add rows
        for job in report.jobs:
            self._add_job_row_with_stages(table, job, max_stages)

        self.console.print(table)

        # Print summary
        self._print_summary(report)

    def print_comparison_report(
        self,
        comparisons: List[ComparisonResult],
        baseline: WorkflowReport,
        current: WorkflowReport,
    ) -> None:
        """Print comparison report between two runs."""
        # Print header
        self.console.print(f"\n[{self.colors.HEADER}]Comparison Report[/{self.colors.HEADER}]")
        self.console.print(
            f"Baseline: {baseline.repo} run {baseline.run_id} ({baseline.branch})"
        )
        self.console.print(
            f"Current:  {current.repo} run {current.run_id} ({current.branch})\n"
        )

        # Create table
        table = Table(
            title="Performance Comparison",
            show_header=True,
            header_style=self.colors.TABLE_HEADER,
        )
        table.add_column("Job", style=self.colors.JOB_NAME, no_wrap=False, width=30)
        table.add_column("Status", justify="center", width=16)
        table.add_column("Samples/sec\nDelta", justify="right", width=15)
        table.add_column("Samples/sec\nChange %", justify="right", width=12)
        table.add_column("Device Perf\nDelta (ms)", justify="right", width=15)
        table.add_column("Device Perf\nChange %", justify="right", width=12)
        table.add_column("Result", justify="center", width=12)

        # Add rows
        for comparison in comparisons:
            self._add_comparison_row(table, comparison)

        self.console.print(table)

        # Print summary
        self._print_comparison_summary(comparisons)

    def _add_job_row(self, table: Table, job: JobResult) -> None:
        """Add a row for a job result."""
        # Simplified job name (extract model name)
        job_display = self._simplify_job_name(job.job_name)

        # Status
        status = self._format_status(job.conclusion)

        # Samples per second
        samples_per_sec = self._format_samples_per_sec(job)

        # Device perf (convert ns to ms)
        device_perf = self._format_device_perf(job)

        # Error message
        error = self._format_error(job)

        table.add_row(job_display, status, samples_per_sec, device_perf, error)

    def _add_job_row_with_stages(
        self, table: Table, job: JobResult, max_stages: int
    ) -> None:
        """Add a row for a job result with dynamic stage columns."""
        # Simplified job name (extract model name)
        job_display = self._simplify_job_name(job.job_name)

        # Status
        status = self._format_status(job.conclusion)

        # Samples per second
        samples_per_sec = self._format_samples_per_sec(job)

        # Build row data
        row_data = [job_display, status, samples_per_sec]

        # Add stage columns
        stages = []
        if job.device_perf_metrics and job.device_perf_metrics.stages:
            stages = job.device_perf_metrics.stages

        for i in range(max_stages):
            if i < len(stages):
                row_data.append(f"{stages[i].duration_ms:.2f}")
            else:
                row_data.append("N/A")

        # Add total column if multiple stages
        if max_stages > 1:
            if job.device_perf_metrics:
                row_data.append(f"{job.device_perf_metrics.total_op_duration_ms:.2f}")
            else:
                row_data.append("N/A")

        # Error message
        error = self._format_error(job)
        row_data.append(error)

        table.add_row(*row_data)

    def _add_comparison_row(self, table: Table, comparison: ComparisonResult) -> None:
        """Add a row for a comparison result."""
        # Status comparison
        status = self._format_status_comparison(comparison)

        # Samples/sec delta and percent
        samples_delta = self._format_samples_delta(comparison)
        samples_percent = self._format_samples_percent(comparison)

        # Device perf delta and percent
        device_delta = self._format_device_delta(comparison)
        device_percent = self._format_device_percent(comparison)

        # Result (regression/improvement/neutral)
        result = self._format_result(comparison)

        table.add_row(
            comparison.job_name,
            status,
            samples_delta,
            samples_percent,
            device_delta,
            device_percent,
            result,
        )

    def _simplify_job_name(self, job_name: str) -> str:
        """Extract simplified job name for display."""
        import re

        match = re.search(r"(tt-(?:xla|forge)-[a-zA-Z0-9_-]+)", job_name, re.IGNORECASE)
        if match:
            return match.group(1)
        return job_name[:50] if len(job_name) > 50 else job_name

    def _format_status(self, conclusion: Optional[JobConclusion]) -> Text:
        """Format job conclusion with color."""
        if conclusion is None:
            return Text("PENDING", style=self.colors.PENDING)

        conclusion_str = conclusion.value.upper()
        if conclusion == JobConclusion.SUCCESS:
            return Text("+ " + conclusion_str, style=self.colors.SUCCESS)
        elif conclusion == JobConclusion.FAILURE:
            return Text("x " + conclusion_str, style=self.colors.FAILURE)
        elif conclusion == JobConclusion.SKIPPED:
            return Text("o " + conclusion_str, style=self.colors.SKIPPED)
        else:
            return Text(conclusion_str, style=self.colors.PENDING)

    def _format_status_comparison(self, comparison: ComparisonResult) -> Text:
        """Format status comparison."""
        if comparison.baseline is None:
            return Text("NEW", style=self.colors.RESULT_NEW)
        if comparison.current is None:
            return Text("REMOVED", style=self.colors.RESULT_REMOVED)

        baseline_status = (
            comparison.baseline.conclusion.value
            if comparison.baseline.conclusion
            else "unknown"
        )
        current_status = (
            comparison.current.conclusion.value
            if comparison.current.conclusion
            else "unknown"
        )

        if comparison.status_changed:
            style = (
                self.colors.FAILURE
                if current_status == "failure"
                else self.colors.SUCCESS
            )
            return Text(f"{baseline_status} -> {current_status}", style=style)
        else:
            return self._format_status(comparison.current.conclusion)

    def _format_samples_per_sec(self, job: JobResult) -> str:
        """Format samples per second value."""
        if job.simulation_metrics and job.simulation_metrics.samples_per_second:
            return f"{job.simulation_metrics.samples_per_second:.2f}"
        return "N/A"

    def _format_device_perf(self, job: JobResult) -> str:
        """Format device perf value (convert ns to ms)."""
        if job.device_perf_metrics:
            return f"{job.device_perf_metrics.total_op_duration_ms:.2f}"
        return "N/A"

    def _format_samples_delta(self, comparison: ComparisonResult) -> Text:
        """Format samples per second delta with color."""
        if comparison.samples_per_sec_delta is None:
            return Text("N/A", style=self.colors.NEUTRAL)

        delta = comparison.samples_per_sec_delta
        color = self._get_delta_color(delta, inverse=False)
        symbol = "+" if delta >= 0 else ""
        return Text(f"{symbol}{delta:.2f}", style=color)

    def _format_samples_percent(self, comparison: ComparisonResult) -> Text:
        """Format samples per second percent change with color."""
        if comparison.samples_per_sec_percent_change is None:
            return Text("N/A", style=self.colors.NEUTRAL)

        percent = comparison.samples_per_sec_percent_change
        color = self._get_delta_color(percent, inverse=False)
        symbol = "+" if percent >= 0 else ""
        return Text(f"{symbol}{percent:.1f}%", style=color)

    def _format_device_delta(self, comparison: ComparisonResult) -> Text:
        """Format device perf delta with color (ms)."""
        if comparison.device_perf_delta_ms is None:
            return Text("N/A", style=self.colors.NEUTRAL)

        delta_ms = comparison.device_perf_delta_ms
        color = self._get_delta_color(delta_ms, inverse=True)  # Lower is better
        symbol = "+" if delta_ms >= 0 else ""
        return Text(f"{symbol}{delta_ms:.2f}", style=color)

    def _format_device_percent(self, comparison: ComparisonResult) -> Text:
        """Format device perf percent change with color."""
        if comparison.device_perf_percent_change is None:
            return Text("N/A", style=self.colors.NEUTRAL)

        percent = comparison.device_perf_percent_change
        color = self._get_delta_color(percent, inverse=True)  # Lower is better
        symbol = "+" if percent >= 0 else ""
        return Text(f"{symbol}{percent:.1f}%", style=color)

    def _format_result(self, comparison: ComparisonResult) -> Text:
        """Format overall result indicator."""
        if comparison.is_regression:
            return Text("REGRESSION", style=self.colors.RESULT_REGRESSION)
        elif comparison.is_improvement:
            return Text("IMPROVEMENT", style=self.colors.RESULT_IMPROVEMENT)
        elif comparison.baseline is None:
            return Text("NEW", style=self.colors.RESULT_NEW)
        elif comparison.current is None:
            return Text("REMOVED", style=self.colors.RESULT_REMOVED)
        else:
            return Text("NEUTRAL", style=self.colors.RESULT_NEUTRAL)

    def _format_error(self, job: JobResult) -> str:
        """Format error message."""
        parts = []
        if job.failed_step:
            parts.append(f"Step: {job.failed_step}")
        if job.error_message:
            # Truncate long error messages
            max_len = 60
            error = job.error_message
            error_text = error[:max_len] + "..." if len(error) > max_len else error
            parts.append(error_text)
        return " | ".join(parts) if parts else ""

    def _get_delta_color(self, value: float, inverse: bool = False) -> str:
        """Get color for delta value."""
        if abs(value) < 0.01:  # Negligible change
            return self.colors.UNCHANGED

        # For inverse metrics (like duration), lower is better
        if inverse:
            value = -value

        if value > 0:
            return self.colors.IMPROVEMENT
        else:
            return self.colors.REGRESSION

    def _colorize_status(self, status: str, conclusion: Optional[str]) -> Text:
        """Colorize workflow status."""
        if status == "completed":
            if conclusion == "success":
                return Text(f"{status} ({conclusion})", style=self.colors.SUCCESS)
            elif conclusion == "failure":
                return Text(f"{status} ({conclusion})", style=self.colors.FAILURE)
        return Text(f"{status} ({conclusion or 'unknown'})", style=self.colors.PENDING)

    def _print_summary(self, report: WorkflowReport) -> None:
        """Print summary statistics."""
        total = len(report.jobs)
        self.console.print(f"\n[bold]Summary:[/bold]")
        self.console.print(f"  Total jobs: {total}")
        self.console.print(f"  [{self.colors.SUCCESS}]Success: {report.success_count}[/{self.colors.SUCCESS}]")
        self.console.print(f"  [{self.colors.FAILURE}]Failed: {report.failure_count}[/{self.colors.FAILURE}]")
        self.console.print(f"  [{self.colors.SKIPPED}]Skipped: {report.skipped_count}[/{self.colors.SKIPPED}]")

    def _print_comparison_summary(self, comparisons: List[ComparisonResult]) -> None:
        """Print comparison summary."""
        regressions = sum(1 for c in comparisons if c.is_regression)
        improvements = sum(1 for c in comparisons if c.is_improvement)
        neutral = sum(
            1
            for c in comparisons
            if not c.is_regression and not c.is_improvement and c.baseline and c.current
        )
        new_jobs = sum(1 for c in comparisons if c.baseline is None)
        removed_jobs = sum(1 for c in comparisons if c.current is None)

        self.console.print(f"\n[bold]Summary:[/bold]")
        self.console.print(f"  Total comparisons: {len(comparisons)}")
        self.console.print(f"  [{self.colors.RESULT_REGRESSION}]Regressions: {regressions}[/{self.colors.RESULT_REGRESSION}]")
        self.console.print(f"  [{self.colors.RESULT_IMPROVEMENT}]Improvements: {improvements}[/{self.colors.RESULT_IMPROVEMENT}]")
        self.console.print(f"  [{self.colors.RESULT_NEUTRAL}]Neutral: {neutral}[/{self.colors.RESULT_NEUTRAL}]")
        if new_jobs > 0:
            self.console.print(f"  [{self.colors.RESULT_NEW}]New: {new_jobs}[/{self.colors.RESULT_NEW}]")
        if removed_jobs > 0:
            self.console.print(f"  [{self.colors.RESULT_REMOVED}]Removed: {removed_jobs}[/{self.colors.RESULT_REMOVED}]")
