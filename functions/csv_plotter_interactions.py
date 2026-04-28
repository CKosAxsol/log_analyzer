"""Mouse interaction helpers for the interactive CSV plotter."""

from __future__ import annotations

from typing import Any

from .csv_plotter_utils import XValue


def is_left_mouse_button(event: object) -> bool:
    """Return True for a normal left-button click across Matplotlib versions."""
    button = getattr(event, "button", None)
    return button == 1 or getattr(button, "name", "").lower() == "left"


def is_middle_mouse_button(event: object) -> bool:
    """Return True for a middle-button click across Matplotlib versions."""
    button = getattr(event, "button", None)
    return button == 2 or getattr(button, "name", "").lower() == "middle"


def zoom_axes_around_cursor(axes: Any, x_cursor: float, y_cursor: float, zoom_factor: float) -> None:
    """Scale both axes around the cursor position."""
    current_xlim = axes.get_xlim()
    current_ylim = axes.get_ylim()

    left_span = (x_cursor - current_xlim[0]) * zoom_factor
    right_span = (current_xlim[1] - x_cursor) * zoom_factor
    lower_span = (y_cursor - current_ylim[0]) * zoom_factor
    upper_span = (current_ylim[1] - y_cursor) * zoom_factor

    axes.set_xlim(x_cursor - left_span, x_cursor + right_span)
    axes.set_ylim(y_cursor - lower_span, y_cursor + upper_span)


def pan_axes_from_drag(
    axes: Any,
    start_x: float,
    start_y: float,
    current_x: float,
    current_y: float,
    start_xlim: tuple[float, float],
    start_ylim: tuple[float, float],
) -> bool:
    """Pan axes according to a pixel-space mouse drag and return whether a pan happened."""
    bbox = axes.bbox
    if bbox.width == 0 or bbox.height == 0:
        return False

    x_span = start_xlim[1] - start_xlim[0]
    y_span = start_ylim[1] - start_ylim[0]
    dx = (current_x - start_x) * x_span / bbox.width
    dy = (current_y - start_y) * y_span / bbox.height

    axes.set_xlim(start_xlim[0] - dx, start_xlim[1] - dx)
    axes.set_ylim(start_ylim[0] - dy, start_ylim[1] - dy)
    return True


def find_nearest_point(
    axes: Any,
    click_x: float,
    click_y: float,
    x_values: list[XValue],
    series_map: dict[str, list[float]],
    plot_columns: list[str],
    to_plot_coordinate: Any,
) -> tuple[str, int, XValue, float] | None:
    """Return the plotted point closest to the click position in screen space."""
    nearest_point: tuple[str, int, XValue, float] | None = None
    min_distance_sq: float | None = None

    for column in plot_columns:
        y_values = series_map.get(column, [])
        for index, (x_value, y_value) in enumerate(zip(x_values, y_values)):
            point_x, point_y = axes.transData.transform((to_plot_coordinate(x_value), y_value))
            distance_sq = (point_x - click_x) ** 2 + (point_y - click_y) ** 2
            if min_distance_sq is None or distance_sq < min_distance_sq:
                min_distance_sq = distance_sq
                nearest_point = (column, index, x_value, y_value)
    return nearest_point
