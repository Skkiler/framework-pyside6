# ui/widgets/overlay_sidebar.py

from PySide6.QtCore import Qt, QEasingCurve, QPropertyAnimation, Signal, QEvent, QRect
from PySide6.QtWidgets import (
    QFrame, QWidget, QVBoxLayout, QListWidget, QListWidgetItem, QLabel,
    QHBoxLayout
)
from ..widgets.buttons import Controls  # usamos Controls.IconButton

EXPANDED_WIDTH = 240

class OverlaySidePanel(QFrame):
    pageSelected = Signal(str)
    opened = Signal()
    closed = Signal()

    def __init__(
        self,
        parent: QWidget,
        *,
        use_scrim: bool = True,
        close_on_scrim: bool = False,   # por padrão não fecha ao clicar fora
        close_on_select: bool = False   # por padrão não fecha ao selecionar item
    ):
        super().__init__(parent)
        self.setObjectName("SidePanel")
        self.setAttribute(Qt.WA_StyledBackground, True)
        self.hide()

        self._expanded = False
        self._close_on_select = close_on_select
        self._in_anim = False
        self._pending_after = None

        # SCRIM
        self._scrim = QWidget(parent) if use_scrim else None
        if self._scrim:
            self._scrim.setObjectName("Scrim")
            self._scrim.hide()
            if close_on_scrim:
                self._scrim.mousePressEvent = lambda e: self.close()

        # ====== CONTEÚDO ======
        root = QVBoxLayout(self)
        root.setContentsMargins(8, 8, 8, 8)
        root.setSpacing(6)

        header_row = QHBoxLayout()
        header_row.setContentsMargins(0, 0, 0, 0)
        header_row.setSpacing(6)

        self.btn_hamb = Controls.IconButton("☰", self, tooltip="Fechar menu")
        self.btn_hamb.clicked.connect(self._on_hamburger_clicked)
        header_row.addWidget(self.btn_hamb, 0)

        self.header = QLabel("Menu", self)
        self.header.setObjectName("SidePanelHeader")
        header_row.addWidget(self.header, 1)

        root.addLayout(header_row)

        self.list = QListWidget(self)
        self.list.itemClicked.connect(self._on_item_clicked)
        root.addWidget(self.list)

        # animação de geometria
        self._anim = QPropertyAnimation(self, b"geometry", self)
        self._anim.setDuration(220)
        self._anim.setEasingCurve(QEasingCurve.OutCubic)
        self._anim.finished.connect(self._on_anim_finished)

        parent.installEventFilter(self)
        self._place_initial()
        self.setFocusPolicy(Qt.StrongFocus)

    # ---------- infra ----------
    def eventFilter(self, watched, event):
        if watched is self.parent() and event.type() in (QEvent.Resize, QEvent.Move, QEvent.Show):
            self._reposition()
        return super().eventFilter(watched, event)

    def keyPressEvent(self, e):
        if e.key() == Qt.Key_Escape and self._expanded and not self._in_anim:
            self.close()
            e.accept()
            return
        super().keyPressEvent(e)

    def _full_rect(self) -> QRect:
        p = self.parent()
        return p.rect() if p else QRect()

    def _place_initial(self):
        fr = self._full_rect()
        self.setGeometry(QRect(-EXPANDED_WIDTH, 0, EXPANDED_WIDTH, fr.height()))
        if self._scrim:
            self._scrim.setGeometry(fr)

    def _reposition(self):
        fr = self._full_rect()
        r = self.geometry()
        self.setGeometry(QRect(r.x(), 0, r.width(), fr.height()))
        if self._scrim:
            self._scrim.setGeometry(fr)

    # ---------- API ----------
    def add_page(self, name: str, label: str):
        it = QListWidgetItem(label)
        it.setData(Qt.UserRole, name)
        self.list.addItem(it)

    def open(self, animate: bool = True):
        if self._expanded or self._in_anim:
            return
        self._expanded = True
        self._in_anim = True
        self._pending_after = None

        if self._scrim:
            self._scrim.show()
            self._scrim.raise_()

        self.show()
        self.raise_()
        self.setFocus()
        self.btn_hamb.setEnabled(False)

        fr = self._full_rect()
        start = QRect(-EXPANDED_WIDTH, 0, EXPANDED_WIDTH, fr.height())
        end   = QRect(0,             0, EXPANDED_WIDTH, fr.height())
        if animate:
            self._anim.stop()
            self._anim.setStartValue(start)
            self._anim.setEndValue(end)
            self._anim.start()
        else:
            self.setGeometry(end)
            self._in_anim = False
            self.btn_hamb.setEnabled(True)
            self.opened.emit()

    def close(self, animate: bool = True):
        if not self._expanded or self._in_anim:
            return
        self._expanded = False
        self._in_anim = True

        fr = self._full_rect()
        start = QRect(self.geometry().x(), 0, EXPANDED_WIDTH, fr.height())
        end   = QRect(-EXPANDED_WIDTH,     0, EXPANDED_WIDTH, fr.height())

        def _after():
            self.hide()
            if self._scrim:
                self._scrim.hide()

        self._pending_after = _after

        if animate:
            self._anim.stop()
            self._anim.setStartValue(start)
            self._anim.setEndValue(end)
            self._anim.start()
        else:
            self.setGeometry(end)
            self._in_anim = False
            if self._pending_after:
                self._pending_after()
            self._pending_after = None
            self.closed.emit()

    def toggle(self):
        if self._in_anim:
            return
        self.open() if not self._expanded else self.close()

    def set_close_on_select(self, value: bool):
        self._close_on_select = bool(value)

    # ---------- slots ----------
    def _on_item_clicked(self, it):
        route = it.data(Qt.UserRole)
        self.pageSelected.emit(route)
        if self._close_on_select and not self._in_anim:
            self.close()

    def _on_hamburger_clicked(self):
        if self._in_anim:
            return
        self.close()

    def _on_anim_finished(self):
        self._in_anim = False
        self.btn_hamb.setEnabled(True)

        if self._pending_after:
            try:
                self._pending_after()
            finally:
                self._pending_after = None

        if self._expanded:
            self.opened.emit()
        else:
            self.closed.emit()
