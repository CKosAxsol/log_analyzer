"""Hilfsfunktionen fuer die zentrale Versionsnummer des Projekts."""

from __future__ import annotations

from pathlib import Path


def read_project_version(root_dir: Path) -> str:
    """Liest die Projektversion aus der zentralen VERSION-Datei."""
    version_file = root_dir / "VERSION"
    try:
        version_text = version_file.read_text(encoding="utf-8").strip()
    except FileNotFoundError:
        return "unbekannt"
    return version_text or "unbekannt"

