# ui/widgets/titlebar.py

from __future__ import annotations
from typing import Optional, Union
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QPoint, QSize, QRect, QEvent
from PySide6.QtGui import QPixmap, QIcon, QPainter
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QPushButton, QSizePolicy


# ---------- Widget de ícone à prova de HiDPI / frameless ----------
class IconWidget(QWidget):
    def __init__(self, icon: Optional[Union[str, QPixmap, QIcon]] = None,
                 size: int = 20, parent: QWidget | None = None):
        super().__init__(parent)
        self._icon_size = size
        self._icon: Optional[QIcon] = self._normalize(icon)
        self.setObjectName("TitleBarAppIcon")
        self.setFixedSize(self._icon_size, self._icon_size)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    def _normalize(self, icon: Optional[Union[str, QPixmap, QIcon]]) -> Optional[QIcon]:
        if not icon:
            win = self.window()
            if win is not None and not win.windowIcon().isNull():
                return win.windowIcon()
            return None
        if isinstance(icon, QIcon):
            return icon
        if isinstance(icon, QPixmap):
            return QIcon(icon)
        p = Path(str(icon))
        return QIcon(str(p)) if p.exists() else None

    def setIcon(self, icon: Optional[Union[str, QPixmap, QIcon]]):
        self._icon = self._normalize(icon)
        self.update()

    def sizeHint(self): return QSize(self._icon_size, self._icon_size)
    def minimumSizeHint(self): return self.sizeHint()

    def paintEvent(self, e):
        if not self._icon or self._icon.isNull():
            return
        w, h = self.width(), self.height()
        try:
            dpr = float(self.window().devicePixelRatioF()) if self.window() else 1.0
        except Exception:
            dpr = 1.0

        phys_w, phys_h = int(self._icon_size * dpr), int(self._icon_size * dpr)
        pm = self._icon.pixmap(phys_w, phys_h)
        if pm.isNull():
            return
        try: pm.setDevicePixelRatio(dpr)
        except Exception: pass

        y = (h - self._icon_size) // 2
        target = QRect(0, y, self._icon_size, self._icon_size)

        p = QPainter(self)
        p.setRenderHint(QPainter.SmoothPixmapTransform, True)
        p.drawPixmap(target, pm)
        p.end()


class TitleBar(QWidget):
    settingsRequested = Signal()
    minimizeRequested = Signal()
    maximizeRestoreRequested = Signal()
    closeRequested = Signal()

    def __init__(self, title: str = "", parent: QWidget | None = None,
                 icon: Optional[Union[str, QPixmap, QIcon]] = None):
        super().__init__(parent)
        self._pressed = False
        self._press_pos = QPoint()

        self.setObjectName("TitleBar")
        self.setFixedHeight(36)
        self._icon_size = 20

        root = QHBoxLayout(self)
        root.setContentsMargins(10, 0, 10, 0)
        root.setSpacing(8)

        # ---- Ícone do app ----
        self._icon = IconWidget(icon=icon, size=self._icon_size, parent=self)
        if not self._icon._icon or self._icon._icon.isNull():
            self._icon.hide()
        else:
            root.addWidget(self._icon, 0)

        # ---- Título (fallback sem ícone) ----
        self._lbl = QLabel(title, self)
        self._lbl.setObjectName("TitleBarLabel")
        self._lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self._lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        if self._icon.isVisible():
            self._lbl.hide()
            root.addStretch(1)
        else:
            root.addWidget(self._lbl, 1)

        # ---- Botões nativos ----
        self.btn_min   = QPushButton("–", self)
        self.btn_max   = QPushButton("□", self)
        self.btn_close = QPushButton("×", self)
        for b, tip in (
            (self.btn_min, "Minimizar"),
            (self.btn_max, "Maximizar/Restaurar"),
            (self.btn_close, "Fechar"),
        ):
            b.setObjectName("TitleBarButton")
            b.setFixedSize(32, 24)
            b.setCursor(Qt.PointingHandCursor)
            b.setFocusPolicy(Qt.NoFocus)
            b.setFlat(True)
            b.setToolTip(tip)

        # ---- Engrenagem (segue o mesmo padrão visual por QSS) ----
        self._btn_settings = QPushButton('⚙︎', self)
        self._btn_settings.setObjectName("TitleBarButton")
        self._btn_settings.setFlat(True)
        self._btn_settings.setCursor(Qt.PointingHandCursor)
        self._btn_settings.setToolTip("Configurações")
        self._btn_settings.setFixedSize(32, 24)
        f = self._btn_settings.font()
        f.setFamily("Segoe UI Symbol")
        self._btn_settings.setFont(f)

        # ordem na barra
        root.addStretch(1)
        root.addWidget(self._btn_settings, 0)
        root.addWidget(self.btn_min, 0)
        root.addWidget(self.btn_max, 0)
        root.addWidget(self.btn_close, 0)

        # Sinais
        self._btn_settings.clicked.connect(self.settingsRequested)
        self.btn_min.clicked.connect(self.minimizeRequested.emit)
        self.btn_max.clicked.connect(self.maximizeRestoreRequested.emit)
        self.btn_close.clicked.connect(self.closeRequested.emit)

    # ---------- API ----------
    def setTitle(self, text: str) -> None:
        if not self._icon.isVisible():
            self._lbl.setText(text)

    def setIcon(self, icon: Union[str, QPixmap, QIcon]) -> bool:
        self._icon.setIcon(icon)
        ok = self._icon._icon is not None and not self._icon._icon.isNull()
        if ok:
            self._icon.show()
            self._lbl.hide()
        return ok

    def setMaximized(self, is_max: bool):
        self.btn_max.setText("❐" if is_max else "□")

    # ---------- mouse: arrasto / duplo clique ----------
    def mousePressEvent(self, e):
        if e.button() == Qt.LeftButton:
            self._pressed = True
            self._press_pos = e.globalPosition().toPoint()
            e.accept()
        else:
            super().mousePressEvent(e)

    def mouseMoveEvent(self, e):
        if self._pressed and self.window() is not None:
            w = self.window()
            delta = e.globalPosition().toPoint() - self._press_pos
            w.move(w.pos() + delta)
            self._press_pos = e.globalPosition().toPoint()
            e.accept()
        else:
            super().mouseMoveEvent(e)

    def mouseReleaseEvent(self, e):
        self._pressed = False
        super().mouseReleaseEvent(e)

    def mouseDoubleClickEvent(self, e):
        if e.button() == Qt.LeftButton:
            self.maximizeRestoreRequested.emit()
            e.accept()
        else:
            super().mouseDoubleClickEvent(e)

    # ---------- eventos sistêmicos ----------
    def event(self, e):
        # sem pintura manual -> nada a refazer em troca de tema
        return super().event(e)
