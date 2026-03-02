"""Parser for benchmark logs."""

import re
from typing import Optional, Dict

from .patterns import PERF_PATTERNS, ERROR_PATTERNS
from ..processors.models import SimulationMetrics
from ..utils.errors import ParseError


class LogParser:
    """Parser for Step 10 benchmark logs."""

    def __init__(self):
        """Initialize log parser with compiled patterns."""
        self.patterns = PERF_PATTERNS
        # Pre-compile patterns for efficiency
        self._samples_pattern = re.compile(
            self.patterns["samples_per_second"], re.MULTILINE | re.IGNORECASE
        )
        self._exec_time_pattern = re.compile(
            self.patterns["execution_time"], re.MULTILINE | re.IGNORECASE
        )
        self._total_samples_pattern = re.compile(
            self.patterns["total_samples"], re.MULTILINE | re.IGNORECASE
        )
        self._batch_size_pattern = re.compile(
            self.patterns["batch_size"], re.MULTILINE | re.IGNORECASE
        )
        self._error_patterns = [
            re.compile(p, re.MULTILINE | re.DOTALL) for p in ERROR_PATTERNS
        ]

    def parse_simulation_metrics(
        self, logs: str, job_name: str
    ) -> Optional[SimulationMetrics]:
        """
        Extract simulation metrics from job logs.

        Args:
            logs: Raw job log content
            job_name: Name of the job

        Returns:
            SimulationMetrics or None if samples_per_second not found
        """
        try:
            # Extract model name from job name
            model_name = self._extract_model_name(job_name)

            # Primary metric: samples per second
            samples_per_sec = self._extract_samples_per_second(logs)
            if samples_per_sec is None:
                return None

            # Optional metrics
            exec_time = self._extract_execution_time(logs)
            total_samples = self._extract_total_samples(logs)
            batch_size = self._extract_batch_size(logs)
            metadata = self._extract_metadata(logs)

            return SimulationMetrics(
                model_name=model_name,
                samples_per_second=samples_per_sec,
                total_execution_time=exec_time,
                total_samples=total_samples,
                batch_size=batch_size,
                metadata=metadata,
            )
        except Exception as e:
            raise ParseError(f"Failed to parse simulation metrics: {e}")

    def _extract_model_name(self, job_name: str) -> str:
        """Extract model name from job name."""
        # Pattern: "run-n150-perf-benchmarks / tt-xla-model-name (n150-perf, 12, 128) benchmark"
        # We want to extract "model-name" part

        # Old format: "... / tt-xla-model-name ..."
        match = re.search(
            r"tt-(?:xla|forge)-([a-zA-Z0-9_-]+)", job_name, re.IGNORECASE
        )
        if match:
            return match.group(1)

        # New tt-xla format: "run-n150-perf-benchmarks / perf model_name (n150-perf)"
        match = re.search(r"/\s*perf\s+([a-zA-Z0-9_][a-zA-Z0-9_.-]*)", job_name, re.IGNORECASE)
        if match:
            return match.group(1)

        # Fallback: return the whole job name
        return job_name

    def _extract_samples_per_second(self, logs: str) -> Optional[float]:
        """Extract samples per second from logs."""
        match = self._samples_pattern.search(logs)
        if match:
            return float(match.group(1))
        return None

    def _extract_execution_time(self, logs: str) -> Optional[float]:
        """Extract total execution time."""
        match = self._exec_time_pattern.search(logs)
        if match:
            return float(match.group(1))
        return None

    def _extract_total_samples(self, logs: str) -> Optional[int]:
        """Extract total samples processed."""
        match = self._total_samples_pattern.search(logs)
        if match:
            return int(match.group(1))
        return None

    def _extract_batch_size(self, logs: str) -> Optional[int]:
        """Extract batch size."""
        match = self._batch_size_pattern.search(logs)
        if match:
            return int(match.group(1))
        return None

    def _extract_metadata(self, logs: str) -> Dict[str, str]:
        """Extract additional metadata from logs."""
        metadata = {}
        for key, pattern in self.patterns.get("metadata", {}).items():
            match = re.search(pattern, logs, re.MULTILINE | re.IGNORECASE)
            if match:
                metadata[key] = match.group(1).strip()
        return metadata

    def find_error_in_logs(self, logs: str) -> Optional[str]:
        """
        Extract error message from logs.

        Args:
            logs: Raw job log content

        Returns:
            Error message or None
        """
        for pattern in self._error_patterns:
            match = pattern.search(logs)
            if match:
                error_msg = match.group(1).strip()
                # Limit error message length
                max_len = 500
                return error_msg[:max_len] + "..." if len(error_msg) > max_len else error_msg
        return None
