"""CLI interface for gh-perf-report."""

import click
from rich.console import Console

from .api.github_client import GitHubClient
from .processors.report_processor import ReportProcessor
from .processors.compare_processor import CompareProcessor
from .formatters.table_formatter import TableFormatter
from .utils.errors import GitHubAPIError, ProcessingError
from .config import DEFAULT_OWNER, SUPPORTED_REPOS, DEFAULT_MAX_WORKERS


@click.group()
@click.version_option(version="0.1.0")
def cli():
    """GitHub CI Performance Report Parser for tt-forge and tt-xla."""
    pass


@cli.command()
@click.argument("run_id", type=int)
@click.option(
    "--repo",
    "-r",
    type=click.Choice(SUPPORTED_REPOS, case_sensitive=False),
    required=True,
    help="Repository name",
)
@click.option(
    "--owner",
    "-o",
    default=DEFAULT_OWNER,
    help=f"Repository owner (default: {DEFAULT_OWNER})",
)
@click.option(
    "--workers",
    "-w",
    type=int,
    default=DEFAULT_MAX_WORKERS,
    help=f"Number of parallel workers (default: {DEFAULT_MAX_WORKERS})",
)
def report(run_id: int, repo: str, owner: str, workers: int):
    """
    Generate performance report for a single workflow run.

    Example:
        gh-perf-report report 12345 --repo tt-xla
    """
    console = Console()

    try:
        # Initialize components
        github_client = GitHubClient()
        processor = ReportProcessor(github_client)
        formatter = TableFormatter(console)

        # Process workflow run
        console.print(f"[cyan]Fetching workflow run {run_id} from {owner}/{repo}...[/cyan]")
        workflow_report = processor.process_workflow_run(owner, repo, run_id, workers)

        # Display report
        formatter.print_workflow_report(workflow_report)

    except GitHubAPIError as e:
        console.print(f"[red bold]GitHub API Error:[/red bold] {e}", style="red")
        raise click.Abort()
    except ProcessingError as e:
        console.print(f"[red bold]Processing Error:[/red bold] {e}", style="red")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red bold]Unexpected Error:[/red bold] {e}", style="red")
        raise click.Abort()


@cli.command()
@click.argument("baseline_run_id", type=int)
@click.argument("current_run_id", type=int)
@click.option(
    "--baseline-repo",
    "-br",
    type=click.Choice(SUPPORTED_REPOS, case_sensitive=False),
    required=True,
    help="Baseline repository name",
)
@click.option(
    "--current-repo",
    "-cr",
    type=click.Choice(SUPPORTED_REPOS, case_sensitive=False),
    help="Current repository name (defaults to baseline-repo)",
)
@click.option(
    "--owner",
    "-o",
    default=DEFAULT_OWNER,
    help=f"Repository owner (default: {DEFAULT_OWNER})",
)
@click.option(
    "--workers",
    "-w",
    type=int,
    default=DEFAULT_MAX_WORKERS,
    help=f"Number of parallel workers (default: {DEFAULT_MAX_WORKERS})",
)
def compare(
    baseline_run_id: int,
    current_run_id: int,
    baseline_repo: str,
    current_repo: str,
    owner: str,
    workers: int,
):
    """
    Compare performance between two workflow runs.

    Example:
        gh-perf-report compare 12345 12346 --baseline-repo tt-xla
        gh-perf-report compare 12345 67890 --baseline-repo tt-xla --current-repo tt-forge
    """
    console = Console()

    # Default current_repo to baseline_repo
    if not current_repo:
        current_repo = baseline_repo

    try:
        # Initialize components
        github_client = GitHubClient()
        report_processor = ReportProcessor(github_client)
        compare_processor = CompareProcessor()
        formatter = TableFormatter(console)

        # Process baseline run
        console.print(
            f"[cyan]Fetching baseline run {baseline_run_id} from {owner}/{baseline_repo}...[/cyan]"
        )
        baseline_report = report_processor.process_workflow_run(
            owner, baseline_repo, baseline_run_id, workers
        )

        # Process current run
        console.print(
            f"[cyan]Fetching current run {current_run_id} from {owner}/{current_repo}...[/cyan]"
        )
        current_report = report_processor.process_workflow_run(
            owner, current_repo, current_run_id, workers
        )

        # Compare reports
        console.print("[cyan]Comparing reports...[/cyan]")
        comparisons = compare_processor.compare_reports(baseline_report, current_report)

        # Display comparison
        formatter.print_comparison_report(comparisons, baseline_report, current_report)

    except GitHubAPIError as e:
        console.print(f"[red bold]GitHub API Error:[/red bold] {e}", style="red")
        raise click.Abort()
    except ProcessingError as e:
        console.print(f"[red bold]Processing Error:[/red bold] {e}", style="red")
        raise click.Abort()
    except Exception as e:
        console.print(f"[red bold]Unexpected Error:[/red bold] {e}", style="red")
        raise click.Abort()


@cli.command("list-jobs")
@click.argument("run_id", type=int)
@click.option(
    "--repo",
    "-r",
    type=click.Choice(SUPPORTED_REPOS, case_sensitive=False),
    required=True,
    help="Repository name",
)
@click.option(
    "--owner",
    "-o",
    default=DEFAULT_OWNER,
    help=f"Repository owner (default: {DEFAULT_OWNER})",
)
def list_jobs(run_id: int, repo: str, owner: str):
    """
    List all jobs in a workflow run (quick view).

    Example:
        gh-perf-report list-jobs 12345 --repo tt-xla
    """
    console = Console()

    try:
        github_client = GitHubClient()
        jobs = github_client.get_workflow_jobs(owner, repo, run_id)

        console.print(f"\n[bold cyan]Jobs for run {run_id}[/bold cyan]")
        console.print(f"Repository: {owner}/{repo}\n")

        for job in jobs:
            status = job.get("conclusion", job.get("status", "unknown"))
            job_id = job["id"]
            name = job["name"]

            # Color based on status
            if status == "success":
                status_display = f"[green]{status}[/green]"
            elif status == "failure":
                status_display = f"[red]{status}[/red]"
            elif status == "skipped":
                status_display = f"[dim]{status}[/dim]"
            else:
                status_display = f"[yellow]{status}[/yellow]"

            console.print(f"  {job_id:12} {name[:60]:60} {status_display}")

        console.print(f"\n[dim]Total jobs: {len(jobs)}[/dim]")

    except GitHubAPIError as e:
        console.print(f"[red bold]Error:[/red bold] {e}", style="red")
        raise click.Abort()


if __name__ == "__main__":
    cli()
