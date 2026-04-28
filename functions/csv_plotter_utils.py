"""Shared helpers for the interactive CSV plotter.

The GUI keeps the application state, while this module contains small,
testable conversions that do not depend on Tkinter widgets.
"""

from __future__ import annotations

from datetime import datetime
from typing import TypeAlias


XValue: TypeAlias = datetime | int | float | str


def normalize_header(header: list[str]) -> list[str]:
    """Strip header cells and fill empty names with stable placeholders."""
    normalized: list[str] = []
    for index, value in enumerate(header, start=1):
        stripped = value.strip()
        normalized.append(stripped if stripped else f"column_{index}")
    return normalized


def get_row_value(row: list[str], index: int) -> str:
    """Safely return a row value or an empty string when the field is missing."""
    if index >= len(row):
        return ""
    return row[index]


def is_float_row_value(row: list[str], index: int) -> bool:
    """Check whether the given cell contains a float-compatible value."""
    value = get_row_value(row, index).strip()
    if not value:
        return False
    try:
        float(value)
    except ValueError:
        return False
    return True


def detect_timestamp_column(header: list[str], sample_rows: list[list[str]]) -> str | None:
    """Pick a likely timestamp column for plain CSV files."""
    preferred_names = {"timestamp", "time", "datetime", "date", "datum", "zeit"}
    for index, column_name in enumerate(header):
        normalized_name = column_name.strip().lower()
        if normalized_name in preferred_names and column_looks_like_timestamp(sample_rows, index):
            return column_name

    for index, column_name in enumerate(header):
        if column_looks_like_timestamp(sample_rows, index):
            return column_name
    return None


def column_looks_like_timestamp(rows: list[list[str]], index: int) -> bool:
    """Return True when at least one non-empty sample cell parses as a timestamp."""
    for row in rows[:50]:
        value = get_row_value(row, index).strip()
        if not value:
            continue
        if try_parse_timestamp(value) is not None:
            return True
    return False


def try_parse_timestamp(value: str) -> datetime | None:
    """Parse common timestamp formats used by generic CSV files."""
    for fmt in (
        "%Y-%m-%d %H:%M:%S",
        "%Y-%m-%d %H:%M",
        "%Y-%m-%dT%H:%M:%S",
        "%Y-%m-%dT%H:%M",
        "%d.%m.%Y %H:%M:%S",
        "%d.%m.%Y %H:%M",
        "%d/%m/%Y %H:%M:%S",
        "%d/%m/%Y %H:%M",
        "%m/%d/%Y %H:%M:%S",
        "%m/%d/%Y %H:%M",
        "%Y-%m-%d",
        "%d.%m.%Y",
        "%d/%m/%Y",
        "%m/%d/%Y",
    ):
        try:
            return datetime.strptime(value, fmt)
        except ValueError:
            continue
    try:
        return datetime.fromisoformat(value)
    except ValueError:
        return None


def convert_x_values(raw_x_values: list[str], x_axis_column: str, row_index_label: str) -> tuple[list[XValue], str, bool]:
    """Convert raw X values to row numbers, datetimes, floats, or strings."""
    if x_axis_column == row_index_label:
        return [int(value) for value in raw_x_values], row_index_label, False

    timestamp_values: list[datetime] = []
    if all((parsed := try_parse_timestamp(value)) is not None for value in raw_x_values):
        for value in raw_x_values:
            parsed = try_parse_timestamp(value)
            if parsed is None:
                break
            timestamp_values.append(parsed)
        if len(timestamp_values) == len(raw_x_values):
            return timestamp_values, x_axis_column, True

    try:
        return [float(value) for value in raw_x_values], x_axis_column, False
    except ValueError:
        return raw_x_values, x_axis_column, False


def format_x_value(x_value: XValue) -> str:
    """Return a readable X value for CSV export, tooltips, and the status bar."""
    if isinstance(x_value, datetime):
        return x_value.strftime("%Y-%m-%d %H:%M:%S")
    return str(x_value)
