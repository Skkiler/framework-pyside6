# ui/widgets/loading_overlay.py

from __future__ import annotations
from pathlib import Path
from typing import Optional, Tuple

from PySide6.QtCore import Qt, QEvent, QRect, QSize, QFileSystemWatcher
from PySide6.QtGui import QMovie
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy, QFrame

# --- Integrar com app.settings para resolver caminhos de assets ---
try:
    from app import settings as S
except Exception:
    S = None


def _default_gif_path() -> Optional[str]:
    # Tema via helpers do settings (você centralizou aí) → fallback DEFAULT_THEME
    theme = None
    try:
        if S and hasattr(S, "_read_exec_settings_theme"):
            theme = S._read_exec_settings_theme()
    except Exception:
        theme = None
    if (not theme) and S and getattr(S, "DEFAULT_THEME", None):
        theme = str(S.DEFAULT_THEME)

    # Slug via helper do settings (com fallback se não existir)
    try:
        slug = S._slugify_theme(theme) if (S and theme) else ""
    except Exception:
        slug = (str(theme).strip().lower().replace(" ", "-")) if theme else ""

    # 1) Nomes candidatos priorizando o tema
    names = []
    if slug:
        names += [
            f"loading_{slug}.gif",   # loading_aku.gif / loading-aku-dark.gif (se o tema já veio com '-')
            f"loading-{slug}.gif",   # loading-aku.gif
            f"{slug}_loading.gif",   # aku_loading.gif
        ]
    names.append("loading.gif")       # fallback genérico

    # 2) Diretórios candidatos (prioridade: settings → compat)
    candidates = []

    if S:
        icons_dir   = getattr(S, "ICONS_DIR", None)
        assets_dir  = getattr(S, "ASSETS_DIR", None)
        ui_dir      = getattr(S, "UI_DIR", None)

        if icons_dir:
            candidates += [(icons_dir / n) for n in names]
        if assets_dir:
            candidates += [(assets_dir / "icons" / n) for n in names]
        if ui_dir:
            candidates += [(ui_dir / "assets" / "icons" / n) for n in names]

    # Fallbacks compatíveis com o código antigo (não quebrar dev)
    here = Path(__file__).resolve()
    repo = here.parents[2] if len(here.parents) >= 3 else here.parent
    candidates += [
        *(repo / "ui" / "assets" / "icons" / n for n in names),
        *(repo / "assets" / "icons" / n for n in names),
    ]

    # 3) Retorna o primeiro que existir
    for p in candidates:
        try:
            if p.exists():
                return str(p)
        except Exception:
            continue

    return None

# -------- Compat de eventos (Qt/PySide variam por versão) --------------------
# Constrói uma tupla apenas com os tipos que EXISTEM no runtime atual
def _opt_events(*names: str) -> tuple:
    present = []
    for n in names:
        v = getattr(QEvent, n, None)
        if v is not None:
            present.append(v)
    return tuple(present)


# Eventos “comuns” que sempre existem
_BASE_LAYOUT_EVENTS = (
    QEvent.Resize, QEvent.Move, QEvent.Show, QEvent.ShowToParent, QEvent.WindowStateChange
)

# Eventos opcionais (se existirem na sua versão, tratamos; senão, ignoramos)
_DPI_SCREEN_EVENTS = _opt_events(
    "ScreenChangeInternal",         # Qt >= 5.14/6.x
    "DevicePixelRatioChange",       # algumas versões
    "ApplicationFontChange",        # fallback: pode disparar realayout
    "FontChange",                   # idem
    "PaletteChange",                # temas podem provocar reflow
    "HighDpiScaleFactorChange",     # algumas builds Qt6
)

_THEME_CHANGE_EVENTS = _opt_events(
    "PaletteChange",
    "ApplicationPaletteChange",
    "StyleChange",
)


