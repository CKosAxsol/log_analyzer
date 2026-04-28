"""Console reporting helpers."""

from __future__ import annotations

from pathlib import Path
from statistics import mean

from .models import ParsedSeries


def print_summary(parsed: ParsedSeries, columns: list[str], output_path: Path) -> None:
    """Print a compact summary for the processed file."""
    print(f"File: {parsed.csv_path}")
    print(f"Rows: {len(parsed.timestamps)}")
    print(f"Plot: {output_path}")
    print(f"Time range: {parsed.timestamps[0]} -> {parsed.timestamps[-1]}")
    for column in columns:
        values = parsed.series[column]
        print(
            f"  {column}: min={min(values):.2f} V, "
            f"max={max(values):.2f} V, mean={mean(values):.2f} V"
        )
