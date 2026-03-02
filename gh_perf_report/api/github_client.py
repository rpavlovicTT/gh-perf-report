"""GitHub API client using gh CLI."""

import json
import subprocess
from typing import Dict, List, Optional

from .rate_limiter import RateLimiter
from ..utils.errors import GitHubAPIError, ArtifactNotFoundError
from ..config import ARTIFACT_PREFIX_DEVICE_PERF


class GitHubClient:
    """Wrapper around GitHub CLI for API interactions."""

    def __init__(self, rate_limiter: Optional[RateLimiter] = None):
        """
        Initialize GitHub client.

        Args:
            rate_limiter: Optional rate limiter instance
        """
        self.rate_limiter = rate_limiter or RateLimiter()
        self._verify_gh_cli()

    def _verify_gh_cli(self) -> None:
        """Verify gh CLI is installed and authenticated."""
        try:
            result = subprocess.run(
                ["gh", "auth", "status"],
                capture_output=True,
                text=True,
                check=False,
            )
            if result.returncode != 0:
                raise GitHubAPIError(
                    "GitHub CLI not authenticated. Run: gh auth login"
                )
        except FileNotFoundError:
            raise GitHubAPIError(
                "GitHub CLI not found. Install from: https://cli.github.com/"
            )

    def _gh_api_call(self, endpoint: str, method: str = "GET") -> Dict:
        """
        Make GitHub API call using gh CLI.

        Args:
            endpoint: API endpoint path
            method: HTTP method (default: GET)

        Returns:
            Parsed JSON response
        """
        self.rate_limiter.wait_if_needed()

        cmd = ["gh", "api", endpoint]
        if method != "GET":
            cmd.extend(["--method", method])

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            return json.loads(result.stdout) if result.stdout else {}
        except subprocess.CalledProcessError as e:
            raise GitHubAPIError(f"GitHub API call failed: {e.stderr}")
        except json.JSONDecodeError as e:
            raise GitHubAPIError(f"Invalid JSON response: {e}")

    def get_workflow_run(self, owner: str, repo: str, run_id: int) -> Dict:
        """
        Get workflow run details.

        Args:
            owner: Repository owner
            repo: Repository name
            run_id: Workflow run ID

        Returns:
            Workflow run data
        """
        endpoint = f"repos/{owner}/{repo}/actions/runs/{run_id}"
        return self._gh_api_call(endpoint)

    def get_workflow_jobs(self, owner: str, repo: str, run_id: int) -> List[Dict]:
        """
        Get all jobs for a workflow run (with pagination).

        Args:
            owner: Repository owner
            repo: Repository name
            run_id: Workflow run ID

        Returns:
            List of job data
        """
        self.rate_limiter.wait_if_needed()

        endpoint = f"repos/{owner}/{repo}/actions/runs/{run_id}/jobs?per_page=100"
        cmd = ["gh", "api", endpoint, "--paginate", "--jq", ".jobs"]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            jobs = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    jobs.extend(json.loads(line))
            return jobs
        except subprocess.CalledProcessError as e:
            raise GitHubAPIError(f"GitHub API call failed: {e.stderr}")
        except json.JSONDecodeError as e:
            raise GitHubAPIError(f"Invalid JSON response: {e}")

    def get_job_logs(self, owner: str, repo: str, job_id: int) -> str:
        """
        Get logs for a specific job.

        Args:
            owner: Repository owner
            repo: Repository name
            job_id: Job ID

        Returns:
            Job logs as string
        """
        self.rate_limiter.wait_if_needed()

        endpoint = f"repos/{owner}/{repo}/actions/jobs/{job_id}/logs"
        cmd = ["gh", "api", endpoint]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            return result.stdout
        except subprocess.CalledProcessError as e:
            raise GitHubAPIError(f"Failed to fetch logs: {e.stderr}")

    def list_artifacts(self, owner: str, repo: str, run_id: int) -> List[Dict]:
        """
        List all artifacts for a workflow run (with pagination).

        Args:
            owner: Repository owner
            repo: Repository name
            run_id: Workflow run ID

        Returns:
            List of artifact data
        """
        self.rate_limiter.wait_if_needed()

        endpoint = f"repos/{owner}/{repo}/actions/runs/{run_id}/artifacts"
        cmd = ["gh", "api", endpoint, "--paginate", "--jq", ".artifacts"]

        try:
            result = subprocess.run(
                cmd,
                capture_output=True,
                text=True,
                check=True,
            )
            # --paginate with --jq returns one JSON array per page, concatenated
            # We need to parse each line as a separate array and combine them
            artifacts = []
            for line in result.stdout.strip().split("\n"):
                if line:
                    page_artifacts = json.loads(line)
                    artifacts.extend(page_artifacts)
            return artifacts
        except subprocess.CalledProcessError as e:
            raise GitHubAPIError(f"Failed to list artifacts: {e.stderr}")
        except json.JSONDecodeError as e:
            raise GitHubAPIError(f"Invalid JSON response: {e}")

    def download_artifact(
        self, owner: str, repo: str, artifact_id: int, output_path: str
    ) -> str:
        """
        Download artifact ZIP file.

        Args:
            owner: Repository owner
            repo: Repository name
            artifact_id: Artifact ID
            output_path: Path to save the artifact

        Returns:
            Output path
        """
        self.rate_limiter.wait_if_needed()

        endpoint = f"repos/{owner}/{repo}/actions/artifacts/{artifact_id}/zip"
        cmd = ["gh", "api", endpoint]

        try:
            # gh api returns binary data, redirect to file
            with open(output_path, "wb") as f:
                result = subprocess.run(cmd, check=True, stdout=f, stderr=subprocess.PIPE)
            return output_path
        except subprocess.CalledProcessError as e:
            raise ArtifactNotFoundError(f"Failed to download artifact: {e.stderr.decode() if e.stderr else 'Unknown error'}")

    def find_device_perf_artifact(
        self, owner: str, repo: str, run_id: int, job_id: int
    ) -> Optional[Dict]:
        """
        Find device-perf artifact for a specific job.

        Args:
            owner: Repository owner
            repo: Repository name
            run_id: Workflow run ID
            job_id: Job ID

        Returns:
            Artifact data or None if not found
        """
        artifacts = self.list_artifacts(owner, repo, run_id)
        pattern = f"{ARTIFACT_PREFIX_DEVICE_PERF}{job_id}"

        for artifact in artifacts:
            if pattern in artifact.get("name", ""):
                return artifact
        return None

    def find_device_perf_artifact_by_job_name(
        self, owner: str, repo: str, run_id: int, job_name: str, artifacts_cache: Optional[dict] = None
    ) -> Optional[Dict]:
        """
        Find device-perf artifact by matching job name.

        This handles cases where workflow was re-run and job IDs don't match
        between the current attempt and the attempt that uploaded artifacts.

        Args:
            owner: Repository owner
            repo: Repository name
            run_id: Workflow run ID
            job_name: Job name to match
            artifacts_cache: Optional pre-built cache of job_name -> artifact

        Returns:
            Artifact data or None if not found
        """
        if artifacts_cache is not None:
            # Use pre-built cache
            normalized_name = self._normalize_job_name(job_name)
            return artifacts_cache.get(normalized_name)

        # Fall back to building cache on demand (less efficient)
        cache = self.build_artifact_cache(owner, repo, run_id)
        normalized_name = self._normalize_job_name(job_name)
        return cache.get(normalized_name)

    def build_artifact_cache(self, owner: str, repo: str, run_id: int) -> dict:
        """
        Build a cache mapping normalized job names to device-perf artifacts.

        This is needed because workflow re-runs create new job IDs but artifacts
        are associated with the original job IDs.

        Args:
            owner: Repository owner
            repo: Repository name
            run_id: Workflow run ID

        Returns:
            Dict mapping normalized job name -> artifact data
        """
        import re

        artifacts = self.list_artifacts(owner, repo, run_id)
        cache = {}

        for artifact in artifacts:
            artifact_name = artifact.get("name", "")
            if not artifact_name.startswith(ARTIFACT_PREFIX_DEVICE_PERF):
                continue

            # Extract job ID from artifact name (device-perf-{job_id})
            match = re.match(rf"{ARTIFACT_PREFIX_DEVICE_PERF}(\d+)", artifact_name)
            if not match:
                continue

            artifact_job_id = int(match.group(1))

            # Look up the job to get its name
            try:
                job_data = self.get_job(owner, repo, artifact_job_id)
                if job_data:
                    job_name = job_data.get("name", "")
                    normalized = self._normalize_job_name(job_name)
                    cache[normalized] = artifact
            except Exception:
                # Skip artifacts we can't resolve
                continue

        return cache

    def get_job(self, owner: str, repo: str, job_id: int) -> Optional[Dict]:
        """
        Get job details by ID.

        Args:
            owner: Repository owner
            repo: Repository name
            job_id: Job ID

        Returns:
            Job data or None if not found
        """
        self.rate_limiter.wait_if_needed()

        endpoint = f"repos/{owner}/{repo}/actions/jobs/{job_id}"
        try:
            return self._gh_api_call(endpoint)
        except GitHubAPIError:
            return None

    def _normalize_job_name(self, job_name: str) -> str:
        """
        Normalize job name for matching.

        Extracts the model identifier (e.g., "tt-xla-efficientnet") from
        the full job name for reliable matching across workflow attempts.
        """
        import re
        # Old format: "... / tt-xla-model-name ..."
        match = re.search(r"(tt-(?:xla|forge)-[a-zA-Z0-9_-]+)", job_name, re.IGNORECASE)
        if match:
            return match.group(1).lower()
        # New tt-xla format: "run-n150-perf-benchmarks / perf model_name (n150-perf)"
        match = re.search(r"/\s*perf\s+([a-zA-Z0-9_][a-zA-Z0-9_.-]*)", job_name, re.IGNORECASE)
        if match:
            return match.group(1).lower()
        return job_name.lower()