class LoadingOverlay(QWidget):
    def __init__(
        self,
        parent: QWidget,
        *,
        message: str = "Carregando…",
        gif_path: Optional[str] = None,
        block_input: bool = True,
        background_mode: str = "theme",                # "theme" | "transparent" | "gradient"
        gradient_colors: Optional[Tuple[str, str]] = None,
    ):
        super().__init__(parent)
        self.setObjectName("LoadingOverlay")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.Widget | Qt.FramelessWindowHint)

        self._movie: Optional[QMovie] = None
        self._block_input = bool(block_input)
        self._active = False
        self._gif_path_str: Optional[str] = None
        self._last_seen_theme: Optional[str] = None  # tema visto na última resolução

        # Guarda refs e instala filtros no parent e na janela top-level
        self._parent = parent
        if self._parent:
            self._parent.installEventFilter(self)
        top = self._parent.window() if self._parent else None
        if top and top is not self._parent:
            top.installEventFilter(self)

        self._panel = QFrame(self)
        self._panel.setObjectName("LoadingPanel")
        self._panel.setAttribute(Qt.WA_StyledBackground, True)

        lay = QVBoxLayout(self._panel)
        lay.setContentsMargins(18, 18, 18, 18)
        lay.setSpacing(8)
        lay.setAlignment(Qt.AlignCenter)

        self._gif_label = QLabel(self._panel)
        self._gif_label.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
        self._gif_label.setAlignment(Qt.AlignCenter)

        self._text = QLabel(message, self._panel)
        self._text.setWordWrap(True)
        self._text.setAlignment(Qt.AlignCenter)
        self._text.setStyleSheet("")  # não forçar cor aqui; deixa o tema decidir

        lay.addWidget(self._gif_label, 0, Qt.AlignCenter)
        lay.addWidget(self._text, 0, Qt.AlignCenter)

        # Inicializa movie com caminho resolvido (ou ícone fallback ⏳)
        path = gif_path or _default_gif_path()
        if path and Path(path).exists():
            self._gif_path_str = path
            self._movie = QMovie(path)
            self._gif_label.setMovie(self._movie)
        else:
            self._gif_label.setText("⏳")
            self._gif_label.setStyleSheet("font-size: 28px;")

        # Overlay sempre transparente (apenas intercepta eventos);
        # o painel é que recebe a cor (via tema ou inline, se solicitado)
        self.setStyleSheet("QWidget#LoadingOverlay { background: transparent; }")

        # <<< só aplica estilo inline ao painel se NÃO for "theme"
        if background_mode == "gradient" and gradient_colors and all(isinstance(c, str) and c.startswith("#") for c in gradient_colors):
            bg0, bg1 = gradient_colors
            self._panel.setStyleSheet(
                f"""
                QFrame#LoadingPanel {{
                    background: qlineargradient(x1:0,y1:0,x2:0,y2:1, stop:0 {bg0}, stop:1 {bg1});
                    border: 1px solid rgba(255,255,255,0.10);
                    border-radius: 24px;
                }}"""
            )
        elif background_mode == "transparent":
            self._panel.setStyleSheet(
                """
                QFrame#LoadingPanel {
                    background: rgba(0,0,0,0.0);
                    border: 1px solid rgba(255,255,255,0.10);
                    border-radius: 24px;
                }"""
            )
        else:
            # "theme": nenhum estilo inline -> base.qss controla
            self._panel.setStyleSheet("")

        # ---- Watcher para mudanças no arquivo de exec (_ui_exec_settings.json)
        self._watcher: Optional[QFileSystemWatcher] = None
        try:
            if S and getattr(S, "CACHE_DIR", None):
                json_path = (S.CACHE_DIR / "_ui_exec_settings.json")
                if json_path.exists():
                    self._watcher = QFileSystemWatcher([str(json_path)])
                    self._watcher.fileChanged.connect(self._on_exec_file_changed)
        except Exception:
            self._watcher = None

    # ---------- API ----------
    def show(self, message: Optional[str] = None):
        if message is not None:
            self._text.setText(message)
        self._active = True
        # Garante que, ao mostrar, já esteja com o GIF do tema atual
        self._maybe_reload_gif_for_theme()
        self._reposition()
        self.raise_()
        super().show()
        if self._movie:
            self._apply_scaled_size()
            self._movie.start()

    def hide(self):
        self._active = False
        if self._movie:
            self._movie.stop()
        super().hide()

    # ---------- Qt events ----------
    def showEvent(self, e):
        super().showEvent(e)
        # Revalida o GIF no primeiro show (caso tema tenha mudado antes)
        self._maybe_reload_gif_for_theme()
        self._reposition()
        if self._movie:
            self._apply_scaled_size()
            self._movie.start()

    def resizeEvent(self, e):
        super().resizeEvent(e)
        self._reposition_panel_only()

    # ---------- infra ----------
    def eventFilter(self, watched, event):
        parent = self.parent()
        top = parent.window() if parent else None

        # Reage a mudanças do parent OU da janela top-level
        if watched is parent or watched is top:
            et = event.type()

            # Parent/janela foram escondidos -> esconda overlay (mantém _active como está)
            if et == QEvent.Hide:
                if self.isVisible():
                    super().hide()
                if self._movie:
                    self._movie.stop()
                return super().eventFilter(watched, event)

            # Layout/state/screen changes
            if et in _BASE_LAYOUT_EVENTS or et in _DPI_SCREEN_EVENTS or et in _THEME_CHANGE_EVENTS:
                if self._active:
                    # Se o parent acabou de aparecer/voltou ao stack, reexiba o overlay
                    if et in (QEvent.Show, QEvent.ShowToParent) and not self.isVisible():
                        super().show()
                        self.raise_()
                        if self._movie:
                            self._movie.start()

                    # Sempre reposiciona quando ativo
                    self._reposition()
                    self.raise_()
                    if self._movie:
                        self._apply_scaled_size()
                        # Em mudanças de DPI/tela, garanta que o GIF reescale
                        if et in _DPI_SCREEN_EVENTS:
                            self._movie.start()

                # Em eventos ligados a mudança de paleta/tema/estilo → recarrega GIF se mudou
                if et in _THEME_CHANGE_EVENTS:
                    self._maybe_reload_gif_for_theme()

        return super().eventFilter(watched, event)

    def _reposition(self):
        """Cobre o parent por completo; centraliza painel com 1/2 da LxA do parent."""
        par = self.parentWidget()
        if not par:
            return
        r = par.rect()
        self.setGeometry(QRect(r.left(), r.top(), r.width(), r.height()))
        self._reposition_panel_only()
        self._apply_scaled_size()
        self._reposition_panel_only()

    def _reposition_panel_only(self):
        """Reposiciona somente o painel com base no tamanho atual do overlay."""
        r = self.rect()
        if r.isNull():
            return

        side = self._ideal_panel_side()
        px = (r.width() - side) // 2
        py = (r.height() - side) // 2
        self._panel.setGeometry(QRect(px, py, side, side))

    def _apply_scaled_size(self):
        """Mantém proporção do GIF: ocupa ~60% do menor lado do painel."""
        if not self._movie:
            return
        side = min(self._panel.width(), self._panel.height())
        if side <= 0:
            return

        # Aumenta a proporção do GIF (de 0.48 → 0.65)
        target = int(side * 0.65)
        target = max(64, min(target, 256))  # aumenta limites mínimo/máximo
        self._movie.setScaledSize(QSize(target, target))
        self._gif_label.setFixedSize(target, target)

        lay = self._panel.layout()
        if lay:
            lay.activate()

    def _ideal_panel_side(self) -> int:
        par = self.parentWidget()
        if not par:
            return 240

        pr = par.rect()
        if pr.isNull():
            return 240

        cap = int(min(pr.width(), pr.height()) * 0.56)
        cap = max(cap, 160)  # nunca cair demais se o parent for pequeno

        hint_w, hint_h = self._content_hint(max_text_width=int(min(pr.width(), pr.height()) * 0.42))

        base = max(hint_w, hint_h)
        side = base + 8

        side = max(140, side)
        side = min(cap, side)
        return side

    def _content_hint(self, max_text_width: int = 280) -> Tuple[int, int]:
        self._text.setWordWrap(True)
        self._text.setMaximumWidth(max(180, max_text_width))

        if self._movie:
            side_guess = max(48, min(int(max_text_width * 0.5), 160))
            self._movie.setScaledSize(QSize(side_guess, side_guess))
            self._gif_label.setFixedSize(side_guess, side_guess)

        lay = self._panel.layout()
        if lay:
            lay.activate()
            hint = lay.sizeHint()
            return hint.width(), hint.height()

        return 220, 160

    # bloqueia somente a área do conteúdo (parent)
    def mousePressEvent(self, e):
        e.accept() if self._block_input else e.ignore()

    def mouseReleaseEvent(self, e):
        e.accept() if self._block_input else e.ignore()

    def keyPressEvent(self, e):
        e.accept() if self._block_input else e.ignore()

    # ---------- Tema / Watcher ----------
    def _current_theme(self) -> str:
        """Tema atual via helpers do settings; fallback DEFAULT_THEME."""
        try:
            if S and hasattr(S, "_read_exec_settings_theme"):
                t = S._read_exec_settings_theme()
                if isinstance(t, str) and t.strip():
                    return t.strip()
        except Exception:
            pass
        return (getattr(S, "DEFAULT_THEME", "") or "") if S else ""

    def _maybe_reload_gif_for_theme(self):
        """
        Se o tema mudou (ou o path do GIF mudou), recarrega o QMovie.
        Chamada em showEvent, eventos de paleta/estilo e quando o JSON muda.
        """
        try:
            current_theme = self._current_theme()
            # Atualiza last_seen para evitar recarregar à toa
            theme_changed = (current_theme != self._last_seen_theme)
            new_path = _default_gif_path()
            path_changed = (new_path != self._gif_path_str)

            if not theme_changed and not path_changed:
                return

            self._last_seen_theme = current_theme
            self._gif_path_str = new_path

            if new_path and Path(new_path).exists():
                new_movie = QMovie(new_path)
                self._movie = new_movie
                self._gif_label.setMovie(self._movie)
                if self._active:
                    self._apply_scaled_size()
                    self._movie.start()
            else:
                # fallback: sem GIF
                self._gif_label.setMovie(None)
                self._movie = None
                self._gif_label.setText("⏳")
                self._gif_label.setStyleSheet("font-size: 28px;")
        except Exception:
            # manter o overlay funcional mesmo se falhar o reload
            pass

    def _on_exec_file_changed(self, changed_path: str):

        try:
            p = Path(changed_path)
            if p.exists() and self._watcher:
                # Garante que o caminho esteja sendo observado (alguns editores recriam o arquivo)
                watched = set(self._watcher.files())
                if str(p) not in watched:
                    try:
                        self._watcher.addPath(str(p))
                    except Exception:
                        pass
        except Exception:
            pass
        # Recarrega o GIF conforme o novo tema
        self._maybe_reload_gif_for_theme()
