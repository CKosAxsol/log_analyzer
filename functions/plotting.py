"""Plotting helpers for time series output."""

from __future__ import annotations

from pathlib import Path

import matplotlib.pyplot as plt
from matplotlib import dates as mdates

from .models import ParsedSeries


PALETTE = ["#0b6e4f", "#c84c09", "#2b59c3", "#7a1fa2", "#8f6f00", "#008b8b"]


def build_output_path(output_dir: Path, csv_path: Path) -> Path:
    """Create a deterministic PNG path for one input CSV.

    Keeping the file name deterministic makes repeated runs predictable:
    the newest result replaces the older plot for the same input file.
    """
    return output_dir / f"{csv_path.stem}_spannungen.png"


def plot_series(
    parsed: ParsedSeries,
    columns: list[str],
    output_dir: Path,
    title: str | None,
    dpi: int,
    y_min: float | None,
    y_max: float | None,
) -> Path:
    """Render the selected time series columns to a PNG file.

    This module knows nothing about CSV parsing details. It only receives
    already cleaned and aligned series data and turns that into an image.
    """
    output_dir.mkdir(parents=True, exist_ok=True)
    output_path = build_output_path(output_dir, parsed.csv_path)

    plt.style.use("seaborn-v0_8-whitegrid")
    fig, ax = plt.subplots(figsize=(14, 7), dpi=dpi)

    for idx, column in enumerate(columns):
        # Die Farben wechseln in einer festen Reihenfolge. So sieht dieselbe
        # Spaltenauswahl auch bei spaeteren Laeufen wieder gleich aus.
        ax.plot(
            parsed.timestamps,
            parsed.series[column],
            label=column,
            linewidth=1.2,
            color=PALETTE[idx % len(PALETTE)],
        )

    effective_title = title or f"{parsed.system_name} Spannungen ueber Zeit\n{parsed.csv_path.name}"
    ax.set_title(effective_title, fontsize=15)
    ax.set_xlabel("Zeitstempel")
    ax.set_ylabel("Spannung [V]")
    locator = mdates.AutoDateLocator()
    ax.xaxis.set_major_locator(locator)
    ax.xaxis.set_major_formatter(mdates.DateFormatter("%Y-%m-%d %H:%M:%S"))
    if y_min is not None or y_max is not None:
        ax.set_ylim(bottom=y_min, top=y_max)
    ax.legend()
    fig.autofmt_xdate()
    plt.tight_layout()
    fig.savefig(output_path)
    plt.close(fig)
    return output_path
