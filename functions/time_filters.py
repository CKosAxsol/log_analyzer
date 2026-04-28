"""Time parsing and filtering helpers."""

from __future__ import annotations

from datetime import datetime

from .models import ParsedSeries


TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def parse_optional_timestamp(raw_value: str | None, label: str) -> datetime | None:
    """Parse an optional timestamp argument from the CLI."""
    if raw_value is None:
        return None
    try:
        return datetime.strptime(raw_value, TIMESTAMP_FORMAT)
    except ValueError as exc:
        raise ValueError(
            f"Invalid {label} value '{raw_value}'. Expected format: {TIMESTAMP_FORMAT}"
        ) from exc


def filter_series_by_time(
    parsed: ParsedSeries,
    time_start: datetime | None,
    time_end: datetime | None,
) -> ParsedSeries:
    """Keep only rows within the requested plotting window."""
    if time_start is None and time_end is None:
        return parsed
    if time_start is not None and time_end is not None and time_start > time_end:
        raise ValueError("--time-start must be earlier than or equal to --time-end")

    selected_indices = [
        idx
        for idx, timestamp in enumerate(parsed.timestamps)
        if (time_start is None or timestamp >= time_start)
        and (time_end is None or timestamp <= time_end)
    ]
    if not selected_indices:
        raise ValueError("No rows remain after applying the selected time range")

    filtered_series = {
        column: [values[idx] for idx in selected_indices]
        for column, values in parsed.series.items()
    }
    filtered_timestamps = [parsed.timestamps[idx] for idx in selected_indices]
    return ParsedSeries(
        csv_path=parsed.csv_path,
        system_name=parsed.system_name,
        record_type=parsed.record_type,
        timestamps=filtered_timestamps,
        series=filtered_series,
    )
