"""Threshold detection helpers for voltage time series."""

from __future__ import annotations

from .models import ParsedSeries, ThresholdEvent


def find_threshold_events(
    parsed: ParsedSeries,
    lower_threshold: float | None,
    upper_threshold: float | None,
) -> list[ThresholdEvent]:
    """Detect threshold crossings for all selected columns.

    A lower-threshold event is emitted when the series moves from
    `>= lower_threshold` to `< lower_threshold`.
    An upper-threshold event is emitted when the series moves from
    `<= upper_threshold` to `> upper_threshold`.
    """
    events: list[ThresholdEvent] = []

    for column, values in parsed.series.items():
        if len(values) < 2:
            continue
        for idx in range(1, len(values)):
            # Ein Schwellwert-Ereignis wird nur dann erkannt, wenn der Wert
            # zwischen zwei direkt benachbarten Messpunkten die Grenze ueber-
            # oder unterschreitet. Einzelne Werte fuer sich allein reichen nicht.
            previous_value = values[idx - 1]
            current_value = values[idx]
            timestamp = parsed.timestamps[idx]

            if lower_threshold is not None and crossed_below(previous_value, current_value, lower_threshold):
                events.append(
                    ThresholdEvent(
                        column=column,
                        timestamp=timestamp,
                        value=current_value,
                        direction="below",
                        threshold=lower_threshold,
                    )
                )

            if upper_threshold is not None and crossed_above(previous_value, current_value, upper_threshold):
                events.append(
                    ThresholdEvent(
                        column=column,
                        timestamp=timestamp,
                        value=current_value,
                        direction="above",
                        threshold=upper_threshold,
                    )
                )

    return sorted(events, key=lambda event: (event.timestamp, event.column, event.direction))


def crossed_below(previous_value: float, current_value: float, threshold: float) -> bool:
    """Return True when the signal enters the below-threshold region.

    We only report the actual crossing moment. Staying below the threshold
    for many following rows does not create duplicate events.
    """
    return previous_value >= threshold and current_value < threshold


def crossed_above(previous_value: float, current_value: float, threshold: float) -> bool:
    """Return True when the signal enters the above-threshold region.

    We only report the actual crossing moment. Staying above the threshold
    for many following rows does not create duplicate events.
    """
    return previous_value <= threshold and current_value > threshold
