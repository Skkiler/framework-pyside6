# ui/widgets/settings_sidebar.py

from __future__ import annotations

from PySide6.QtCore import Qt, QEasingCurve, QPropertyAnimation, Signal, QEvent, QRect
from PySide6.QtWidgets import QFrame, QWidget, QVBoxLayout, QHBoxLayout, QLabel
from .buttons import Controls

EXPANDED_WIDTH = 320  # largura da sidebar direita

class SettingsSidePanel(QFrame):
    opened = Signal()
    closed = Signal()

    def __init__(
        self,
        parent: QWidget,
        content: QWidget,
        *,
        title: str = "Configurações",
        use_scrim: bool = True,
        close_on_scrim: bool = True
    ):
        super().__init__(parent)
        self.setObjectName("SettingsSidePanel")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.hide()

        self._expanded = False
        self._in_anim = False
        self._pending_after = None

        # layout base
        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(0)

        # cabeçalho com botão fechar
        header = QFrame()
        header.setObjectName("SettingsSidePanelHeader")
        h = QHBoxLayout(header)
        h.setContentsMargins(8, 8, 8, 8)
        h.setSpacing(8)

        self.btn_close = Controls.IconButton("⟵", header, tooltip="Fechar")
        self.btn_close.clicked.connect(lambda: self.close(True))
        h.addWidget(self.btn_close)
        h.addWidget(QLabel(title))
        h.addStretch(1)

        root.addWidget(header)

        # conteúdo
        root.addWidget(content)

        # animação de entrada/saída
        self._anim = QPropertyAnimation(self, b"geometry", self)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.setDuration(220)
        self._anim.finished.connect(self._on_anim_finished)

        # scrim (fundo escuro)
        self._scrim = QWidget(parent) if use_scrim else None
        if self._scrim:
            self._scrim.setObjectName("Scrim")
            self._scrim.hide()
            if close_on_scrim:
                self._scrim.mousePressEvent = lambda e: self.close(True)

        parent.installEventFilter(self)

    # --- helpers ---
    def _full_rect(self) -> QRect:
        p = self.parentWidget()
        return QRect(0, 0, p.width(), p.height()) if p else QRect()

    def eventFilter(self, obj, e):
        if obj is self.parentWidget() and e.type() == QEvent.Resize:
            if self._expanded:
                fr = self._full_rect()
                self.setGeometry(QRect(fr.width() - EXPANDED_WIDTH, 0, EXPANDED_WIDTH, fr.height()))
                if self._scrim:
                    self._scrim.setGeometry(fr)
        return super().eventFilter(obj, e)

    # --- abrir/fechar ---
    def open(self, animate: bool = True):
        if self._expanded or self._in_anim:
            return
        self._expanded, self._in_anim = True, True
        self.show()
        if self._scrim:
            fr = self._full_rect()
            self._scrim.setGeometry(fr)
            self._scrim.show()
            self._scrim.raise_()
        self.raise_()

        fr = self._full_rect()
        start = QRect(fr.width(), 0, EXPANDED_WIDTH, fr.height())
        end   = QRect(fr.width() - EXPANDED_WIDTH, 0, EXPANDED_WIDTH, fr.height())

        if animate:
            self._anim.stop()
            self._anim.setStartValue(start)
            self._anim.setEndValue(end)
            self._anim.start()
        else:
            self.setGeometry(end)
            self._in_anim = False
            self.opened.emit()

    def close(self, animate: bool = True):
        if not self._expanded or self._in_anim:
            return
        self._expanded, self._in_anim = False, True

        fr = self._full_rect()
        start = QRect(self.geometry().x(), 0, EXPANDED_WIDTH, fr.height())
        end   = QRect(fr.width(), 0, EXPANDED_WIDTH, fr.height())

        def _after():
            self.hide()
            if self._scrim:
                self._scrim.hide()

        if animate:
            self._pending_after = _after
            self._anim.stop()
            self._anim.setStartValue(start)
            self._anim.setEndValue(end)
            self._anim.start()
        else:
            self.setGeometry(end)
            _after()
            self._in_anim = False
            self.closed.emit()

    def toggle(self):
        if self._expanded:
            self.close(True)
        else:
            self.open(True)

    def _on_anim_finished(self):
        self._in_anim = False
        if self._expanded:
            self.opened.emit()
        else:
            if self._pending_after:
                self._pending_after()
                self._pending_after = None
            self.closed.emit()
