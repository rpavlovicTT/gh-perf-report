"""Parser for device performance CSV files."""

import csv
import io
import zipfile
from pathlib import Path
from typing import Optional

from ..processors.models import DevicePerfMetrics, StagePerfMetrics
from ..utils.errors import ParseError
from ..config import CSV_REQUIRED_COLUMNS, CSV_DURATION_COLUMN


class CSVParser:
    """Parser for device performance CSV files."""

    def parse_device_perf_csv(self, csv_content: str) -> DevicePerfMetrics:
        """
        Parse device performance CSV and calculate metrics.

        Filters out rows where:
        - CONST_EVAL_OP == True
        - INPUT_LAYOUT_CONVERSION_OP == True

        Calculates:
        - Sum of DEVICE KERNEL DURATION [ns]
        - Count of filtered operations
        - Average operation duration

        Args:
            csv_content: CSV file content as string

        Returns:
            DevicePerfMetrics with calculated values
        """
        try:
            reader = csv.DictReader(io.StringIO(csv_content))

            # Verify required columns exist
            fieldnames = reader.fieldnames or []
            missing_cols = [
                col for col in CSV_REQUIRED_COLUMNS if col not in fieldnames
            ]
            if missing_cols:
                raise ParseError(f"Missing required columns: {missing_cols}")

            total_duration = 0.0
            filtered_count = 0

            for row in reader:
                # Apply filters - skip rows where either flag is true
                if self._should_filter_row(row):
                    continue

                # Extract duration
                duration = self._parse_duration(row.get(CSV_DURATION_COLUMN, "0"))
                if duration is None:
                    continue

                total_duration += duration
                filtered_count += 1

            avg_duration = total_duration / filtered_count if filtered_count > 0 else 0.0

            return DevicePerfMetrics(
                total_op_duration_ns=total_duration,
                filtered_op_count=filtered_count,
                avg_op_duration_ns=avg_duration,
            )

        except ParseError:
            raise
        except Exception as e:
            raise ParseError(f"Failed to parse device perf CSV: {e}")

    def _should_filter_row(self, row: dict) -> bool:
        """
        Check if row should be filtered based on flags.

        Args:
            row: CSV row as dictionary

        Returns:
            True if row should be excluded
        """
        const_eval = self._parse_bool(row.get("CONST_EVAL_OP", "false"))
        layout_conversion = self._parse_bool(
            row.get("INPUT_LAYOUT_CONVERSION_OP", "false")
        )
        # Exclude if either flag is true
        return const_eval or layout_conversion

    def _parse_duration(self, value: str) -> Optional[float]:
        """Parse duration value from CSV."""
        try:
            return float(value.strip())
        except (ValueError, AttributeError):
            return None

    def _parse_bool(self, value: str) -> bool:
        """Parse boolean value from CSV."""
        if not value:
            return False
        value_lower = str(value).strip().lower()
        return value_lower in ("true", "1", "yes", "t")

    def extract_csvs_from_artifact_zip(self, zip_path: str) -> list:
        """
        Extract ALL CSV files from artifact ZIP.

        Args:
            zip_path: Path to the ZIP file

        Returns:
            List of tuples (filename, content)
        """
        try:
            with zipfile.ZipFile(zip_path, "r") as zip_ref:
                # Find CSV files in ZIP
                csv_files = [f for f in zip_ref.namelist() if f.endswith(".csv")]
                if not csv_files:
                    raise ParseError("No CSV file found in artifact ZIP")

                # Sort by filename for consistent ordering
                csv_files.sort()

                # Read ALL CSV files with their names
                csv_data = []
                for csv_file_name in csv_files:
                    with zip_ref.open(csv_file_name) as csv_file:
                        content = csv_file.read().decode("utf-8")
                        csv_data.append((csv_file_name, content))

                return csv_data

        except zipfile.BadZipFile as e:
            raise ParseError(f"Invalid ZIP file: {e}")
        except Exception as e:
            raise ParseError(f"Failed to extract CSV from ZIP: {e}")

    def parse_all_csvs_from_zip(self, zip_path: str) -> DevicePerfMetrics:
        """
        Parse ALL CSV files from artifact ZIP and combine metrics.

        Skips empty CSV files and tracks per-stage metrics.

        Args:
            zip_path: Path to the ZIP file

        Returns:
            Combined DevicePerfMetrics from all CSV files with per-stage breakdown
        """
        csv_data = self.extract_csvs_from_artifact_zip(zip_path)

        total_duration = 0.0
        total_count = 0
        stages = []
        stage_num = 1

        for filename, csv_content in csv_data:
            try:
                metrics = self.parse_device_perf_csv(csv_content)

                # Skip empty CSVs (no valid ops after filtering)
                if metrics.filtered_op_count == 0:
                    continue

                # Track per-stage metrics
                stage = StagePerfMetrics(
                    stage_name=f"Stage {stage_num}",
                    duration_ns=metrics.total_op_duration_ns,
                    op_count=metrics.filtered_op_count,
                )
                stages.append(stage)
                stage_num += 1

                total_duration += metrics.total_op_duration_ns
                total_count += metrics.filtered_op_count

            except ParseError:
                # Skip CSVs that don't have required columns
                continue

        if total_count == 0:
            raise ParseError("No valid device perf data found in any CSV file")

        avg_duration = total_duration / total_count

        return DevicePerfMetrics(
            total_op_duration_ns=total_duration,
            filtered_op_count=total_count,
            avg_op_duration_ns=avg_duration,
            stages=stages,
        )
