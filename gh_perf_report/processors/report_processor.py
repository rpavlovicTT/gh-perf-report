"""Process workflow runs and extract performance metrics."""

import concurrent.futures
import tempfile
from pathlib import Path
from typing import List, Optional

from ..api.github_client import GitHubClient
from ..parsers.log_parser import LogParser
from ..parsers.csv_parser import CSVParser
from .models import (
    WorkflowReport,
    JobResult,
    JobStatus,
    JobConclusion,
    DevicePerfMetrics,
)
from ..utils.errors import ProcessingError
from ..config import BENCHMARK_JOB_PATTERNS, DEFAULT_MAX_WORKERS


class ReportProcessor:
    """Process workflow run and extract performance metrics."""

    def __init__(self, github_client: GitHubClient):
        """
        Initialize report processor.

        Args:
            github_client: GitHub API client instance
        """
        self.github = github_client
        self.log_parser = LogParser()
        self.csv_parser = CSVParser()

    def process_workflow_run(
        self, owner: str, repo: str, run_id: int, max_workers: int = DEFAULT_MAX_WORKERS
    ) -> WorkflowReport:
        """
        Process a complete workflow run and extract all metrics.

        Args:
            owner: GitHub repo owner
            repo: Repository name
            run_id: Workflow run ID
            max_workers: Max parallel workers for job processing

        Returns:
            Complete workflow report with all job metrics
        """
        # Fetch workflow run details
        run_data = self.github.get_workflow_run(owner, repo, run_id)
        jobs_data = self.github.get_workflow_jobs(owner, repo, run_id)

        # Filter benchmark jobs
        benchmark_jobs = [job for job in jobs_data if self._is_benchmark_job(job["name"])]

        # Build artifact cache once (handles workflow re-runs with different job IDs)
        artifact_cache = self.github.build_artifact_cache(owner, repo, run_id)

        # Process jobs in parallel
        job_results = self._process_jobs_parallel(
            owner, repo, run_id, benchmark_jobs, max_workers, artifact_cache
        )

        return WorkflowReport(
            run_id=run_id,
            repo=f"{owner}/{repo}",
            workflow_name=run_data.get("name", "Unknown"),
            branch=run_data.get("head_branch", "Unknown"),
            created_at=run_data.get("created_at", "Unknown"),
            status=run_data.get("status", "Unknown"),
            conclusion=run_data.get("conclusion", "Unknown"),
            jobs=job_results,
        )

    def _is_benchmark_job(self, job_name: str) -> bool:
        """Check if job is a benchmark job."""
        return any(pattern in job_name for pattern in BENCHMARK_JOB_PATTERNS)

    def _process_jobs_parallel(
        self,
        owner: str,
        repo: str,
        run_id: int,
        jobs: List[dict],
        max_workers: int,
        artifact_cache: dict,
    ) -> List[JobResult]:
        """Process multiple jobs in parallel."""
        with concurrent.futures.ThreadPoolExecutor(max_workers=max_workers) as executor:
            future_to_job = {
                executor.submit(
                    self._process_single_job, owner, repo, run_id, job, artifact_cache
                ): job
                for job in jobs
            }

            results = []
            for future in concurrent.futures.as_completed(future_to_job):
                job = future_to_job[future]
                try:
                    result = future.result()
                    results.append(result)
                except Exception as e:
                    # Create error result for failed processing
                    results.append(
                        JobResult(
                            job_id=job["id"],
                            job_name=job["name"],
                            status=JobStatus.COMPLETED,
                            conclusion=JobConclusion.FAILURE,
                            error_message=f"Processing error: {str(e)}",
                        )
                    )

            # Sort by job name for consistent ordering
            results.sort(key=lambda x: x.job_name)
            return results

    def _process_single_job(
        self, owner: str, repo: str, run_id: int, job_data: dict, artifact_cache: dict
    ) -> JobResult:
        """Process a single job and extract all metrics."""
        job_id = job_data["id"]
        job_name = job_data["name"]
        status = JobStatus(job_data["status"])
        conclusion = None
        if job_data.get("conclusion"):
            try:
                conclusion = JobConclusion(job_data["conclusion"])
            except ValueError:
                conclusion = None

        # Initialize result
        result = JobResult(
            job_id=job_id,
            job_name=job_name,
            status=status,
            conclusion=conclusion,
        )

        # Only process completed jobs
        if status != JobStatus.COMPLETED:
            return result

        # If job failed, extract error information
        if conclusion == JobConclusion.FAILURE:
            failed_step, error_msg = self._extract_failure_info(job_data)
            result.failed_step = failed_step
            result.error_message = error_msg

        # Extract simulation metrics from logs (Step 10)
        try:
            logs = self.github.get_job_logs(owner, repo, job_id)
            result.simulation_metrics = self.log_parser.parse_simulation_metrics(
                logs, job_name
            )
            # If job failed and no error found yet, try to find in logs
            if conclusion == JobConclusion.FAILURE and not result.error_message:
                result.error_message = self.log_parser.find_error_in_logs(logs)
        except Exception as e:
            if not result.error_message:
                result.error_message = f"Failed to parse logs: {str(e)}"

        # Extract device perf metrics from artifacts (Step 19)
        try:
            result.device_perf_metrics = self._extract_device_perf_metrics(
                owner, repo, run_id, job_name, artifact_cache
            )
        except Exception as e:
            # Don't overwrite existing error messages
            if not result.error_message:
                result.error_message = f"Failed to parse device perf: {str(e)}"

        return result

    def _extract_failure_info(self, job_data: dict) -> tuple:
        """
        Extract failed step and error message from job data.

        Args:
            job_data: Job data from API

        Returns:
            Tuple of (failed_step_name, error_message)
        """
        steps = job_data.get("steps", [])
        for step in steps:
            if step.get("conclusion") == "failure":
                return step.get("name", "Unknown step"), None
        return None, None

    def _extract_device_perf_metrics(
        self, owner: str, repo: str, run_id: int, job_name: str, artifact_cache: dict
    ) -> Optional[DevicePerfMetrics]:
        """Extract device performance metrics from artifact."""
        # Find device-perf artifact by job name (handles workflow re-runs)
        artifact = self.github.find_device_perf_artifact_by_job_name(
            owner, repo, run_id, job_name, artifact_cache
        )
        if not artifact:
            return None

        # Download artifact to temp file
        with tempfile.NamedTemporaryFile(suffix=".zip", delete=False) as tmp_file:
            zip_path = tmp_file.name

        try:
            self.github.download_artifact(owner, repo, artifact["id"], zip_path)

            # Parse ALL CSV files from the artifact and combine metrics
            return self.csv_parser.parse_all_csvs_from_zip(zip_path)

        finally:
            # Cleanup temp file
            Path(zip_path).unlink(missing_ok=True)

        return None
