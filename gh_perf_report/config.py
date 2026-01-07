"""Configuration constants."""

# Repository configuration
DEFAULT_OWNER = "tenstorrent"
SUPPORTED_REPOS = ["tt-forge", "tt-xla"]

# Benchmark job patterns - jobs that contain these patterns are benchmark jobs
BENCHMARK_JOB_PATTERNS = ["tt-xla-", "tt-forge-"]

# Step names
STEP_NAME_PERF_BENCHMARK = "Run Perf Benchmark"
STEP_NAME_DEVICE_PERF = "Run Device Perf"

# Artifact patterns
ARTIFACT_PREFIX_DEVICE_PERF = "device-perf-"

# Performance thresholds (as decimals)
REGRESSION_THRESHOLD = -0.05  # 5% decrease is regression
IMPROVEMENT_THRESHOLD = 0.05  # 5% increase is improvement

# API configuration
DEFAULT_API_RATE_LIMIT = 10  # calls per second
DEFAULT_MAX_WORKERS = 5

# Cache configuration
DEFAULT_CACHE_TTL_HOURS = 24
CACHE_DIR_NAME = ".gh-perf-report"

# CSV parsing configuration
CSV_FILTER_COLUMNS = ["CONST_EVAL_OP", "INPUT_LAYOUT_CONVERSION_OP"]
CSV_DURATION_COLUMN = "DEVICE KERNEL DURATION [ns]"
CSV_REQUIRED_COLUMNS = [
    "OP CODE",
    "DEVICE KERNEL DURATION [ns]",
    "OP TO OP LATENCY [ns]",
    "CONST_EVAL_OP",
    "INPUT_LAYOUT_CONVERSION_OP",
]
