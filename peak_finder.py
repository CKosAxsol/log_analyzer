#!/usr/bin/env python3
"""CLI entry point for finding threshold crossings in APS/APU CSV exports."""

from __future__ import annotations

import argparse
from pathlib import Path
import sys

from functions.csv_parser import parse_csv
from functions.path_utils import resolve_csv_path
from functions.threshold_reporting import print_threshold_summary
from functions.thresholds import find_threshold_events
from functions.time_filters import filter_series_by_time, parse_optional_timestamp


DEFAULT_COLUMNS = ["VL12/V", "VL23/V", "VL31/V"]


def parse_args() -> argparse.Namespace:
    """Build and parse the command line interface for threshold analysis."""
    parser = argparse.ArgumentParser(
        description=(
            "Read APS/APU CSV files and print timestamps where selected "
            "voltage columns cross below or above configured thresholds."
        ),
    )
    parser.add_argument(
        "--H",
        action="help",
        help="Show this help message and exit.",
    )
    parser.add_argument("files", nargs="+", help="One or more CSV files to analyze.")
    parser.add_argument(
        "--system-name",
        default="APU 2",
        help="System row label to evaluate, e.g. 'APU 2'. Default: %(default)s",
    )
    parser.add_argument(
        "--record-type",
        default="APU Stat 10s",
        help="Record type to evaluate. Default: %(default)s",
    )
    parser.add_argument(
        "--columns",
        nargs="+",
        default=DEFAULT_COLUMNS,
        help=f"Columns to check. Default: {' '.join(DEFAULT_COLUMNS)}",
    )
    parser.add_argument(
        "--threshold-low",
        type=float,
        default=None,
        help="Report timestamps where the signal falls below this value.",
    )
    parser.add_argument(
        "--threshold-high",
        type=float,
        default=None,
        help="Report timestamps where the signal rises above this value.",
    )
    parser.add_argument(
        "--time-start",
        default=None,
        help="Optional start timestamp in format YYYY-MM-DD HH:MM:SS.",
    )
    parser.add_argument(
        "--time-end",
        default=None,
        help="Optional end timestamp in format YYYY-MM-DD HH:MM:SS.",
    )
    parser.add_argument("--delimiter", default=";", help="CSV delimiter. Default: %(default)s")
    args = parser.parse_args()
    validate_threshold_args(args)
    return args


def validate_threshold_args(args: argparse.Namespace) -> None:
    """Reject calls that do not request any threshold search.

    Without at least one threshold the tool would parse the file but have
    no actual condition to evaluate.
    """
    if args.threshold_low is None and args.threshold_high is None:
        raise ValueError("Use at least one of --threshold-low or --threshold-high")


def process_file(csv_path: Path, args: argparse.Namespace) -> None:
    """Parse, filter, detect events, and print them for one CSV file.

    This mirrors the same staged pipeline as `log_analyzer.py`, but swaps
    plotting/reporting for threshold detection/reporting.
    """
    parsed = parse_csv(
        csv_path=csv_path,
        system_name=args.system_name,
        record_type=args.record_type,
        columns=list(args.columns),
        delimiter=args.delimiter,
    )
    parsed = filter_series_by_time(
        parsed=parsed,
        time_start=parse_optional_timestamp(args.time_start, "--time-start"),
        time_end=parse_optional_timestamp(args.time_end, "--time-end"),
    )
    events = find_threshold_events(
        parsed=parsed,
        lower_threshold=args.threshold_low,
        upper_threshold=args.threshold_high,
    )
    print(f"File: {csv_path}")
    print_threshold_summary(events)


def main() -> int:
    """Program entry point.

    Argument errors are handled before file processing starts so the user
    gets immediate feedback for invalid calls.
    """
    try:
        args = parse_args()
    except Exception as exc:
        print(exc, file=sys.stderr)
        return 1

    had_error = False
    for file_arg in args.files:
        csv_path = resolve_csv_path(file_arg)
        if not csv_path.exists():
            print(f"File not found: {csv_path}", file=sys.stderr)
            had_error = True
            continue

        try:
            process_file(csv_path=csv_path, args=args)
        except Exception as exc:
            print(f"Error while processing {csv_path}: {exc}", file=sys.stderr)
            had_error = True

    return 1 if had_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
