# ui/widgets/titlebar.py

from __future__ import annotations
from typing import Optional, Union
from pathlib import Path

from PySide6.QtCore import Qt, Signal, QPoint, QSize, QTimeLine, QTimer
from PySide6.QtGui import QPixmap, QIcon, QPainter
from PySide6.QtWidgets import QWidget, QLabel, QHBoxLayout, QPushButton, QSizePolicy


# ---------- Widget de ícone com animação (cross-fade) à prova de HiDPI ----------

class IconWidget(QWidget):
    def __init__(self, icon: Optional[Union[str, QPixmap, QIcon]] = None,
                 size: int = 20, parent: QWidget | None = None):
        super().__init__(parent)
        self._icon_size = size
        self._icon: Optional[QIcon] = self._normalize(icon)
        self._old_icon: Optional[QIcon] = None
        self._anim: Optional[QTimeLine] = None
        self._progress: float = 1.0  # 1.0 = ícone atual totalmente visível
        self._fade_duration_ms: int = 240  # mais suave; ajuste se quiser

        self.setObjectName("TitleBarAppIcon")
        self.setFixedSize(self._icon_size, self._icon_size)
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)

    # --------- Helpers ---------
    def _normalize(self, icon: Optional[Union[str, QPixmap, QIcon]]) -> Optional[QIcon]:
        if icon is None:
            win = self.window()
            if win is not None and not win.windowIcon().isNull():
                return win.windowIcon()
            return None
        if isinstance(icon, QIcon):
            return icon
        if isinstance(icon, QPixmap):
            return QIcon(icon)
        s = str(icon)
        p = Path(s)
        if p.exists():
            return QIcon(str(p))
        tmp = QIcon(s)  # aceita também ":/recurso"
        return tmp if not tmp.isNull() else None

    def setFadeDuration(self, ms: int):
        self._fade_duration_ms = max(60, int(ms))

    # --------- API ---------
    def setIcon(self, icon: Optional[Union[str, QPixmap, QIcon]], *,
                animate: bool = True, duration_ms: Optional[int] = None):
        new_icon = self._normalize(icon)
        if (self._icon is None or self._icon.isNull()) and (new_icon is None or new_icon.isNull()):
            return

        # Troca direta quando não dá para animar
        if not animate or self._icon is None or self._icon.isNull():
            self._icon = new_icon
            self._old_icon = None
            self._progress = 1.0
            self.update()
            return

        # Início do cross-fade
        self._old_icon = self._icon
        self._icon = new_icon
        self._progress = 0.0

        if self._anim:
            try:
                self._anim.stop()
            except Exception:
                pass

        dur = int(duration_ms) if duration_ms is not None else self._fade_duration_ms
        self._anim = QTimeLine(dur, self)
        self._anim.setFrameRange(0, 100)
        # Suavização real (EaseInOut)
        try:
            self._anim.setCurveShape(QTimeLine.CurveShape.EaseInOutCurve)
        except Exception:
            # fallback seguro caso a enum varie
            self._anim.setCurveShape(QTimeLine.EaseInOutCurve)
        # 60 fps aprox.
        try:
            self._anim.setUpdateInterval(16)
        except Exception:
            pass

        self._anim.frameChanged.connect(self._on_anim_frame)
        self._anim.finished.connect(self._on_anim_end)
        self._anim.start()
        self.update()

    def _on_anim_frame(self, frame: int):
        self._progress = max(0.0, min(1.0, frame / 100.0))
        self.update()

    def _on_anim_end(self):
        self._progress = 1.0
        self._old_icon = None
        self.update()

    def sizeHint(self):
        return QSize(self._icon_size, self._icon_size)

    def minimumSizeHint(self):
        return self.sizeHint()

    def _pixmap_for(self, icon: QIcon, dpr: float) -> Optional[QPixmap]:
        phys_w, phys_h = int(self._icon_size * dpr), int(self._icon_size * dpr)
        pm = icon.pixmap(phys_w, phys_h)
        if pm.isNull():
            return None
        try:
            pm.setDevicePixelRatio(dpr)
        except Exception:
            pass
        return pm

    # --------- Pintura (cross-fade) ---------
    def paintEvent(self, e):
        if (self._icon is None or self._icon.isNull()) and \
           (self._old_icon is None or (self._old_icon and self._old_icon.isNull())):
            return

        w, h = self.width(), self.height()
        try:
            dpr = float(self.window().devicePixelRatioF()) if self.window() else 1.0
        except Exception:
            dpr = 1.0

        painter = QPainter(self)
        painter.setRenderHint(QPainter.SmoothPixmapTransform, True)

        p = self._progress  # 0 → antigo 100% / novo 0% ; 1 → antigo 0% / novo 100%
        x = (w - self._icon_size) // 2
        y = (h - self._icon_size) // 2  # centraliza verticalmente (caso o widget seja maior)

        # antigo primeiro (se houver) com alpha decrescente
        if self._old_icon and not self._old_icon.isNull():
            old_alpha = 1.0 - p
            if old_alpha > 0.0:
                pm_old = self._pixmap_for(self._old_icon, dpr)
                if pm_old:
                    painter.save()
                    painter.setOpacity(old_alpha)
                    painter.drawPixmap(x, y, pm_old)
                    painter.restore()

        # novo depois, com alpha crescente
        if self._icon and not self._icon.isNull():
            new_alpha = p
            if new_alpha > 0.0:
                pm_new = self._pixmap_for(self._icon, dpr)
                if pm_new:
                    painter.save()
                    painter.setOpacity(new_alpha)
                    painter.drawPixmap(x, y, pm_new)
                    painter.restore()

        painter.end()


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
        self._suppress_next_win_icon_changed = False  # coalescer eventos

        self.setObjectName("TitleBar")
        self.setFixedHeight(36)
        self._icon_size = 20
        # Pendências durante animações pesadas de tema
        self._pending_icon = None
        self._pending_icon_timer: QTimer | None = None

        root = QHBoxLayout(self)
        root.setContentsMargins(10, 0, 10, 0)
        root.setSpacing(8)

        # ---- Ícone do app (sempre no layout) ----
        self._icon = IconWidget(icon=icon, size=self._icon_size, parent=self)
        # Se quiser ainda mais suave por tema: self._icon.setFadeDuration(260)
        root.addWidget(self._icon, 0)
        if not self._icon._icon or self._icon._icon.isNull():
            self._icon.hide()

        # ---- Título ----
        self._lbl = QLabel(title, self)
        self._lbl.setObjectName("TitleBarLabel")
        self._lbl.setAlignment(Qt.AlignVCenter | Qt.AlignLeft)
        self._lbl.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Preferred)
        if self._icon.isVisible():
            self._lbl.hide()
            root.addStretch(1)
        else:
            root.addWidget(self._lbl, 1)

        # ---- Botões ----
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

        # ---- Engrenagem ----
        self._btn_settings = QPushButton('⚙︎', self)
        self._btn_settings.setObjectName("TitleBarButton")
        self._btn_settings.setFlat(True)
        self._btn_settings.setCursor(Qt.PointingHandCursor)
        self._btn_settings.setToolTip("Configurações")
        self._btn_settings.setFixedSize(32, 24)
        f = self._btn_settings.font()
        f.setFamily("Segoe UI Symbol")
        self._btn_settings.setFont(f)

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

        # Conecta ao windowIconChanged assim que possível
        QTimer.singleShot(0, self._hook_window_icon_signal)

    # ---------- Integração com mudança de ícone da janela ----------
    def _hook_window_icon_signal(self):
        if hasattr(self, "_win_icon_hooked") and self._win_icon_hooked:
            return
        w = self.window()
        if w is not None:
            try:
                w.windowIconChanged.connect(self._on_window_icon_changed)
                self._win_icon_hooked = True
            except Exception:
                self._win_icon_hooked = False

    def _on_window_icon_changed(self, icon: QIcon):
        # Se acabamos de setar manualmente, ignorar este evento duplicado
        if self._suppress_next_win_icon_changed:
            return
        # Se a janela sinalizou animação pesada de tema, postergar atualização do ícone
        try:
            w = self.window()
            if w is not None and getattr(w, "_is_heavy_anim", False):
                self._pending_icon = icon
                self._ensure_pending_icon_timer()
                return
        except Exception:
            pass
        try:
            self._icon.setIcon(icon, animate=True)
            self._icon.show()
            self._lbl.hide()
        except Exception:
            pass

    # ---------- API ----------
    def setTitle(self, text: str) -> None:
        if not self._icon.isVisible():
            self._lbl.setText(text)

    def setIcon(self, icon: Union[str, QPixmap, QIcon]) -> bool:
        # Se animação pesada está ativa, posterga atualização para o fim
        try:
            w = self.window()
            if w is not None and getattr(w, "_is_heavy_anim", False):
                self._pending_icon = icon
                self._ensure_pending_icon_timer()
                return False
        except Exception:
            pass

        # Sinalizamos para ignorar o windowIconChanged do mesmo ciclo
        self._suppress_next_win_icon_changed = True
        try:
            self._icon.setIcon(icon, animate=True)
        finally:
            # libera no próximo tick do event loop (coalescência)
            QTimer.singleShot(0, lambda: setattr(self, "_suppress_next_win_icon_changed", False))

        ok = self._icon._icon is not None and not self._icon._icon.isNull()
        if ok:
            self._icon.show()
            self._lbl.hide()
        return ok

    def _ensure_pending_icon_timer(self):
        try:
            if self._pending_icon_timer is None:
                self._pending_icon_timer = QTimer(self)
                self._pending_icon_timer.setSingleShot(True)
                self._pending_icon_timer.timeout.connect(self._apply_pending_icon_if_ready)
            # tenta novamente em ~50ms
            self._pending_icon_timer.start(50)
        except Exception:
            pass

    def _apply_pending_icon_if_ready(self):
        try:
            if self._pending_icon is None:
                return
            w = self.window()
            if w is not None and getattr(w, "_is_heavy_anim", False):
                # ainda pesado → reagendar
                self._ensure_pending_icon_timer()
                return
            icon = self._pending_icon
            self._pending_icon = None
        except Exception:
            icon = None
        if icon is not None:
            try:
                self.setIcon(icon)
            except Exception:
                pass

    # aliases p/ compatibilidade
    def set_icon(self, icon: Union[str, QPixmap, QIcon]) -> bool:
        return self.setIcon(icon)

    def updateIcon(self, icon: Union[str, QPixmap, QIcon]) -> bool:
        return self.setIcon(icon)

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

    def showEvent(self, e):
        super().showEvent(e)
        self._hook_window_icon_signal()
