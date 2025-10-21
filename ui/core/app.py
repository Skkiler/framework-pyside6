# ui/core/app.py

from __future__ import annotations

from pathlib import Path
from typing import Iterable
import json

from PySide6.QtGui import QIcon
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QApplication
from PySide6.QtCore import QFileSystemWatcher, QTimer

from .router import Router
from .settings import Settings
from .theme_service import ThemeService
from .frameless_window import FramelessWindow

from ui.widgets.topbar import TopBar
from ui.widgets.overlay_sidebar import OverlaySidePanel
from ui.services.theme_repository_json import JsonThemeRepository
from ui.widgets.titlebar import TitleBar
from ui.widgets.settings_sidebar import SettingsSidePanel

from app.pages.settings import build as build_settings_page

try:
    from app import settings as S
except Exception:
    S = None

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

        # Sincroniza ícone com o tema (titlebar + taskbar)
        self._setup_theme_icon_sync()

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
        icon_path = self.assets_dir / "icons" / "app" / "app.ico"
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

    # ---------------------- ÍCONE DO APP SINCRONIZADO COM TEMA ----------------------

    def _setup_theme_icon_sync(self) -> None:
        # 1) Conecta em sinais do ThemeService (pegamos os mais comuns)
        try:
            if hasattr(self, "theme_service"):
                for sig_name in ("themeApplied", "themeChanged", "paletteChanged", "styleApplied"):
                    if hasattr(self.theme_service, sig_name):
                        getattr(self.theme_service, sig_name).connect(self._update_app_icon_for_theme)
        except Exception as e:
            print("[WARN] não consegui conectar nos sinais de tema:", e)

        # 2) Observa o arquivo de cache (mesma linha do loading_overlay)
        try:
            self._iconWatcher = QFileSystemWatcher(self)
            cache_json = self._cache_json_path()
            if cache_json and cache_json.exists():
                self._iconWatcher.addPath(str(cache_json))
                self._iconWatcher.fileChanged.connect(self._on_theme_cache_changed)
        except Exception as e:
            print("[WARN] não consegui observar _ui_exec_settings.json:", e)

        # 3) Aplica já o ícone do tema atual
        theme_name = self._current_theme_name_safe()
        self._update_app_icon_for_theme(theme_name)

    def _on_theme_cache_changed(self, path: str) -> None:
        # Alguns editores salvam como delete+create → precisamos re-adicionar o path
        try:
            if hasattr(self, "_iconWatcher") and self._iconWatcher is not None:
                files = set(self._iconWatcher.files())
                if path not in files:
                    from pathlib import Path as _P
                    if _P(path).exists():
                        self._iconWatcher.addPath(path)
        except Exception:
            pass

        # pequena espera para o arquivo terminar de salvar e o ThemeService atualizar
        QTimer.singleShot(25, lambda: self._update_app_icon_for_theme(self._current_theme_name_safe()))

    def _current_theme_name_safe(self) -> str:
        # Preferimos o theme_service; se não existir, caímos num default.
        try:
            if hasattr(self, "theme_service"):
                for attr in ("current_theme_name", "currentThemeName", "themeName"):
                    if hasattr(self.theme_service, attr):
                        name = getattr(self.theme_service, attr)
                        if callable(name):
                            name = name()
                        if name:
                            return str(name)
        except Exception:
            pass
        return "default"

    def _slugify(self, name: str) -> str:
        import re, unicodedata
        s = unicodedata.normalize("NFKD", name or "").encode("ascii", "ignore").decode("ascii")
        s = re.sub(r"[^a-zA-Z0-9]+", "-", s).strip("-").lower()
        return s or "default"

    def _theme_slug_candidates(self, theme_name: str) -> list[str]:
        """
        Gera uma lista de possíveis slugs para o tema, incluindo o que está no JSON
        usado pelo loading_overlay (cache/_ui_exec_settings.json).
        """
        def slugify(s: str) -> str:
            import re, unicodedata
            s2 = unicodedata.normalize("NFKD", s or "").encode("ascii", "ignore").decode("ascii")
            s2 = re.sub(r"[^a-zA-Z0-9]+", "-", s2).strip("-").lower()
            return s2 or "default"

        cands: list[str] = []

        # 1) do ThemeService
        if theme_name:
            raw = str(theme_name)
            cands += [
                slugify(raw),
                raw.strip().lower().replace(" ", "-"),
                raw.strip().lower().replace(" ", "_"),
            ]

        # 2) do JSON do cache (igual ao loading_overlay)
        try:
            cj = self._cache_json_path()
            if cj and cj.exists():
                data = json.loads(cj.read_text(encoding="utf-8", errors="ignore"))
                for key in ("theme", "current_theme", "theme_key", "ui_theme", "selected_theme"):
                    v = data.get(key)
                    if isinstance(v, str):
                        cands += [
                            slugify(v),
                            v.strip().lower().replace(" ", "-"),
                            v.strip().lower().replace(" ", "_"),
                        ]
        except Exception:
            # silencioso: sem debug
            pass

        # 3) remove duplicados preservando ordem
        seen, out = set(), []
        for s in cands:
            if s and s not in seen:
                out.append(s)
                seen.add(s)
        if not out:
            out = ["default"]

        return out

    def _assets_roots(self) -> list[Path]:
        """
        Raízes onde procurar ícones:
        - settings.assets_dir / settings.icons_dir (se existirem)
        - .../app/assets (a partir do __file__)
        - .../app/app/assets (fallback)
        - cwd/assets e cwd/app/assets (úteis em dev)
        """
        roots: list[Path] = []
        try:
            if hasattr(self.settings, "assets_dir") and self.settings.assets_dir:
                roots.append(Path(self.settings.assets_dir))
        except Exception:
            pass
        try:
            if hasattr(self.settings, "icons_dir") and self.settings.icons_dir:
                roots.append(Path(self.settings.icons_dir))
        except Exception:
            pass

        base = Path(__file__).resolve().parents[2]  # .../app/
        roots.extend([base / "assets", base / "app" / "assets"])

        cwd = Path.cwd()
        roots.extend([cwd / "assets", cwd / "app" / "assets"])

        # unique preservando ordem
        seen, out = set(), []
        for r in roots:
            rp = r.resolve()
            if rp not in seen:
                out.append(rp)
                seen.add(rp)

        return out

    def _cache_json_path(self) -> Path | None:
        try:
            if hasattr(self, "settings") and hasattr(self.settings, "cache_dir"):
                p = Path(self.settings.cache_dir) / "_ui_exec_settings.json"
                return p
        except Exception:
            pass
        base = Path(__file__).resolve().parents[2]
        candidatos = [
            base / "assets" / "cache" / "_ui_exec_settings.json",
            base / "app" / "assets" / "cache" / "_ui_exec_settings.json",
        ]
        for p in candidatos:
            if p.exists():
                return p
        return candidatos[0]

    def _resolve_app_icon_path(self, theme_name: str) -> Path | None:
        slugs = self._theme_slug_candidates(theme_name)

        def name_candidates(s: str) -> list[str]:
            return [
                f"app_{s}.ico", f"app-{s}.ico", f"{s}_app.ico",
                f"{s}.ico", f"icon_{s}.ico",
                # png fallbacks
                f"app_{s}.png", f"app-{s}.png", f"{s}_app.png",
                f"{s}.png", f"icon_{s}.png",
            ]

        def dir_candidates(root: Path, s: str) -> list[Path]:
            return [
                root / "icons",
                root / "icons" / "themes",
                root / "icons" / "app",
                root,  # direto na raiz dos assets
                # pastas com o nome do tema (icons/aku/app.ico)
                root / "icons" / s,
                root / "icons" / "themes" / s,
            ]

        for root in self._assets_roots():
            for s in slugs:
                for d in dir_candidates(root, s):
                    for nm in name_candidates(s):
                        p = d / nm
                        if p.exists():
                            return p

        # último fallback: app.ico/png genérico
        for root in self._assets_roots():
            for generic in ("app.ico", "app.png", "icon.ico", "icon.png"):
                p = (root / "icons" / generic)
                if p.exists():
                    return p
                p2 = root / generic
                if p2.exists():
                    return p2

        return None

    def _apply_app_icon(self, icon_path: Path | None) -> None:
        if not icon_path:
            return
        try:
            icon = QIcon(str(icon_path))

            # 1) janela (Alt-Tab e parte da taskbar em vários SOs)
            self.setWindowIcon(icon)

            # 2) aplicação (ícone da taskbar no Windows/Linux tende a seguir este)
            try:
                QApplication.setWindowIcon(icon)
            except Exception:
                pass

            # 2.1) empurrão no próximo ciclo (ajuda no Windows teimoso)
            QTimer.singleShot(0, lambda: self.setWindowIcon(icon))

            # 3) TitleBar (sem depender do nome exato do atributo)
            for attr in ("titlebar", "topbar", "title_bar", "header", "appbar"):
                bar = getattr(self, attr, None)
                if bar and hasattr(bar, "setIcon"):
                    try:
                        bar.setIcon(icon)  # TitleBar já anima
                        break
                    except Exception:
                        pass
            else:
                # 3b) fallback: procura por children com API setIcon
                for w in self.findChildren(QWidget):
                    try:
                        if w.objectName() in ("TitleBar", "titlebar") and hasattr(w, "setIcon"):
                            w.setIcon(icon)
                            break
                    except Exception:
                        pass

        except Exception as e:
            print("[WARN] Falha ao aplicar ícone:", e)

    def _update_app_icon_for_theme(self, theme_name: str | None) -> None:
        """Resolve arquivo do ícone para o tema e aplica."""
        try:
            if not theme_name:
                theme_name = self._current_theme_name_safe()
            path = self._resolve_app_icon_path(theme_name)
            self._apply_app_icon(path)
        except Exception as e:
            print("[WARN] Falha em _update_app_icon_for_tema:", e)
