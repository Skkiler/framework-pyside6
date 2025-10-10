# ui/core/app.py

import inspect
from pathlib import Path
from typing import Iterable

from PySide6.QtWidgets import QMainWindow, QWidget, QVBoxLayout, QHBoxLayout

from .router import Router
from .settings import Settings
from .theme_service import ThemeService
from ..widgets.topbar import TopBar
from ..widgets.overlay_sidebar import OverlaySidePanel
from ..services.theme_repository_json import JsonThemeRepository


class AppShell(QMainWindow):
    def __init__(self, title: str, assets_dir: str, themes_dir: str, base_qss_path: str):
        super().__init__()
        self.setWindowTitle(title)
        self.setObjectName("RootWindow")
        self.resize(1100, 720)

        assets_dir_path = Path(assets_dir)

        # --- cache local do projeto: ui/assets/cache ---
        self.cache_dir = assets_dir_path / "cache"
        self.cache_dir.mkdir(parents=True, exist_ok=True)

        # Settings: tenta usar assinatura com cache_dir; se não houver, faz fallback
        try:
            self.settings = Settings(cache_dir=self.cache_dir, filename="_ui_exec_settings.json")
        except TypeError:
            self.settings = Settings()

        self.router = Router()

        self.theme_service = ThemeService(
            repo=JsonThemeRepository(themes_dir),
            root=self,
            settings=self.settings,
            base_qss_path=base_qss_path,
            animate_ms_default=450,
            cache_dir=self.cache_dir,
        )

        # -------- UI base --------
        central = QWidget()
        central.setProperty("role", "content")
        self.setCentralWidget(central)

        root_v = QVBoxLayout(central)
        root_v.setContentsMargins(0, 0, 0, 0)
        root_v.setSpacing(0)

        # Topbar
        self.topbar = TopBar(onHamburgerClick=self._toggle_sidebar, title=title)
        root_v.addWidget(self.topbar)

        # Área central (router)
        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)
        root_v.addLayout(content)

        content.addWidget(self.router)

        # OverlaySidePanel flutuante sobre o central widget (fora do layout)
        self.sidebar = OverlaySidePanel(parent=central, use_scrim=True, close_on_scrim=True, close_on_select=True)
        self.sidebar.pageSelected.connect(self._go)
        # self.sidebar.set_close_on_select(True)

    # -------- public helpers --------
    def register_page(self, route: str, widget: QWidget, label: str | None = None, show_in_sidebar: bool = True):
        self.router.register(route, widget)
        if show_in_sidebar:
            self.sidebar.add_page(route, label or route)

    def _call_factory(self, factory, **deps):
        params = inspect.signature(factory).parameters
        use = {k: v for k, v in deps.items() if k in params}
        return factory(**use)

    def register_pages(self, specs: Iterable, *, task_runner=None):
        for spec in specs:
            widget = self._call_factory(
                spec.factory,
                task_runner=task_runner,
                theme_service=self.theme_service,
            )
            self.register_page(spec.route, widget, spec.label, spec.sidebar)

    def start(self, first_route: str, default_theme: str = "Dracula"):
        chosen = self.theme_service.load_selected_from_settings() or default_theme
        avail = self.theme_service.available()
        if avail:
            self.theme_service.apply(
                chosen if chosen in avail else avail[0],
                animate=False,
                persist=False,
            )
        self.router.go(first_route)

    # -------- callbacks --------
    def _toggle_sidebar(self):
        self.sidebar.toggle()

    def _go(self, route: str):
        self.router.go(route)
