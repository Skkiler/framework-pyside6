# ui/core/app.py

from __future__ import annotations

from pathlib import Path
from typing import Iterable

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout

from .router import Router
from .settings import Settings
from .theme_service import ThemeService
from ui.widgets.topbar import TopBar
from ui.widgets.overlay_sidebar import OverlaySidePanel
from ui.services.theme_repository_json import JsonThemeRepository
from .frameless_window import FramelessWindow
from ui.widgets.titlebar import TitleBar
from ui.widgets.settings_sidebar import SettingsSidePanel
from app.pages.settings import build as build_settings_page

# utils
from .utils.paths import ensure_dir, safe_icon


class AppShell(FramelessWindow):

    def __init__(self, title: str, assets_dir: str, themes_dir: str, base_qss_path: str, settings: Settings):
        super().__init__()
        self.setWindowTitle(title)
        self.setObjectName("RootWindow")
        self.resize(1100, 720)

        self.assets_dir = Path(assets_dir)
        self.cache_dir = ensure_dir(self.assets_dir / "cache")
        self.settings = settings

        self.router = Router()

        self.theme_service = ThemeService(
            repo=JsonThemeRepository(themes_dir),
            root=self,
            settings=self.settings,
            base_qss_path=base_qss_path,
            animate_ms_default=450,
            cache_dir=self.cache_dir,
        )

        central = self._build_central(title)
        self.setCentralWidget(central)

        # Sidebar (navegação)
        self.sidebar = OverlaySidePanel(parent=central, use_scrim=True, close_on_scrim=True, close_on_select=True)
        self.sidebar.pageSelected.connect(self._go)

        # Sidebar (configurações)
        self._settings_widget = build_settings_page(theme_service=self.theme_service)
        self.settings_panel = SettingsSidePanel(
            parent=central,
            content=self._settings_widget,
            use_scrim=True,
            close_on_scrim=True,
        )

        # Dicionário de rotas -> labels (preenchido ao registrar páginas)
        self._page_labels: dict[str, str] = {}

    # ---------------------------------------------------------
    #  Montagem da UI
    # ---------------------------------------------------------
    def _build_central(self, title: str) -> QWidget:
        central = QWidget()
        central.setProperty("role", "content")

        root_v = QVBoxLayout(central)
        root_v.setContentsMargins(0, 0, 0, 0)
        root_v.setSpacing(0)

        # TitleBar (janela principal)
        icon_path = self.assets_dir / "icons" / "app.ico"
        icon_ref = safe_icon(icon_path)
        self.titlebar = TitleBar(title, self, icon=icon_ref)
        root_v.addWidget(self.titlebar)
        self.connect_titlebar(self.titlebar)
        self.titlebar.settingsRequested.connect(self._toggle_settings_panel)

        # Topbar (inicialmente sem título; será atualizado conforme página)
        self.topbar = TopBar(onHamburgerClick=self._toggle_sidebar, title=None)
        root_v.addWidget(self.topbar)

        # Router (conteúdo principal)
        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)
        root_v.addLayout(content)
        content.addWidget(self.router)

        return central

    # ---------------------------------------------------------
    #  Registro de páginas
    # ---------------------------------------------------------
    def register_page(self, route, widget, label=None, show_in_sidebar=True):
        """Registra uma única página no roteador e sidebar."""
        self.router.register(route, widget)
        if show_in_sidebar:
            self.sidebar.add_page(route, label or route)

        # Guarda o label (para exibir na TopBar)
        self._page_labels[route] = label or route

    def register_pages(self, specs: Iterable, *, task_runner=None):
        """Registra páginas a partir de uma lista de PageSpecs."""
        from .utils.factories import call_with_known_kwargs
        for spec in specs:
            widget = call_with_known_kwargs(
                spec.factory,
                task_runner=task_runner,
                theme_service=self.theme_service,
            )
            self.register_page(spec.route, widget, spec.label, spec.sidebar)

    # ---------------------------------------------------------
    #  Inicialização (tema + página inicial)
    # ---------------------------------------------------------
    def start(self, first_route: str, default_theme: str = "Dracula"):
        """Aplica o tema e navega para a primeira página."""
        chosen = self.theme_service.load_selected_from_settings() or default_theme
        avail = self.theme_service.available()
        if avail:
            self.theme_service.apply(
                chosen if chosen in avail else avail[0],
                animate=False,
                persist=False,
            )

        # Navega para a página inicial
        self.router.go(first_route)

        # Define o título da TopBar como o da página inicial
        try:
            label = self._page_labels.get(first_route, first_route)
            if hasattr(self.topbar, "set_title"):
                self.topbar.set_title(label)
        except Exception as e:
            print(f"[WARN] Falha ao definir título inicial da TopBar: {e}")

    # ---------------------------------------------------------
    #  Ações simples
    # ---------------------------------------------------------
    def _toggle_settings_panel(self):
        try:
            self.settings_panel.toggle()
        except Exception as e:  # noqa: BLE001
            print("[ERRO] toggle settings panel:", e)

    def _toggle_sidebar(self):
        self.sidebar.toggle()

    def _go(self, route: str):
        """Troca de rota e atualiza o título da TopBar."""
        self.router.go(route)
        try:
            label = self._page_labels.get(route, route)
            if hasattr(self.topbar, "set_title"):
                self.topbar.set_title(label)
        except Exception as e:
            print("[WARN] Falha ao atualizar título da TopBar:", e)
