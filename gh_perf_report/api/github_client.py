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
        Get all jobs for a workflow run.

        Args:
            owner: Repository owner
            repo: Repository name
            run_id: Workflow run ID

        Returns:
            List of job data
        """
        endpoint = f"repos/{owner}/{repo}/actions/runs/{run_id}/jobs?per_page=100"
        response = self._gh_api_call(endpoint)
        return response.get("jobs", [])

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
