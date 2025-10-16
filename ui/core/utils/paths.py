# ui/core/utils/paths.py

from __future__ import annotations
from pathlib import Path
from PySide6.QtGui import QIcon

def ensure_dir(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    return path

def safe_icon(path: Path) -> QIcon | None:
    return QIcon(str(path)) if path and path.exists() else None
