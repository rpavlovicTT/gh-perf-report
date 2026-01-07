"""Data models for performance reports."""

from dataclasses import dataclass, field
from typing import Optional, List, Dict
from enum import Enum


class JobStatus(Enum):
    """Job execution status."""

    COMPLETED = "completed"
    IN_PROGRESS = "in_progress"
    QUEUED = "queued"


class JobConclusion(Enum):
    """Job conclusion status."""

    SUCCESS = "success"
    FAILURE = "failure"
    SKIPPED = "skipped"
    CANCELLED = "cancelled"
    NEUTRAL = "neutral"


@dataclass
class SimulationMetrics:
    """Metrics from Step 10: Run Perf Benchmark."""

    model_name: str
    samples_per_second: float
    total_execution_time: Optional[float] = None
    total_samples: Optional[int] = None
    batch_size: Optional[int] = None
    metadata: Dict[str, str] = field(default_factory=dict)


@dataclass
class StagePerfMetrics:
    """Metrics for a single stage (one CSV file)."""

    stage_name: str
    duration_ns: float
    op_count: int

    @property
    def duration_ms(self) -> float:
        """Duration in milliseconds."""
        return self.duration_ns / 1_000_000


@dataclass
class DevicePerfMetrics:
    """Metrics from Device Perf CSV artifacts."""

    total_op_duration_ns: float
    filtered_op_count: int
    avg_op_duration_ns: float
    stages: List["StagePerfMetrics"] = field(default_factory=list)

    @property
    def total_op_duration_ms(self) -> float:
        """Total op duration in milliseconds."""
        return self.total_op_duration_ns / 1_000_000

    @property
    def num_stages(self) -> int:
        """Number of non-empty stages."""
        return len(self.stages)


@dataclass
class JobResult:
    """Complete job performance data."""

    job_id: int
    job_name: str
    status: JobStatus
    conclusion: Optional[JobConclusion] = None
    simulation_metrics: Optional[SimulationMetrics] = None
    device_perf_metrics: Optional[DevicePerfMetrics] = None
    error_message: Optional[str] = None
    failed_step: Optional[str] = None


@dataclass
class WorkflowReport:
    """Complete workflow run report."""

    run_id: int
    repo: str
    workflow_name: str
    branch: str
    created_at: str
    status: str
    conclusion: str
    jobs: List[JobResult] = field(default_factory=list)

    @property
    def success_count(self) -> int:
        """Count of successful jobs."""
        return sum(1 for j in self.jobs if j.conclusion == JobConclusion.SUCCESS)

    @property
    def failure_count(self) -> int:
        """Count of failed jobs."""
        return sum(1 for j in self.jobs if j.conclusion == JobConclusion.FAILURE)

    @property
    def skipped_count(self) -> int:
        """Count of skipped jobs."""
        return sum(1 for j in self.jobs if j.conclusion == JobConclusion.SKIPPED)


@dataclass
class ComparisonResult:
    """Comparison between two job results."""

    job_name: str
    baseline: Optional[JobResult] = None
    current: Optional[JobResult] = None
    samples_per_sec_delta: Optional[float] = None
    samples_per_sec_percent_change: Optional[float] = None
    device_perf_delta_ns: Optional[float] = None
    device_perf_percent_change: Optional[float] = None
    status_changed: bool = False
    is_regression: bool = False
    is_improvement: bool = False

    @property
    def device_perf_delta_ms(self) -> Optional[float]:
        """Device perf delta in milliseconds."""
        if self.device_perf_delta_ns is not None:
            return self.device_perf_delta_ns / 1_000_000
        return None
