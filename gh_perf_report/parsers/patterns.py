"""Regex patterns for parsing benchmark logs."""

# Primary performance metric pattern
# Matches: "Sample per second: 12345.67" or "Samples per second: 12345.67"
SAMPLES_PER_SECOND_PATTERN = r"Sample[s]?\s+per\s+second:\s*(\d+\.?\d*)"

# Optional metric patterns
EXECUTION_TIME_PATTERN = r"Total\s+execution\s+time:\s*(\d+\.?\d*)"
TOTAL_SAMPLES_PATTERN = r"Total\s+samples:\s*(\d+)"
BATCH_SIZE_PATTERN = r"Batch\s+size:\s*(\d+)"

# Metadata patterns
METADATA_PATTERNS = {
    "model_type": r"Model\s+type:\s*([^\n]+)",
    "dataset_name": r"Dataset\s+name:\s*([^\n]+)",
    "data_format": r"Data\s+format:\s*([^\n]+)",
    "input_size": r"Input\s+size:\s*([^\n]+)",
}

# Error patterns for extracting error messages
ERROR_PATTERNS = [
    r"Error:\s*(.+?)(?:\n|$)",
    r"ERROR:\s*(.+?)(?:\n|$)",
    r"FAILED:\s*(.+?)(?:\n|$)",
    r"Exception:\s*(.+?)(?:\n|$)",
    r"Traceback.*?(?:Error|Exception):\s*(.+?)(?:\n|$)",
]

# All patterns collected
PERF_PATTERNS = {
    "samples_per_second": SAMPLES_PER_SECOND_PATTERN,
    "execution_time": EXECUTION_TIME_PATTERN,
    "total_samples": TOTAL_SAMPLES_PATTERN,
    "batch_size": BATCH_SIZE_PATTERN,
    "metadata": METADATA_PATTERNS,
}
