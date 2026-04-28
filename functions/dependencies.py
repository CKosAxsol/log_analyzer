"""Runtime dependency bootstrap."""

from __future__ import annotations

import importlib
import subprocess
import sys


def ensure_package(module_name: str, package_name: str | None = None) -> None:
    """Install a missing Python package via pip and verify that it imports."""
    try:
        importlib.import_module(module_name)
    except ImportError:
        target = package_name or module_name
        print(f"Installing missing dependency: {target}", file=sys.stderr)
        subprocess.check_call([sys.executable, "-m", "pip", "install", target])
        importlib.import_module(module_name)


def ensure_dependencies() -> None:
    """Install shared runtime dependencies on first use."""
    ensure_package("matplotlib")
