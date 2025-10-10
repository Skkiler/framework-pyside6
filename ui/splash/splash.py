# ui/splash/splash.py

from __future__ import annotations
from pathlib import Path
from typing import Optional, Callable

from PySide6.QtCore import Qt, QTimer, QEasingCurve, QPropertyAnimation, QRect, QSize
from PySide6.QtGui import QPixmap, QMovie, QFont, QPainter
from PySide6.QtWidgets import QWidget, QLabel, QVBoxLayout, QGraphicsOpacityEffect, QApplication


class Splash(QWidget):

    def __init__(
        self,
        assets_icons_dir: str | Path,
        title_text: Optional[str] = None,
        hold_ms: int = 1200,
        fade_in_ms: int = 260,
        fade_out_ms: int = 300,
        gif_loops: int = 1,
        gif_speed: int = 100,
    ):
        super().__init__(None)

        # Janela transparente: só imagem/texto.
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.SplashScreen | Qt.WindowStaysOnTopHint)
        self.setStyleSheet("background: transparent;")

        self._assets = Path(assets_icons_dir)
        self._title_text = title_text
        self._hold_ms = hold_ms
        self._fade_in_ms = fade_in_ms
        self._fade_out_ms = fade_out_ms
        self._gif_loops = gif_loops
        self._gif_speed = gif_speed

        self._after: Optional[Callable[[], None]] = None
        self._fade_anim: Optional[QPropertyAnimation] = None  # manter referência

        # Layout mínimo
        self._img = QLabel(self)
        self._img.setAlignment(Qt.AlignCenter)
        self._img.setStyleSheet("background: transparent;")

        self._title = QLabel(self)
        self._title.setAlignment(Qt.AlignCenter)
        self._title.setStyleSheet("background: transparent;")
        if title_text:
            f = QFont(); f.setPointSize(11); f.setBold(True)
            self._title.setFont(f)

        lay = QVBoxLayout(self)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(6)
        lay.addWidget(self._img, 1)
        if title_text:
            lay.addWidget(self._title, 0)

        lay.setAlignment(self._img, Qt.AlignCenter)
        if title_text:
            lay.setAlignment(self._title, Qt.AlignHCenter)

        # Opacidade inicial 0 para o fade
        eff = QGraphicsOpacityEffect(self)
        eff.setOpacity(0.0)
        self.setGraphicsEffect(eff)
        self._opacity = eff

        # Detecta mídia (GIF tem prioridade)
        png = self._assets / "splash.png"
        gif = self._assets / "splash.gif"
        self._is_gif = gif.exists()
        self._movie: Optional[QMovie] = None
        self._fit_applied = False

        # Dimensiona janela (1/4 da tela) e centraliza
        self._apply_target_geometry()

        # Carrega
        if self._is_gif:
            self._setup_gif(gif)
        elif png.exists():
            self._setup_png(png)
        else:
            pm = QPixmap(360, 220); pm.fill(Qt.black)
            self._img.setPixmap(self._scaled_pixmap(pm))
            if self._title_text:
                self._title.setText(self._title_text)

    # ---------- setups ----------
    def _setup_png(self, path: Path):
        pm = QPixmap(str(path))
        self._img.setPixmap(self._scaled_pixmap(pm))
        if self._title_text:
            self._title.setText(self._title_text)

    def _setup_gif(self, path: Path):
        mv = QMovie(str(path))
        mv.setCacheMode(QMovie.CacheAll)
        mv.setSpeed(self._gif_speed)

        self._movie = mv
        if self._title_text:
            self._title.setText(self._title_text)

        self._fit_applied = False
        self._loops_done = 0
        self._last_frame = -1
        self._fade_started = False
        self._fixed_size: QSize | None = None

        def _apply_fit_once(idx: int):
            if self._fit_applied:
                return
            fr = self._movie.frameRect()
            src_w, src_h = fr.width(), fr.height()
            if src_w > 0 and src_h > 0:
                max_sz = self._available_image_size()
                dst_w, dst_h = self._fit_size(src_w, src_h, max_sz.width(), max_sz.height())
                self._fixed_size = QSize(dst_w, dst_h)
                self._img.setFixedSize(self._fixed_size)
                self._fit_applied = True

        def _render_frame(idx: int):
            if not self._fit_applied:
                _apply_fit_once(idx)
                if not self._fit_applied:
                    return

            canvas = QPixmap(self._fixed_size)
            canvas.fill(Qt.transparent)

            frame_pm = self._movie.currentPixmap()
            if not frame_pm.isNull():
                scaled = frame_pm.scaled(self._fixed_size, Qt.KeepAspectRatio, Qt.SmoothTransformation)
                x = (self._fixed_size.width() - scaled.width()) // 2
                y = (self._fixed_size.height() - scaled.height()) // 2
                painter = QPainter(canvas)
                painter.drawPixmap(x, y, scaled)
                painter.end()

            self._img.setPixmap(canvas)

            total = self._movie.frameCount()
            if total > 0:
                if self._last_frame == total - 1 and idx == 0:
                    self._loops_done += 1
                    if self._gif_loops > 0 and self._loops_done >= self._gif_loops and not self._fade_started:
                        self._fade_started = True
                        self._fade_out()
            self._last_frame = idx

        self._movie.frameChanged.connect(_render_frame)

    # ---------- public API ----------
    def run(self, after: Callable[[], None]):
        """Mostra, faz fade-in; PNG espera hold_ms; GIF respeita gif_loops; depois fade-out -> after()."""
        self._after = after
        self.show()
        self._fade_in()

        if self._is_gif and self._movie:
            self._movie.start()
        else:
            QTimer.singleShot(self._hold_ms, self._fade_out)

    # ---------- anim ----------
    def _fade_in(self):
        self._fade_anim = self._anim(0.0, 1.0, self._fade_in_ms)
        self._fade_anim.start()

    def _fade_out(self):
        self._fade_anim = self._anim(1.0, 0.0, self._fade_out_ms)
        self._fade_anim.finished.connect(self._finish)
        self._fade_anim.start()

    def _anim(self, start: float, end: float, ms: int) -> QPropertyAnimation:
        anim = QPropertyAnimation(self._opacity, b"opacity", self)
        anim.setDuration(ms)
        anim.setStartValue(start)
        anim.setEndValue(end)
        anim.setEasingCurve(QEasingCurve.OutCubic if end > start else QEasingCurve.InCubic)
        return anim

    def _finish(self):
        if self._movie and self._movie.state() == QMovie.Running:
            self._movie.stop()
        if callable(self._after):
            self._after()
        self.close()

    # ---------- sizing & helpers ----------
    def _apply_target_geometry(self):
        """Define a janela para 1/4 da tela (1/2 W x 1/2 H) e centraliza."""
        scr = QApplication.primaryScreen().availableGeometry()
        target_w = max(360, int(scr.width() * 0.5))   # metade da largura
        target_h = max(220, int(scr.height() * 0.5))  # metade da altura
        x = scr.x() + (scr.width() - target_w) // 2
        y = scr.y() + (scr.height() - target_h) // 2
        self.setGeometry(QRect(x, y, target_w, target_h))

    def _available_image_size(self) -> QSize:
        """Tamanho útil para a imagem considerando eventual título."""
        spacing = 6
        w = max(50, self.width())
        h = max(50, self.height())
        if self._title_text:
            h = max(40, h - (spacing + 22))
        return QSize(w, h)

    @staticmethod
    def _fit_size(src_w: int, src_h: int, max_w: int, max_h: int) -> tuple[int, int]:
        """Calcula tamanho destino preservando proporção para caber dentro de max_w x max_h."""
        if src_w <= 0 or src_h <= 0:
            return (max_w, max_h)
        ratio = min(max_w / src_w, max_h / src_h)
        return (max(1, int(src_w * ratio)), max(1, int(src_h * ratio)))

    def _scaled_pixmap(self, pm: QPixmap) -> QPixmap:
        avail = self._available_image_size()
        if not pm.isNull():
            pm = pm.scaled(avail, Qt.KeepAspectRatio, Qt.SmoothTransformation)
        return pm
