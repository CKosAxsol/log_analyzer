"""Helpers for resolving local file paths."""

from __future__ import annotations

from pathlib import Path


def resolve_csv_path(file_arg: str) -> Path:
    """Resolve relative file arguments against the current working directory.

    The CLI accepts whatever path string the user passes in. Downstream code
    should not need to care whether it was relative, absolute, or used `~`.
    """
    csv_path = Path(file_arg).expanduser()
    if not csv_path.is_absolute():
        csv_path = Path.cwd() / csv_path
    return csv_path
