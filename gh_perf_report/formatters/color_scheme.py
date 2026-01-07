"""Color scheme definitions for output formatting."""


class ColorScheme:
    """Color definitions for console output."""

    # Status colors
    SUCCESS = "green"
    FAILURE = "red"
    SKIPPED = "dim"
    PENDING = "yellow"
    NEUTRAL = "dim"

    # Metric colors
    IMPROVEMENT = "green"
    REGRESSION = "red"
    UNCHANGED = "dim"

    # Header colors
    HEADER = "bold cyan"
    SUBHEADER = "cyan"

    # Table colors
    TABLE_HEADER = "bold magenta"
    JOB_NAME = "cyan"
    ERROR = "red"

    # Result colors
    RESULT_IMPROVEMENT = "green bold"
    RESULT_REGRESSION = "red bold"
    RESULT_NEUTRAL = "dim"
    RESULT_NEW = "cyan"
    RESULT_REMOVED = "yellow"
