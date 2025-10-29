# ui/core/app.py

from __future__ import annotations

from pathlib import Path
from typing import Optional, Iterable, Any
import json

from PySide6.QtGui import QIcon, QShortcut, QKeySequence
from PySide6.QtWidgets import QWidget, QVBoxLayout, QHBoxLayout, QApplication, QFrame, QScrollArea
from PySide6.QtCore import QFileSystemWatcher, QTimer, Qt

from .router import Router
from .settings import Settings
from .theme_service import ThemeService
from .frameless_window import FramelessWindow

from ui.services.theme_repository_json import JsonThemeRepository
from ui.widgets.topbar import TopBar
from ui.widgets.overlay_sidebar import OverlaySidePanel
from ui.widgets.push_sidebar import PushSidePanel
from ui.widgets.titlebar import TitleBar
from ui.widgets.toast import notification_bus
from ui.widgets.settings_sidebar import SettingsSidePanel

from .utils.helpers import create_layout_widget
from .utils.resource_manager import ResourceManager
from .utils.page_manager import PageManager
from .utils.paths import safe_icon
from .utils.factories import call_with_known_kwargs

from app.pages.notificacoes import NotificationCenter
from app.pages.settings import build as build_settings_page

try:
    from app import settings as S
except Exception:
    S = None


