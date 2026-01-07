"""Custom exceptions for gh-perf-report."""


class GHPerfReportError(Exception):
    """Base exception for gh-perf-report."""

    pass


class GitHubAPIError(GHPerfReportError):
    """GitHub API related errors."""

    pass


class ArtifactNotFoundError(GitHubAPIError):
    """Artifact not found or inaccessible."""

    pass


class ParseError(GHPerfReportError):
    """Error parsing logs or CSV files."""

    pass


class ProcessingError(GHPerfReportError):
    """Error processing workflow or job data."""

    pass


class ValidationError(GHPerfReportError):
    """Input validation error."""

    pass
