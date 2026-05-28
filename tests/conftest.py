"""Pytest configuration and shared test utilities."""
import os
import sys
from pathlib import Path


def resolve_test_python(root: Path | None = None) -> Path:
    """Resolve Python executable path for subprocess tests.
    
    Prefers venv Python if available, falls back to sys.executable.
    Supports Windows (.venv/Scripts/python.exe) and Unix (.venv/bin/python).
    """
    if root is None:
        root = Path(__file__).resolve().parent.parent
    else:
        root = Path(root).resolve()
    
    # Candidates in order of preference
    candidates = [
        root / ".venv" / "Scripts" / "python.exe",  # Windows
        root / ".venv" / "bin" / "python",          # Unix/macOS
        root / ".venv" / "bin" / "python3",         # Unix/macOS alternative
    ]
    
    for candidate in candidates:
        if candidate.exists():
            return candidate.resolve()
    
    # Fall back to current Python
    return Path(sys.executable).resolve()
