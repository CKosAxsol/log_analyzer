#!/usr/bin/env python3
"""CLI entry point for analyzing voltage series from APS/APU CSV exports."""

from __future__ import annotations

from pathlib import Path
import sys

ROOT_DIR = Path(__file__).resolve().parents[1]
if str(ROOT_DIR) not in sys.path:
    sys.path.insert(0, str(ROOT_DIR))

from functions.cli import parse_args
from functions.csv_parser import parse_csv
from functions.dependencies import ensure_dependencies
from functions.path_utils import resolve_csv_path

ensure_dependencies()

import matplotlib  # noqa: E402

# Dieses CLI erzeugt nur PNG-Dateien. Darum wird bewusst ein
# nicht-interaktives Backend verwendet, damit keine grafische Oberflaeche
# noetig ist und das Skript auch auf einfachen Servern laeuft.
matplotlib.use("Agg")

from functions.plotting import plot_series  # noqa: E402
from functions.reporting import print_summary  # noqa: E402
from functions.time_filters import filter_series_by_time, parse_optional_timestamp  # noqa: E402

def process_file(
    csv_path: Path,
    args,
    columns: list[str],
    output_dir: Path,
) -> None:
    """Parse, filter, plot, and report for one CSV file.

    The processing order is intentionally linear:
    parse -> optional time filter -> plot -> console summary.
    """
    parsed = parse_csv(
        csv_path=csv_path,
        system_name=args.system_name,
        record_type=args.record_type,
        columns=columns,
        delimiter=args.delimiter,
    )
    # Die Zeitfilterung bleibt absichtlich getrennt, damit der reine CSV-Parser
    # auch in anderen Faellen unveraendert wiederverwendet werden kann.
    parsed = filter_series_by_time(
        parsed=parsed,
        time_start=parse_optional_timestamp(args.time_start, "--time-start"),
        time_end=parse_optional_timestamp(args.time_end, "--time-end"),
    )
    output_path = plot_series(
        parsed=parsed,
        columns=columns,
        output_dir=output_dir,
        title=args.title,
        dpi=args.dpi,
        y_min=args.y_min,
        y_max=args.y_max,
    )
    print_summary(parsed, columns, output_path)


def main() -> int:
    """Program entry point.

    We continue processing the remaining files even if one file fails so a
    batch run can still produce partial results.
    """
    args = parse_args()
    output_dir = Path(args.output_dir)
    columns = list(args.columns)

    had_error = False
    for file_arg in args.files:
        csv_path = resolve_csv_path(file_arg)
        if not csv_path.exists():
            print(f"File not found: {csv_path}", file=sys.stderr)
            had_error = True
            continue

        try:
            process_file(
                csv_path=csv_path,
                args=args,
                columns=columns,
                output_dir=output_dir,
            )
        except Exception as exc:
            print(f"Error while processing {csv_path}: {exc}", file=sys.stderr)
            had_error = True

    return 1 if had_error else 0


if __name__ == "__main__":
    raise SystemExit(main())
