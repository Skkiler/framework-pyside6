# ui/widgets/toast.py

from __future__ import annotations
from typing import Optional
from PySide6.QtCore import Qt, QTimer, QEasingCurve, QPropertyAnimation, QRect
from PySide6.QtGui import QFont
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QGraphicsOpacityEffect

_STYLE = {
    "info":    {"bg": "#2d6cdf", "fg": "#ffffff"},
    "success": {"bg": "#20a068", "fg": "#ffffff"},
    "warn":    {"bg": "#d9a300", "fg": "#0e0e0e"},
    "error":   {"bg": "#cc3333", "fg": "#ffffff"},
}

class Toast(QWidget):
    """Snackbar flotante no canto inferior direito do parent."""
    def __init__(self, parent: QWidget, text: str, kind: str = "info", timeout_ms: int = 2400):
        super().__init__(parent)
        self.setAttribute(Qt.WA_TranslucentBackground, True)
        self.setWindowFlags(Qt.FramelessWindowHint | Qt.ToolTip)
        self.setObjectName("Toast")

        k = _STYLE.get(kind, _STYLE["info"])
        self._bg = k["bg"]; self._fg = k["fg"]; self._timeout = timeout_ms

        lay = QHBoxLayout(self); lay.setContentsMargins(12, 8, 12, 8); lay.setSpacing(8)
        self._label = QLabel(text, self)
        f = QFont(); f.setPointSize(10); f.setBold(True)
        self._label.setFont(f); self._label.setStyleSheet(f"color: {self._fg};")
        lay.addWidget(self._label)

        self.setStyleSheet(f"""
        QWidget#Toast {{
            background: {self._bg};
            border-radius: 8px;
            border: 1px solid rgba(0,0,0,0.18);
        }}""")

        # Opacidade
        eff = QGraphicsOpacityEffect(self); eff.setOpacity(0.0)
        self.setGraphicsEffect(eff); self._eff = eff

        self._anim = QPropertyAnimation(self._eff, b"opacity", self)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)

        self._life = QTimer(self); self._life.setSingleShot(True)
        self._life.timeout.connect(self._fade_out)

    # ---------- API ----------
    def show_toast(self):
        self._place_bottom_right()
        self.show()
        self._fade_in()

    # ---------- internals ----------
    def _place_bottom_right(self):
        par = self.parentWidget()
        if not par:
            return
        par_rect = par.rect()
        self.adjustSize()
        w, h = self.width(), self.height()
        margin = 16
        x = par_rect.right() - w - margin
        y = par_rect.bottom() - h - margin
        self.setGeometry(QRect(x, y, w, h))

    def _fade_in(self):
        self._anim.stop()
        self._anim.setDuration(180)
        self._anim.setStartValue(0.0); self._anim.setEndValue(1.0)
        self._anim.start()
        self._life.start(self._timeout)

    def _fade_out(self):
        self._anim.stop()
        self._anim.setDuration(220)
        self._anim.setStartValue(1.0); self._anim.setEndValue(0.0)
        self._anim.finished.connect(self.close)
        self._anim.start()

# ----- helper simples -----
def show_toast(parent: QWidget, text: str, kind: str = "info", timeout_ms: int = 2400):
    t = Toast(parent, text, kind, timeout_ms)
    t.show_toast()
    return t
