# ui/widgets/loading_overlay.py

from __future__ import annotations
from pathlib import Path
from typing import Optional, Tuple

from PySide6.QtCore import Qt, QEvent, QRect, QSize
from PySide6.QtGui import QMovie
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QSizePolicy, QFrame


def _default_gif_path() -> Optional[str]:
    here = Path(__file__).resolve()
    repo = here.parents[2]
    ui_icons = repo / "ui" / "assets" / "icons" / "loading.gif"
    root_icons = repo / "assets" / "icons" / "loading.gif"
    if ui_icons.exists(): return str(ui_icons)
    if root_icons.exists(): return str(root_icons)
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

        path = gif_path or _default_gif_path()
        if path and Path(path).exists():
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

    # ---------- API ----------
    def show(self, message: Optional[str] = None):
        if message is not None:
            self._text.setText(message)
        self._active = True
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
            if et in _BASE_LAYOUT_EVENTS or et in _DPI_SCREEN_EVENTS:
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
    def mousePressEvent(self, e):  e.accept() if self._block_input else e.ignore()
    def mouseReleaseEvent(self, e): e.accept() if self._block_input else e.ignore()
    def keyPressEvent(self, e):     e.accept() if self._block_input else e.ignore()
