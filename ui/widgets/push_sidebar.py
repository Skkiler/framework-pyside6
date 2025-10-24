# ui/widgets/push_sidebar.py

from __future__ import annotations

from PySide6.QtCore import Qt, QEasingCurve, QPropertyAnimation, Signal, QPoint
from PySide6.QtWidgets import QWidget, QFrame, QVBoxLayout, QHBoxLayout, QLabel, QSizePolicy, QSpacerItem

DEFAULT_WIDTH = 480
GRIP_WIDTH = 6  # área sensível para redimensionar


class PushSidePanel(QFrame):
    opened = Signal()
    closed = Signal()
    expandedChanged = Signal(bool)
    widthChanged = Signal(int)

    def __init__(
        self,
        parent: QWidget | None = None,
        *,
        content: QWidget | None = None,
        title: str | None = None,
        width: int = DEFAULT_WIDTH,
        duration_ms: int = 200,
        easing: QEasingCurve.Type = QEasingCurve.OutCubic,
        position: str = "right",
        resizable: bool = True,
        **_ignored_kwargs,
    ) -> None:
        super().__init__(parent)
        self._target_width = max(240, int(width))
        self._duration = max(0, int(duration_ms))
        self._easing = easing
        self._position = position
        self._expanded = False
        self._is_animating = False
        self._is_resizing = False
        self._anim: QPropertyAnimation | None = None

        self.setObjectName("PushSidePanel")
        self.setFrameShape(QFrame.StyledPanel)
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.setMinimumWidth(0)
        self.setMaximumWidth(0)  # inicia fechado
        self.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)

        # ---------- Layout ----------
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        # Cabeçalho com título
        header = QFrame(self)
        header.setObjectName("PushSidePanelHeader")
        hl = QHBoxLayout(header)
        hl.setContentsMargins(12, 10, 12, 6)
        hl.setSpacing(6)

        self._title_label = QLabel(title or "Detalhes", header)
        f = self._title_label.font(); f.setBold(True)
        self._title_label.setFont(f)
        self._title_label.setWordWrap(True)
        self._title_label.setTextInteractionFlags(Qt.TextSelectableByMouse)
        hl.addWidget(self._title_label)
        hl.addItem(QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        outer.addWidget(header)

        # Conteúdo
        self._container = QFrame(self)
        self._container.setObjectName("PushSidePanelContainer")
        self._layout = QVBoxLayout(self._container)
        self._layout.setContentsMargins(10, 0, 10, 10)
        self._layout.setSpacing(0)

        # Grip de resize (fica na borda que empurra o conteúdo)
        grip_host = QFrame(self)
        grip_host.setFixedWidth(GRIP_WIDTH)
        grip_host.setCursor(Qt.SizeHorCursor)
        grip_host.setObjectName("PushSidePanelGrip")
        grip_host.mousePressEvent = lambda ev: self._on_grip_press(ev)
        grip_host.mouseMoveEvent = lambda ev: self._on_grip_move(ev)
        grip_host.mouseReleaseEvent = lambda ev: self._on_grip_release(ev)
        grip_host.mouseDoubleClickEvent = lambda ev: self._on_grip_double(ev)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(0)
        if position == "right":
            row.addWidget(grip_host)           # grip encosta no conteúdo principal
            row.addWidget(self._container, 1)  # painel cresce “para a esquerda”
        else:
            row.addWidget(self._container, 1)
            row.addWidget(grip_host)
        outer.addLayout(row, 1)

        self._grip = grip_host
        self._resizable = bool(resizable)
        self._grip.setVisible(self._resizable)

        # Animação
        self._anim = QPropertyAnimation(self, b"maximumWidth", self)
        self._anim.setEasingCurve(self._easing)
        self._anim.setDuration(self._duration)
        self._anim.finished.connect(self._on_anim_end)

        if content is not None:
            self.setWidget(content)

        self.hide()

    # -------------------- API --------------------

    def setWidget(self, widget: QWidget | None) -> None:
        while self._layout.count():
            item = self._layout.takeAt(0)
            w = item.widget()
            if w:
                w.setParent(None)
        if widget:
            self._layout.addWidget(widget)

    def setTitle(self, text: str | None) -> None:
        self._title_label.setText(text or "Detalhes")

    def isExpanded(self) -> bool:
        return self._expanded

    def setResizable(self, on: bool) -> None:
        self._resizable = bool(on)
        self._grip.setVisible(self._resizable)

    def setTargetWidth(self, w: int) -> None:
        self._target_width = max(240, int(w))
        if self._expanded:
            self.setMaximumWidth(self._target_width)
            self.widthChanged.emit(self._target_width)

    def toggle(self) -> None:
        if self._is_animating or self._is_resizing:
            return
        self.open() if not self._expanded else self.close()

    def open(self) -> None:
        if self._expanded and self.maximumWidth() == self._target_width:
            return
        if self._is_animating or self._is_resizing:
            return
        self._expanded = True
        self.expandedChanged.emit(True)
        self.show()
        start = self.maximumWidth()
        end = self._target_width
        if start == end:
            self.opened.emit()
            return
        self._start_anim(start, end)

    def close(self) -> None:
        if (not self._expanded) and self.maximumWidth() == 0:
            return
        if self._is_animating or self._is_resizing:
            return
        self._expanded = False
        self.expandedChanged.emit(False)
        start = self.maximumWidth()
        end = 0
        if start == end:
            self.hide()
            self.closed.emit()
            return
        self._start_anim(start, end)

    # ------------------- Internos -------------------

    def _start_anim(self, start: int, end: int) -> None:
        anim = self._anim
        if anim is None:
            anim = QPropertyAnimation(self, b"maximumWidth", self)
            self._anim = anim
            anim.finished.connect(self._on_anim_end)
        anim.stop()
        self._is_animating = True
        anim.setEasingCurve(self._easing)
        anim.setDuration(self._duration)
        anim.setStartValue(int(start))
        anim.setEndValue(int(end))
        anim.start()

    def _on_anim_end(self) -> None:
        self._is_animating = False
        if self._expanded:
            self.setMaximumWidth(self._target_width)
            self.show()
            self.opened.emit()
        else:
            self.setMaximumWidth(0)
            self.hide()
            self.closed.emit()

    # ------- Redimensionamento por grip -------
    def _on_grip_press(self, ev):
        if not self._resizable or ev.button() != Qt.LeftButton:
            return
        self._is_resizing = True
        self._resize_origin_global = ev.globalPosition().toPoint() if hasattr(ev, "globalPosition") else ev.globalPos()
        self._resize_origin_width = self.width()
        if self._anim:
            self._anim.stop()
            self._is_animating = False
        ev.accept()

    def _on_grip_move(self, ev):
        if not self._is_resizing:
            return
        pos: QPoint = ev.globalPosition().toPoint() if hasattr(ev, "globalPosition") else ev.globalPos()
        dx = pos.x() - self._resize_origin_global.x()

        # Para painel à direita:
        # mover o mouse para ESQUERDA (dx < 0) => AUMENTA largura (invade conteúdo)
        # mover para DIREITA (dx > 0)          => DIMINUI
        if self._position == "right":
            new_w = max(240, self._resize_origin_width - dx)
        else:
            new_w = max(240, self._resize_origin_width + dx)

        self.setMaximumWidth(new_w)
        self._target_width = new_w
        self.widthChanged.emit(new_w)
        ev.accept()

    def _on_grip_release(self, ev):
        if not self._is_resizing or ev.button() != Qt.LeftButton:
            return
        self._is_resizing = False
        self._expanded = self.maximumWidth() > 0
        ev.accept()

    def _on_grip_double(self, ev):
        if not self._resizable:
            return
        self._target_width = DEFAULT_WIDTH
        self.setMaximumWidth(self._target_width)
        self.widthChanged.emit(self._target_width)
        ev.accept()
