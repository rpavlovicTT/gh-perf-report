# GitHub CI Performance Report Parser

A CLI tool for parsing and comparing GitHub Actions performance metrics from tt-forge and tt-xla repositories.

## Features

- **Report Mode**: Analyze single workflow run with simulation and device performance metrics
- **Compare Mode**: Compare two runs with delta calculations and regression detection
- **Rich Output**: Color-coded console tables with performance metrics

## Installation

```bash
pip install -e .
```

## Prerequisites

- Python 3.8+
- GitHub CLI (`gh`) installed and authenticated

## Usage

### Generate Report for Single Run

```bash
gh-perf-report report <run_id> --repo <tt-xla|tt-forge>
```

Example:
```bash
gh-perf-report report 20770713621 --repo tt-forge
```

### Compare Two Runs

```bash
gh-perf-report compare <baseline_run_id> <current_run_id> --baseline-repo <tt-xla|tt-forge>
```

Example:
```bash
gh-perf-report compare 20770713621 20780226487 --baseline-repo tt-xla
```

### List Jobs (Quick View)

```bash
gh-perf-report list-jobs <run_id> --repo <tt-xla|tt-forge>
```

## Options

- `--owner`: Repository owner (default: tenstorrent)
- `--no-cache`: Disable caching
- `--workers`: Number of parallel workers (default: 5)
- `--current-repo`: Current repository for comparison (defaults to baseline-repo)

## What It Does

1. **Extracts Simulation Metrics**: Parses "Sample per second" from Step 10 ("Run Perf Benchmark") logs
2. **Extracts Device Performance**: Downloads and parses device-perf CSV artifacts, calculates sum of filtered operation durations
3. **Reports Failures**: Identifies failed tests and reports which step failed with error messages
4. **Compares Runs**: Calculates deltas and percentage changes, highlights regressions and improvements

## Output

### Report Mode
Shows table with:
- Job name
- Status (success/failure)
- Samples per second
- Device perf (milliseconds)
- Error messages for failed jobs

### Compare Mode
Shows table with:
- Job name
- Status changes
- Samples/sec delta and percentage
- Device perf delta and percentage
- Result (regression/improvement/neutral)

## License

MIT
