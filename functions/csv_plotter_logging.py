"""Hilfsfunktionen fuer die Protokollierung und Log-Pflege des CSV-Plotters."""

from __future__ import annotations

import logging
import traceback
from datetime import datetime, timedelta
from pathlib import Path


LOGGER_NAME = "csv_plotter"
LOG_RETENTION_DAYS = 30


def prepare_log_directory(root_dir: Path) -> tuple[Path, int]:
    """Erzeugt den Log-Ordner und entfernt alte Log-Dateien automatisch."""
    log_dir = root_dir / "log"
    log_dir.mkdir(parents=True, exist_ok=True)
    deleted_count = cleanup_old_log_files(log_dir)
    return log_dir, deleted_count


def cleanup_old_log_files(log_dir: Path) -> int:
    """Loescht Log-Dateien, die aelter als die Aufbewahrungszeit sind."""
    cutoff_time = datetime.now() - timedelta(days=LOG_RETENTION_DAYS)
    deleted_count = 0
    for log_file in sorted(log_dir.glob("*.log"), key=lambda path: path.stat().st_mtime):
        modified_time = datetime.fromtimestamp(log_file.stat().st_mtime)
        if modified_time >= cutoff_time:
            break
        log_file.unlink(missing_ok=True)
        deleted_count += 1
    return deleted_count


def configure_csv_plotter_logging(root_dir: Path) -> tuple[logging.Logger, Path]:
    """Richtet eine dateibasierte Protokollierung im Projektordner ein."""
    log_dir, deleted_count = prepare_log_directory(root_dir)
    log_path = log_dir / f"csv_plotter_{datetime.now().strftime('%Y%m%d_%H%M%S')}.log"

    logger = logging.getLogger(LOGGER_NAME)
    logger.setLevel(logging.INFO)
    logger.handlers.clear()
    logger.propagate = False

    file_handler = logging.FileHandler(log_path, encoding="utf-8")
    file_handler.setLevel(logging.INFO)
    file_handler.setFormatter(
        logging.Formatter("%(asctime)s | %(levelname)s | %(message)s")
    )
    logger.addHandler(file_handler)
    logger.info(
        "Log-Ordner vorbereitet. Automatisch geloeschte Log-Dateien aelter als %s Tage: %s",
        LOG_RETENTION_DAYS,
        deleted_count,
    )
    return logger, log_path


def log_exception(logger: logging.Logger, context_message: str, exc: BaseException) -> None:
    """Schreibt einen Fehler mit kompletter Rueckverfolgung in die Log-Datei."""
    logger.error("%s\n%s", context_message, "".join(traceback.format_exception(exc)))
