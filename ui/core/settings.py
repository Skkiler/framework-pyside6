# ui/core/settings.py

from __future__ import annotations
from pathlib import Path
import json
from typing import Any, Optional


class Settings:

    def __init__(self, cache_dir: Optional[str | Path] = None, filename: str = "_ui_exec_settings.json"):
        # Fallback seguro: se não passar cache_dir, usa pasta do script atual
        base = Path(cache_dir) if cache_dir else Path(__file__).resolve().parents[2] / "ui" / "assets" / "cache"
        base.mkdir(parents=True, exist_ok=True)
        self._path = base / filename
        self._data: dict[str, Any] = {}
        self._load()

    # --- API compatível ---
    def read(self, key: str, default: Any = None) -> Any:
        return self._data.get(key, default)

    def write(self, key: str, value: Any) -> None:
        self._data[key] = value
        self._save()

    # --- helpers ---
    def _load(self) -> None:
        try:
            if self._path.exists():
                self._data = json.loads(self._path.read_text(encoding="utf-8")) or {}
            else:
                self._data = {}
        except Exception:
            self._data = {}

    def _save(self) -> None:
        try:
            self._path.write_text(json.dumps(self._data, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception:
            # se der erro de IO, não levanta — só não persiste
            pass

    @property
    def path(self) -> Path:
        return self._path
