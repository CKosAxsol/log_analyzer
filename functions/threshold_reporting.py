"""Console reporting for threshold events."""

from __future__ import annotations

from collections import defaultdict

from .models import ThresholdEvent


def print_threshold_summary(events: list[ThresholdEvent]) -> None:
    """Print all detected threshold events grouped by column.

    The output is split into:

    - a short count per column for a quick overview
    - the detailed event list for exact timestamps
    """
    if not events:
        print("No threshold crossings found in the selected time range.")
        return

    counts_by_column: dict[str, int] = defaultdict(int)
    for event in events:
        counts_by_column[event.column] += 1

    print(f"Threshold crossings found: {len(events)}")
    for column in sorted(counts_by_column):
        print(f"  {column}: {counts_by_column[column]}")

    print("Events:")
    for event in events:
        direction_label = "unter" if event.direction == "below" else "ueber"
        print(
            f"  {event.timestamp} | {event.column} | {event.value:.2f} V | "
            f"{direction_label} {event.threshold:.2f} V"
        )
