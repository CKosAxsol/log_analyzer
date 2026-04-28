"""CSV reading and parsing helpers."""

from __future__ import annotations

import csv
from datetime import datetime
from io import StringIO
from pathlib import Path
from typing import Iterable

from .models import ParsedSeries


DEFAULT_ENCODINGS = ["utf-8-sig", "cp1252", "latin-1"]
TIMESTAMP_COLUMN = "TimeStamp"
TIMESTAMP_FORMAT = "%Y-%m-%d %H:%M:%S"


def open_csv_with_fallbacks(csv_path: Path) -> StringIO:
    """Read CSV text using a small encoding fallback chain."""
    last_error: Exception | None = None
    for encoding in DEFAULT_ENCODINGS:
        try:
            text = csv_path.read_text(encoding=encoding)
            return StringIO(text)
        except UnicodeDecodeError as exc:
            last_error = exc
    if last_error is not None:
        raise last_error
    return StringIO(csv_path.read_text())


def parse_csv(
    csv_path: Path,
    system_name: str,
    record_type: str,
    columns: Iterable[str],
    delimiter: str,
) -> ParsedSeries:
    """Extract one logical time series block from the semicolon-separated export."""
    selected_columns = list(columns)
    header_map: dict[str, int] | None = None
    timestamps: list[datetime] = []
    series = {column: [] for column in selected_columns}

    with open_csv_with_fallbacks(csv_path) as handle:
        reader = csv.reader(handle, delimiter=delimiter)
        for row in reader:
            if not row or len(row) < 3:
                continue
            if row[0] == record_type and row[2] == TIMESTAMP_COLUMN:
                # The schema row appears in the same file as the data rows.
                header_map = {name: idx for idx, name in enumerate(row)}
                continue
            if row[0] != record_type or row[1] != system_name:
                continue
            if header_map is None:
                raise ValueError(
                    f"No schema line found for record type '{record_type}' in {csv_path}"
                )
            timestamp, values = parse_data_row(
                row=row,
                header_map=header_map,
                csv_path=csv_path,
                selected_columns=selected_columns,
            )
            if timestamp is None or values is None:
                continue

            timestamps.append(timestamp)
            for column, value in zip(selected_columns, values):
                series[column].append(value)

    if not timestamps:
        raise ValueError(
            f"No matching rows found in {csv_path} for record type '{record_type}' "
            f"and system '{system_name}'"
        )

    return ParsedSeries(
        csv_path=csv_path,
        system_name=system_name,
        record_type=record_type,
        timestamps=timestamps,
        series=series,
    )


def parse_data_row(
    row: list[str],
    header_map: dict[str, int],
    csv_path: Path,
    selected_columns: list[str],
) -> tuple[datetime | None, list[float] | None]:
    """Parse one CSV row into timestamp and numeric values."""
    try:
        timestamp = datetime.strptime(row[header_map[TIMESTAMP_COLUMN]], TIMESTAMP_FORMAT)
        values = [float(row[header_map[column]]) for column in selected_columns]
        return timestamp, values
    except (KeyError, IndexError) as exc:
        raise ValueError(f"Missing expected column in {csv_path}: {exc}") from exc
    except ValueError:
        # Skip malformed rows instead of failing the whole file.
        return None, None
