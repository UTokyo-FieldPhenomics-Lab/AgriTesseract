"""Pytest path bootstrap for nested rename IDs tests."""

from __future__ import annotations

import sys
from pathlib import Path


def _append_repo_root() -> None:
    """Ensure repository root is present in import path."""
    repo_root = Path(__file__).resolve().parents[2]
    repo_root_text = str(repo_root)
    if repo_root_text in sys.path:
        return
    sys.path.insert(0, repo_root_text)


_append_repo_root()