class AppShell(FramelessWindow):
    """
    Shell principal da aplicação seguindo o princípio da Responsabilidade Única (SRP).
    Esta classe coordena os componentes principais da UI.
    """

    def __init__(self, title: str, assets_dir: str, themes_dir: str, base_qss_path: str, settings: Settings):
        super().__init__()
        self.setWindowTitle(title)
        self.setObjectName("RootWindow")
        self.resize(1100, 720)
        self._page_labels = {}

        # Inicializa gerenciadores
        self.resources = ResourceManager(assets_dir)
        self.settings = settings
        self.page_manager = PageManager()

        # Router com histórico (limit 100)
        self.router = Router(history_limit=100)

        # Serviço de temas
        self.theme_service = ThemeService(
            repo=JsonThemeRepository(themes_dir),
            root=self,
            settings=self.settings,
            base_qss_path=base_qss_path,
            animate_ms_default=450,
            cache_dir=self.resources.cache_dir,
        )

        # Constrói a UI
        self._build_ui(title)

    def register_pages(self, specs: Iterable[tuple[str, Any]], *, task_runner=None) -> None:
        """
        Registra páginas na aplicação.
        
        Args:
            specs: Iterável de tuplas (page_id, factory)
            task_runner: Runner opcional para tarefas assíncronas
        """
        dependencies = {"theme_service": self.theme_service}
        if task_runner:
            dependencies["task_runner"] = task_runner

        for page_id, factory in specs:
            self.page_manager.register(page_id, factory, **dependencies)
            
    def _go(self, page_id: str, **kwargs: Any) -> None:
        """Navega para uma página."""
        if not self.page_manager.has_page(page_id):
            return
            
        page = self.page_manager.create(page_id, **kwargs)
        if page:
            self.router.push(page)
            
    def _build_ui(self, title: str) -> None:
        """Constrói os elementos principais da UI."""
        # Widget central
        central = self._build_central(title)
        self.setCentralWidget(central)

        # Conecta eventos
        self._wire_router_events()
        self._setup_theme_icon_sync()

        # Sidebar de navegação
        self.sidebar = OverlaySidePanel(
            parent=central,
            use_scrim=True,
            close_on_scrim=True,
            close_on_select=True
        )
        self.sidebar.pageSelected.connect(self._go)

        # Sidebar de configurações
        self._settings_widget = build_settings_page(theme_service=self.theme_service)
        self.settings_panel = SettingsSidePanel(
            parent=central,
            content=self._settings_widget,
            use_scrim=True,
            close_on_scrim=True,
        )

        # Centro de Notificações
        self._build_notification_center(central)

    def _build_central(self, title: str) -> QWidget:
        """Constrói o widget central com layout."""
        # Container principal
        container = create_layout_widget(QVBoxLayout, parent=self)
        
        # Barra de título
        titlebar = TitleBar(title, parent=container)
        titlebar.minimizeClicked.connect(self.showMinimized)
        titlebar.maximizeClicked.connect(self.toggleMaximized)
        titlebar.closeClicked.connect(self.close)
        container.layout().addWidget(titlebar)

        # Container de conteúdo com layout horizontal
        content = create_layout_widget(QHBoxLayout, parent=container)
        content.layout().setContentsMargins(0, 0, 0, 0)
        container.layout().addWidget(content)

        # Área principal de conteúdo
        self._central_widget = QWidget()
        self._central_widget.setObjectName("CentralWidget")
        content.layout().addWidget(self._central_widget)

        self._content_hbox = content.layout()
        return container

    def _build_notification_center(self, parent: QWidget) -> None:
        """Constrói o centro de notificações."""
        self._notif_center = NotificationCenter(self)
        self._notif_panel = PushSidePanel(
            parent=parent,
            content=self._notif_center,
            title="Notificações",
            width=360,
        )

        if self._content_hbox is not None:
            self._content_hbox.addWidget(self._notif_panel)
        else:
            print("[WARN] Layout _content_hbox não existe, notificações não visíveis!")

        # Conexões TopBar ↔ Notificações
        self.topbar.openNotificationsRequested.connect(self._notif_panel.toggle)
        # “Limpar” pela TopBar → tenta limpar concluídas pela API da página; fallback: limpar tudo via bus
        self.topbar.clearNotificationsRequested.connect(self._clear_notifications_from_topbar)

        # Atualiza badge conforme entradas mudam
        if hasattr(self._notif_center, "countChanged"):
            self._notif_center.countChanged.connect(self.topbar.setUnreadCountRequested.emit)

    # ---------------------------------------------------------
    #  Montagem da UI
    # ---------------------------------------------------------
    def _build_central(self, title: str) -> QWidget:
        central = QWidget()
        central.setProperty("role", "content")
        self._central_widget = central  # guardamos para o push panel

        root_v = QVBoxLayout(central)
        root_v.setContentsMargins(0, 0, 0, 0)
        root_v.setSpacing(0)

        # TitleBar (janela principal)
        icon_path = self.resources.assets_dir / "icons" / "app" / "app.ico"
        icon_ref = safe_icon(icon_path)
        self.titlebar = TitleBar(title, self, icon=icon_ref)
        root_v.addWidget(self.titlebar)
        self.connect_titlebar(self.titlebar)
        self.titlebar.settingsRequested.connect(self._toggle_settings_panel)

        # Topbar (inicialmente sem título; será atualizado conforme página)
        self.topbar = TopBar(onHamburgerClick=self._toggle_sidebar, title=None)
        self.topbar.breadcrumbClicked.connect(self._go)
        # Clique no botão de “mais” abre o centro de notificações também
        try:
            self.topbar.btn_more.clicked.connect(self.topbar.openNotificationsRequested.emit)  # type: ignore[attr-defined]
        except Exception:
            pass
        root_v.addWidget(self.topbar)

        # Área da Toolbar da página (opcional)
        self.toolbar_area = QFrame(central)
        self.toolbar_area.setObjectName("PageToolbarArea")
        self.toolbar_area.setAttribute(Qt.WA_StyledBackground, True)
        self.toolbar_area.hide()
        tb_lay = QHBoxLayout(self.toolbar_area)
        tb_lay.setContentsMargins(0, 0, 0, 0)
        tb_lay.setSpacing(0)
        self._toolbar_layout = tb_lay
        root_v.addWidget(self.toolbar_area)

        # Router (conteúdo principal) + espaço para o push sidebar à direita
        content = QHBoxLayout()
        content.setContentsMargins(0, 0, 0, 0)
        content.setSpacing(0)
        root_v.addLayout(content)
        content.addWidget(self.router)
        self._content_hbox = content  # guardamos para inserir o PushSidePanel depois

        # --- Atalhos globais ---
        try:
            sc_back = QShortcut(QKeySequence("Alt+Left"), self)
            sc_back.activated.connect(self.router.go_back)
            sc_fwd = QShortcut(QKeySequence("Alt+Right"), self)
            sc_fwd.activated.connect(self.router.go_forward)
        except Exception as e:
            print("[WARN] atalhos back/forward falharam:", e)

        try:
            sc_qk = QShortcut(QKeySequence("Ctrl+K"), self)
            sc_qk.activated.connect(self._open_quick_open)
        except Exception as e:
            print("[WARN] atalho Ctrl+K falhou:", e)

        return central

    # ---------------------------------------------------------
    #  Registro de páginas
    # ---------------------------------------------------------
    def register_page(self, route, widget, label=None, show_in_sidebar=True):
        """Registra uma única página no roteador e sidebar."""
        self.router.register(route, widget)
        if show_in_sidebar:
            self.sidebar.add_page(route, label or route)

        # Guarda o label (para exibir na TopBar e breadcrumb)
        self._page_labels[route] = label or route

    def register_pages(self, specs: Iterable, *, task_runner=None):
        """Registra páginas a partir de uma lista de PageSpecs."""
        self._all_pages = list(specs)
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
        """Aplica o tema e navega para a primeira página (respeitando última rota persistida)."""
        chosen = self.theme_service.load_selected_from_settings() or default_theme
        avail = self.theme_service.available()
        if avail:
            self.theme_service.apply(
                chosen if chosen in avail else avail[0],
                animate=False,
                persist=False,
            )

        try:
            force_home = bool(self.settings.get("nav.always_open_home", False))
        except Exception:
            force_home = False

        # Tenta restaurar última rota persistida
        if not force_home:
            try:
                last_route = self.settings.get("nav.last_route")
                if isinstance(last_route, str) and last_route in self.router._pages:
                    first_route = last_route
            except Exception:
                pass

        # Navega para a página inicial/recuperada
        self.router.go(first_route)

        # Define o título + breadcrumb na TopBar e persiste last_route
        self._update_topbar_for_route(first_route)
        try:
            self.settings.set("nav.last_route", first_route)
        except Exception:
            pass

        # ----- Geometria inicial -----
        try:
            start_max = bool(self.settings.get("window.start_maximized", False))
        except Exception:
            start_max = False

        try:
            ag = self._available_rect() if hasattr(self, "_available_rect") else self.screen().availableGeometry()
        except Exception:
            from PySide6.QtCore import QRect
            ag = QRect(0, 0, 1280, 720)

        if start_max:
            # Maximiza sem animação e atualiza TitleBars
            self.setGeometry(ag)
            self._is_maximized = True
            for tb in getattr(self, "_titlebars", []) or []:
                if hasattr(tb, "setMaximized"):
                    try:
                        tb.setMaximized(True)
                    except Exception:
                        pass
        else:
            # 1/4 da área de tela (metade de cada dimensão), centralizado
            w = max(320, int(ag.width() * 0.5))
            h = max(200, int(ag.height() * 0.5))
            x = ag.center().x() - w // 2
            y = ag.center().y() - h // 2
            self.setGeometry(x, y, w, h)

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
        """Troca de rota e atualiza TopBar/breadcrumb + persistência."""
        self.router.go(route)
        self._update_topbar_for_route(route)
        try:
            self.settings.set("nav.last_route", route)
        except Exception:
            pass

    # ---------------------- Router wiring / Topbar helpers ----------------------

    def _wire_router_events(self):
        """Conecta eventos do Router para manter TopBar e persistência em sincronia."""
        try:
            self.router.routeChanged.connect(self._on_route_changed)
        except Exception as e:
            print("[WARN] não consegui conectar routeChanged:", e)

    def _on_route_changed(self, path: str, params: dict):
        """Atualiza UI/persistência quando a rota muda (back/forward/go)."""
        self._update_topbar_for_route(path)
        self._update_toolbar_for_current_page()
        try:
            self.settings.set("nav.last_route", path)
        except Exception:
            pass

    def _update_topbar_for_route(self, path: str):
        """Atualiza título e breadcrumb simples na TopBar."""
        # Título: label registrado para a rota (fallback = último segmento humanizado)
        label = self._page_labels.get(path)
        if not label:
            label = path.split("/")[-1].replace("-", " ").title()
        if hasattr(self.topbar, "set_title"):
            self.topbar.set_title(label)

        # Breadcrumb: partes acumuladas
        parts = []
        acc = []
        for seg in (path or "").split("/"):
            if not seg:
                continue
            acc.append(seg)
            acc_path = "/".join(acc)
            seg_label = self._page_labels.get(acc_path) or seg.replace("-", " ").title()
            parts.append((seg_label, acc_path))

        if hasattr(self.topbar, "set_breadcrumb"):
            self.topbar.set_breadcrumb(parts if len(parts) > 1 else None)

    # ---------------------- Toolbar por página ----------------------
    def set_page_toolbar(self, toolbar: QWidget | None):
        try:
            lay = self._toolbar_layout
            # limpa widgets antigos
            while lay.count():
                item = lay.takeAt(0)
                w = item.widget()
                if w:
                    w.setParent(None)
            if toolbar is not None:
                lay.addWidget(toolbar)
                self.toolbar_area.show()
            else:
                self.toolbar_area.hide()
        except Exception as e:
            print("[WARN] set_page_toolbar falhou:", e)

    def _update_toolbar_for_current_page(self):
        try:
            page = self.router.currentWidget()
            # Se a página estiver embrulhada por um QScrollArea (wrapper global),
            # desce até o widget real da página para buscar build_toolbar/toolbar.
            if isinstance(page, QScrollArea):
                container = page.widget()
                if container and hasattr(container, "layout") and container.layout() is not None:
                    lay = container.layout()
                    # tenta pegar o primeiro widget do layout (página real)
                    for i in range(lay.count()):
                        it = lay.itemAt(i)
                        if it and it.widget():
                            page = it.widget()
                            break
            tb = None
            if page is not None:
                # Se a página expõe build_toolbar() retornando um QWidget, usamos
                build = getattr(page, "build_toolbar", None)
                if callable(build):
                    tb = build()
                else:
                    # ou aceita atributo 'toolbar' pré-montado
                    tb = getattr(page, "toolbar", None)
                self.set_page_toolbar(tb if isinstance(tb, QWidget) else None)
        except Exception as e:
            print("[WARN] _update_toolbar_for_current_page:", e)

    def _open_quick_open(self):
        """Abre Quick Open (Ctrl+K) frameless, modal e estilizado pelo base.qss."""
        try:
            from ui.dialogs.quick_open import QuickOpenDialog
            pages = getattr(self, "_all_pages", []) or []
            dlg = QuickOpenDialog(pages, parent=self)
            dlg.routeChosen.connect(self._go)
            dlg.exec()  # modal real com animação (FramelessDialog)
        except Exception as e:
            print("[WARN] QuickOpen indisponível:", e)

    # ---------------------- Hooks de animação pesada (tema) ----------------------
    def _begin_heavy_anim(self) -> None:
        """Sinaliza animação pesada: suspende cosméticos (toolbar/menus) e hovers."""
        try:
            setattr(self, "_is_heavy_anim", True)
        except Exception:
            pass
        # Toolbar por página: pausa hover/timers e desabilita updates
        try:
            if hasattr(self, "toolbar_area") and self.toolbar_area is not None:
                self.toolbar_area.setUpdatesEnabled(False)
                # tenta localizar widget toolbar no layout
                tb = None
                try:
                    lay = getattr(self, "_toolbar_layout", None)
                    if lay is not None:
                        for i in range(lay.count()):
                            it = lay.itemAt(i)
                            if it and it.widget():
                                tb = it.widget(); break
                except Exception:
                    tb = None
                if tb is not None and hasattr(tb, "pause_hover"):
                    try:
                        tb.pause_hover(True)  # type: ignore[attr-defined]
                    except Exception:
                        pass
            # Também reduz updates visuais na TitleBar (cosmético)
            if hasattr(self, "titlebar") and self.titlebar is not None:
                try:
                    self.titlebar.setUpdatesEnabled(False)
                except Exception:
                    pass
        except Exception:
            pass

    def _end_heavy_anim(self) -> None:
        """Retoma estado após animação pesada."""
        try:
            setattr(self, "_is_heavy_anim", False)
        except Exception:
            pass
        try:
            if hasattr(self, "toolbar_area") and self.toolbar_area is not None:
                # tenta localizar toolbar para retomar hover
                tb = None
                try:
                    lay = getattr(self, "_toolbar_layout", None)
                    if lay is not None:
                        for i in range(lay.count()):
                            it = lay.itemAt(i)
                            if it and it.widget():
                                tb = it.widget(); break
                except Exception:
                    tb = None
                if tb is not None and hasattr(tb, "pause_hover"):
                    try:
                        tb.pause_hover(False)  # type: ignore[attr-defined]
                    except Exception:
                        pass
                # reabilita updates da área visual
                self.toolbar_area.setUpdatesEnabled(True)
            if hasattr(self, "titlebar") and self.titlebar is not None:
                try:
                    self.titlebar.setUpdatesEnabled(True)
                except Exception:
                    pass
        except Exception:
            pass

    # ---------------------- Notificações: helpers ----------------------

    def _clear_notifications_from_topbar(self):
        try:
            if hasattr(self._notif_center, "clear_finished_public"):
                self._notif_center.clear_finished_public()  # type: ignore[attr-defined]
            else:
                notification_bus().removeEntry.emit("__all__")
        except Exception:
            notification_bus().removeEntry.emit("__all__")

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
            # Evita I/O/varreduras durante a interpolação de tema
            if getattr(self, "_is_heavy_anim", False):
                # reagenda para depois (evita loop: flag será baixada no finished())
                QTimer.singleShot(60, lambda: self._update_app_icon_for_theme(theme_name))
                return

            if not theme_name:
                theme_name = self._current_theme_name_safe()
            path = self._resolve_app_icon_path(theme_name)
            self._apply_app_icon(path)
        except Exception as e:
            print("[WARN] Falha em _update_app_icon_for_tema:", e)
