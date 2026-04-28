"""Runtime dependency bootstrap."""

from __future__ import annotations

import importlib
import subprocess
import sys


def ensure_package(module_name: str, package_name: str | None = None) -> None:
    """Install a missing Python package via pip and verify that it imports.

    We import first and install only on demand so the tools still work in a
    fresh environment without forcing a separate setup step.
    """
    try:
        importlib.import_module(module_name)
    except ImportError:
        target = package_name or module_name
        print(f"Installing missing dependency: {target}", file=sys.stderr)
        subprocess.check_call([sys.executable, "-m", "pip", "install", target])
        importlib.import_module(module_name)


def ensure_dependencies() -> None:
    """Install shared runtime dependencies on first use.

    Centralizing this here avoids each entry point hard-coding its own
    package bootstrap logic.
    """
    ensure_package("matplotlib")
