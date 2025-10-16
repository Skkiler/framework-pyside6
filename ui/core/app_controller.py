# ui/core/app_controller.py

from __future__ import annotations

from dataclasses import dataclass
from pathlib import Path
from typing import Iterable, List, Optional

from ..services.task_runner_adapter import TaskRunnerAdapter
from .app import AppShell
from ..pages.registry import load_from_manifest, discover_pages


@dataclass(frozen=True)
class ControllerConfig:
    assets_dir: Path
    themes_dir: Path
    base_qss_path: Path
    app_title: str
    default_theme: str
    first_page: str
    manifest_filename: str


def _merge_specs(primary: Iterable, fallback: Iterable) -> List:
    # primary (manifest) tem prioridade; dedup por route; ordena por (order, label)
    by_route = {}
    for spec in fallback:
        by_route[getattr(spec, "route", "")] = spec
    for spec in primary:
        by_route[getattr(spec, "route", "")] = spec  # override
    merged = list(by_route.values())
    merged.sort(key=lambda s: (getattr(s, "order", 1000), getattr(s, "label", getattr(s, "route", ""))))
    return merged


class AppController:
    """
    Responsável por:
      - construir AppShell com serviços injetados
      - carregar PageSpecs (manifest + autodiscovery)
      - registrar páginas
      - iniciar tema e primeira rota
    """

    def __init__(
        self,
        *,
        task_runner,
        assets_dir: str,
        base_qss_path: str,
        themes_dir: str,
        default_theme: str,
        first_page: str,
        manifest_filename: str,
        settings,
        app_title: str,
    ):
        self.cfg = ControllerConfig(
            assets_dir=Path(assets_dir),
            themes_dir=Path(themes_dir),
            base_qss_path=Path(base_qss_path),
            app_title=app_title,
            default_theme=default_theme,
            first_page=first_page,
            manifest_filename=manifest_filename,
        )
        self.settings = settings
        self.task_runner_adapter = TaskRunnerAdapter(task_runner) if task_runner else None

        self.shell = AppShell(
            title=self.cfg.app_title,
            assets_dir=str(self.cfg.assets_dir),
            themes_dir=str(self.cfg.themes_dir),
            base_qss_path=str(self.cfg.base_qss_path),
            settings=self.settings,
        )

        # Carrega e registra páginas
        self._init_pages()

        # Inicia tema + primeira rota
        self.shell.start(first_route=self.cfg.first_page, default_theme=self.cfg.default_theme)

    # ----- ciclo de páginas -----
    def _init_pages(self):
        manifest_path = self.cfg.assets_dir / self.cfg.manifest_filename
        from_manifest = load_from_manifest(manifest_path) if manifest_path.exists() else []
        auto = discover_pages()
        specs = _merge_specs(from_manifest, auto)
        self.shell.register_pages(specs, task_runner=self.task_runner_adapter)

    # ----- API simples -----
    def show(self):
        self.shell.show()
