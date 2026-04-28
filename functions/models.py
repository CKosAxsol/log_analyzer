"""Shared data models for the CSV voltage analyzer."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime
from pathlib import Path


@dataclass
class ParsedSeries:
    """Container for one parsed CSV time series selection."""

    csv_path: Path
    system_name: str
    record_type: str
    timestamps: list[datetime]
    series: dict[str, list[float]]


@dataclass
class ThresholdEvent:
    """One detected threshold crossing in a time series."""

    column: str
    timestamp: datetime
    value: float
    direction: str
    threshold: float
