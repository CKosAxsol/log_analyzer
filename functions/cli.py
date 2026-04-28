"""Argument parsing for the voltage analyzer CLI."""

from __future__ import annotations

import argparse


DEFAULT_COLUMNS = ["VL12/V", "VL23/V", "VL31/V"]


def parse_args() -> argparse.Namespace:
    """Build and parse the command line interface.

    This module only defines CLI arguments. The actual work is done in the
    parser, filter, plotting, and reporting modules so each responsibility
    stays easy to understand and test in isolation.
    """
    parser = argparse.ArgumentParser(
        description=(
            "Read APS/APU CSV files, extract selected voltage columns, "
            "and create time-series plots."
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
        help=f"Columns to plot. Default: {' '.join(DEFAULT_COLUMNS)}",
    )
    parser.add_argument(
        "--output-dir",
        default="scripts/output",
        help="Directory for generated PNG plots. Default: %(default)s",
    )
    parser.add_argument("--title", default=None, help="Optional custom title for the plot.")
    parser.add_argument("--dpi", type=int, default=150, help="PNG resolution. Default: %(default)s")
    parser.add_argument("--y-min", type=float, default=None, help="Optional lower Y axis limit.")
    parser.add_argument("--y-max", type=float, default=None, help="Optional upper Y axis limit.")
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
    return parser.parse_args()
