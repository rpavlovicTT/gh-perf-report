"""Compare two workflow runs and identify differences."""

from typing import List, Optional

from .models import WorkflowReport, JobResult, ComparisonResult, JobConclusion
from ..config import REGRESSION_THRESHOLD, IMPROVEMENT_THRESHOLD


class CompareProcessor:
    """Compare two workflow runs and identify differences."""

    def compare_reports(
        self, baseline: WorkflowReport, current: WorkflowReport
    ) -> List[ComparisonResult]:
        """
        Compare two workflow reports.

        Args:
            baseline: Baseline workflow report
            current: Current workflow report to compare

        Returns:
            List of comparison results for each job
        """
        # Build job lookup maps by extracting model name from job name
        baseline_jobs = {self._get_job_key(job): job for job in baseline.jobs}
        current_jobs = {self._get_job_key(job): job for job in current.jobs}

        # Get all unique job keys
        all_job_keys = sorted(set(baseline_jobs.keys()) | set(current_jobs.keys()))

        comparisons = []
        for job_key in all_job_keys:
            baseline_job = baseline_jobs.get(job_key)
            current_job = current_jobs.get(job_key)

            comparison = self._compare_jobs(job_key, baseline_job, current_job)
            comparisons.append(comparison)

        return comparisons

    def _get_job_key(self, job: JobResult) -> str:
        """
        Extract a comparable key from job name.

        This normalizes job names to allow comparison across different
        workflow runs that might have slightly different naming.
        """
        job_name = job.job_name

        # Extract the model identifier (e.g., "tt-xla-efficientnet" from full job name)
        # Pattern: "run-n150-perf-benchmarks / tt-xla-model-name (n150-perf, 12, 128) benchmark"
        import re

        match = re.search(r"(tt-(?:xla|forge)-[a-zA-Z0-9_-]+)", job_name, re.IGNORECASE)
        if match:
            return match.group(1).lower()

        # Fallback: use full job name
        return job_name.lower()

    def _compare_jobs(
        self,
        job_key: str,
        baseline: Optional[JobResult],
        current: Optional[JobResult],
    ) -> ComparisonResult:
        """Compare two job results."""
        comparison = ComparisonResult(
            job_name=job_key,
            baseline=baseline,
            current=current,
        )

        # Check for missing jobs
        if baseline is None or current is None:
            return comparison

        # Check status changes
        comparison.status_changed = baseline.conclusion != current.conclusion

        # Compare simulation metrics (samples per second)
        if (
            baseline.simulation_metrics
            and current.simulation_metrics
            and baseline.simulation_metrics.samples_per_second
            and current.simulation_metrics.samples_per_second
        ):
            baseline_sps = baseline.simulation_metrics.samples_per_second
            current_sps = current.simulation_metrics.samples_per_second

            comparison.samples_per_sec_delta = current_sps - baseline_sps
            if baseline_sps != 0:
                comparison.samples_per_sec_percent_change = (
                    (current_sps - baseline_sps) / baseline_sps * 100
                )

        # Compare device perf metrics
        if baseline.device_perf_metrics and current.device_perf_metrics:
            baseline_duration = baseline.device_perf_metrics.total_op_duration_ns
            current_duration = current.device_perf_metrics.total_op_duration_ns

            comparison.device_perf_delta_ns = current_duration - baseline_duration
            if baseline_duration != 0:
                comparison.device_perf_percent_change = (
                    (current_duration - baseline_duration) / baseline_duration * 100
                )

        # Determine if regression or improvement
        comparison.is_regression = self._is_regression(comparison)
        comparison.is_improvement = self._is_improvement(comparison)

        return comparison

    def _is_regression(self, comparison: ComparisonResult) -> bool:
        """
        Check if comparison shows a performance regression.

        Regression means:
        - Status changed from success to failure
        - Samples per second decreased by more than threshold
        - Device perf duration increased by more than threshold (higher is worse)
        """
        # Status regression: success -> failure
        if comparison.baseline and comparison.current:
            if (
                comparison.baseline.conclusion == JobConclusion.SUCCESS
                and comparison.current.conclusion == JobConclusion.FAILURE
            ):
                return True

        # Performance regression: significant decrease in samples/sec
        if comparison.samples_per_sec_percent_change is not None:
            if comparison.samples_per_sec_percent_change < REGRESSION_THRESHOLD * 100:
                return True

        # Device perf regression: significant increase in duration (lower is better)
        if comparison.device_perf_percent_change is not None:
            if comparison.device_perf_percent_change > -REGRESSION_THRESHOLD * 100:
                # This means duration increased by more than threshold
                if comparison.device_perf_percent_change > abs(REGRESSION_THRESHOLD * 100):
                    return True

        return False

    def _is_improvement(self, comparison: ComparisonResult) -> bool:
        """
        Check if comparison shows a performance improvement.

        Improvement means:
        - Status changed from failure to success
        - Samples per second increased by more than threshold
        - Device perf duration decreased by more than threshold (lower is better)
        """
        # Status improvement: failure -> success
        if comparison.baseline and comparison.current:
            if (
                comparison.baseline.conclusion == JobConclusion.FAILURE
                and comparison.current.conclusion == JobConclusion.SUCCESS
            ):
                return True

        # Performance improvement: significant increase in samples/sec
        if comparison.samples_per_sec_percent_change is not None:
            if comparison.samples_per_sec_percent_change > IMPROVEMENT_THRESHOLD * 100:
                return True

        # Device perf improvement: significant decrease in duration
        if comparison.device_perf_percent_change is not None:
            if comparison.device_perf_percent_change < -IMPROVEMENT_THRESHOLD * 100:
                return True

        return False
