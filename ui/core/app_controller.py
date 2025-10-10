# ui/core/app_controller.py

from __future__ import annotations
from pathlib import Path
from typing import Optional, List, Dict

from ..services.task_runner_adapter import TaskRunnerAdapter
from .app import AppShell
from ..pages.registry import load_from_manifest, discover_pages  # <- nomes corretos


def _merge_specs(primary, fallback):
    """
    Junta listas de PageSpec:
      - primary (manifest) tem prioridade sobre fallback (autodiscovery)
      - deduplica por route
      - ordena por (order, label)
    """
    by_route: Dict[str, object] = {}
    for spec in fallback:
        by_route[getattr(spec, "route", "")] = spec
    for spec in primary:
        by_route[getattr(spec, "route", "")] = spec  # override
    merged = list(by_route.values())
    merged.sort(key=lambda s: (getattr(s, "order", 999), getattr(s, "label", "").lower()))
    return merged


class AppController:
    def __init__(
        self,
        task_runner,
        assets_dir: str,
        *,
        auto_start: bool = True,
        default_theme: str = "Dracula",
        first_page: str = "home",
        manifest_filename: str = "pages_manifest.json",   # opcional
    ):
        self.task_runner = TaskRunnerAdapter(task_runner)

        assets_dir_path = Path(assets_dir)
        base_qss   = str(assets_dir_path / "qss" / "base.qss")
        themes_dir = str(assets_dir_path / "themes")

        self.app = AppShell("Executável", assets_dir, themes_dir, base_qss)

        # 1) tenta manifesto (se existir) + 2) auto-discovery fallback
        manifest_path = assets_dir_path / manifest_filename
        pri = load_from_manifest(str(manifest_path)) if manifest_path.exists() else []
        fb  = discover_pages("ui.pages")

        specs = _merge_specs(pri, fb)

        # registra em lote
        self.app.register_pages(specs, task_runner=self.task_runner)

        self._first_page    = first_page
        self._default_theme = default_theme
        if auto_start:
            self.start()

    def start(self, first_page: Optional[str] = None, default_theme: Optional[str] = None) -> None:
        page  = first_page or self._first_page
        theme = default_theme or self._default_theme
        self.app.start(page, default_theme=theme)

    def show(self) -> None:
        self.app.show()

    @property
    def theme_service(self):
        return self.app.theme_service
