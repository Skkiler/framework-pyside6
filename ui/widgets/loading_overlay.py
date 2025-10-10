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


class LoadingOverlay(QWidget):
    def __init__(
        self,
        parent: QWidget,
        *,
        message: str = "Carregando…",
        gif_path: Optional[str] = None,
        block_input: bool = True,
        # >>> mude o padrão para "theme"
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
                    border-radius: 12px;
                }}"""
            )
        elif background_mode == "transparent":
            self._panel.setStyleSheet(
                """
                QFrame#LoadingPanel {
                    background: rgba(0,0,0,0.0);
                    border: 1px solid rgba(255,255,255,0.10);
                    border-radius: 12px;
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

    # ---------- infra ----------
    def eventFilter(self, watched, event):
        if watched is self.parent():
            et = event.type()
            if et in (QEvent.Resize, QEvent.Move, QEvent.Show):
                self._reposition()
            elif et == QEvent.Hide:
                if self.isVisible():
                    super().hide()
                if self._movie:
                    self._movie.stop()
            elif et == QEvent.ShowToParent:
                if self._active:
                    self._reposition()
                    self.raise_()
                    super().show()
                    if self._movie:
                        self._apply_scaled_size()
                        self._movie.start()
        return super().eventFilter(watched, event)

    def _reposition(self):
        """Cobre o parent por completo; centraliza painel com 1/2 da LxA do parent."""
        par = self.parentWidget()
        if not par:
            return
        r = par.rect()
        self.setGeometry(QRect(r.left(), r.top(), r.width(), r.height()))

        pw = max(220, int(r.width() * 0.5))
        ph = max(160, int(r.height() * 0.5))
        px = (r.width() - pw) // 2
        py = (r.height() - ph) // 2
        self._panel.setGeometry(QRect(px, py, pw, ph))

        self._apply_scaled_size()

    def _apply_scaled_size(self):
        """Mantém proporção do GIF: ocupa ~60% do menor lado do painel."""
        if not self._movie:
            return
        w = self._panel.width()
        h = self._panel.height()
        if w <= 0 or h <= 0:
            return
        target = max(32, int(min(w, h) * 0.60))
        self._movie.setScaledSize(QSize(target, target))
        self._gif_label.setFixedSize(target, target)

    # bloqueia somente a área do conteúdo (parent)
    def mousePressEvent(self, e):  e.accept() if self._block_input else e.ignore()
    def mouseReleaseEvent(self, e): e.accept() if self._block_input else e.ignore()
    def keyPressEvent(self, e):     e.accept() if self._block_input else e.ignore()
