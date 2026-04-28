"""CSV export helpers for the interactive plotter."""

from __future__ import annotations

import csv
from pathlib import Path
from typing import Callable

from .csv_plotter_utils import XValue, format_x_value


def get_export_row_indices(
    export_scope: str,
    x_values: list[XValue],
    series_map: dict[str, list[float]],
    plot_columns: list[str],
    x_limits: tuple[float, float],
    y_limits: tuple[float, float],
    to_plot_coordinate: Callable[[XValue], float | int | str],
) -> list[int]:
    """Return all plotted row indices or only those inside the visible axes."""
    if export_scope != "visible":
        return list(range(len(x_values)))

    x_lower, x_upper = sorted(x_limits)
    y_lower, y_upper = sorted(y_limits)
    row_indices: list[int] = []
    for index, x_value in enumerate(x_values):
        try:
            numeric_x = float(to_plot_coordinate(x_value))
        except (TypeError, ValueError):
            continue
        if x_lower <= numeric_x <= x_upper and row_has_visible_y_value(index, series_map, plot_columns, y_lower, y_upper):
            row_indices.append(index)
    return row_indices


def row_has_visible_y_value(
    index: int,
    series_map: dict[str, list[float]],
    plot_columns: list[str],
    y_lower: float,
    y_upper: float,
) -> bool:
    """Return True when at least one plotted series is inside the visible Y range."""
    for column in plot_columns:
        values = series_map.get(column, [])
        if index < len(values) and y_lower <= values[index] <= y_upper:
            return True
    return False


def write_plot_export(
    output_path: Path,
    delimiter: str,
    x_label: str,
    x_values: list[XValue],
    plot_columns: list[str],
    series_map: dict[str, list[float]],
    row_indices: list[int],
) -> None:
    """Write selected plotted rows as CSV with one X column and all plotted Y series."""
    with output_path.open("w", newline="", encoding="utf-8-sig") as handle:
        writer = csv.writer(handle, delimiter=delimiter)
        writer.writerow([x_label, *plot_columns])
        for index in row_indices:
            row = [format_x_value(x_values[index])]
            for column in plot_columns:
                values = series_map.get(column, [])
                row.append(f"{values[index]:g}" if index < len(values) else "")
            writer.writerow(row)
