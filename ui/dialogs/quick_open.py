# ui/dialogs/quick_open.py

from __future__ import annotations
from typing import List, Tuple

from PySide6.QtCore import Qt, QStringListModel, Signal, QModelIndex
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLineEdit, QListView, QFrame

from ui.widgets.titlebar import TitleBar
from ui.core.frameless_window import FramelessDialog


class QuickOpenDialog(FramelessDialog):

    routeChosen = Signal(str)

    def __init__(self, pages, parent=None, *, title: str = "Quick Open"):
        super().__init__(parent)
        self.setObjectName("QuickOpenDialog")
        self.setProperty("role", "panel")
        self.set_edges_enabled(False)      # diálogo não redimensionável por borda
        self.set_center_mode("parent")     # centraliza sobre a janela do app

        # --- CENTRAL ---
        central = QWidget(self.content())  # usa o content() do Frameless
        central.setObjectName("QuickOpenCentral")
        v = QVBoxLayout(central)
        v.setContentsMargins(0, 0, 0, 0)
        v.setSpacing(0)

        # TitleBar (igual ao app)
        tb_wrap = QFrame(central)
        tb_wrap.setObjectName("DialogTitleFrame")
        tb_lay = QVBoxLayout(tb_wrap)
        tb_lay.setContentsMargins(6, 6, 6, 6)

        tb = TitleBar(title, self)
        tb.setObjectName("QuickOpenTitleBar")
        self.connect_titlebar(tb)          # integra com drag/fechar e oculta min/max
        tb_lay.addWidget(tb)
        v.addWidget(tb_wrap)

        # Conteúdo
        content = QFrame(central)
        content.setObjectName("DialogContent")
        cv = QVBoxLayout(content)
        cv.setContentsMargins(12, 12, 12, 12)
        cv.setSpacing(10)

        self._edit = QLineEdit(content)
        self._edit.setPlaceholderText("Filtrar rotas…")
        self._edit.setObjectName("QuickOpenFilter")
        self._edit.setClearButtonEnabled(True)
        cv.addWidget(self._edit)

        self._list = QListView(content)
        self._list.setObjectName("QuickOpenList")
        self._list.setUniformItemSizes(True)
        self._list.setEditTriggers(QListView.NoEditTriggers)
        self._list.setSelectionBehavior(QListView.SelectItems)
        self._list.setSelectionMode(QListView.SingleSelection)
        cv.addWidget(self._list)

        v.addWidget(content)
        self.setCentralWidget(central)

        # --- Dados: apenas pages com sidebar=True ---
        # pages é uma lista de PageSpec (route, label, sidebar, order, factory)
        self._all: List[Tuple[str, str]] = [
            (getattr(p, "label", None) or getattr(p, "route", ""), getattr(p, "route", ""))
            for p in pages
            if getattr(p, "sidebar", False)
        ]
        # ordenação por label (case-insensitive)
        self._all.sort(key=lambda x: (x[0] or "").lower())

        self._model = QStringListModel(self)
        self._apply_items(self._all)

        self._list.setModel(self._model)

        # Eventos / interações
        self._edit.textChanged.connect(self._on_filter_changed)
        self._list.doubleClicked.connect(self._on_activate)

        # Teclas: Enter abre seleção; Esc fecha
        self._edit.returnPressed.connect(self._open_current)
        self._list.setFocusPolicy(Qt.StrongFocus)

        # seleção inicial
        self._select_first()

    # --------------- Helpers de UI ---------------

    def _apply_items(self, items: List[Tuple[str, str]]):
        """Atualiza o modelo com a lista (label, path)."""
        self._filtered = list(items)
        display = [f"{lbl}  —  {path}" for (lbl, path) in self._filtered]
        self._model.setStringList(display)

    def _select_first(self):
        if self._model.rowCount() > 0:
            idx = self._model.index(0)
            self._list.setCurrentIndex(idx)
        self._edit.setFocus(Qt.TabFocusReason)

    # --------------- Filtro ---------------

    def _on_filter_changed(self, text: str):
        text = (text or "").strip().lower()
        if not text:
            self._apply_items(self._all)
            self._select_first()
            return

        tokens = text.split()
        out: List[Tuple[str, str]] = []
        for lbl, path in self._all:
            hay = f"{lbl} {path}".lower()
            if all(tok in hay for tok in tokens):
                out.append((lbl, path))
        self._apply_items(out)
        self._select_first()

    # --------------- Abrir seleção ---------------

    def _on_activate(self, idx: QModelIndex):
        self._activate_index(idx)

    def _open_current(self):
        idx = self._list.currentIndex()
        if idx and idx.isValid():
            self._activate_index(idx)

    def _activate_index(self, idx: QModelIndex):
        row = idx.row()
        if 0 <= row < len(self._filtered):
            _, path = self._filtered[row]
            if path:
                self.routeChosen.emit(path)
                self.accept()  # fecha com animação

    # --------------- Teclado extra ---------------

    def keyPressEvent(self, e):
        # Up/Down na linha de edição deve navegar na lista
        if e.key() in (Qt.Key_Down, Qt.Key_Up):
            view = self._list
            cur = view.currentIndex().row()
            if e.key() == Qt.Key_Down:
                cur = min(cur + 1, self._model.rowCount() - 1)
            else:
                cur = max(cur - 1, 0)
            if cur >= 0:
                view.setCurrentIndex(self._model.index(cur))
            e.accept()
            return
        if e.key() == Qt.Key_Return or e.key() == Qt.Key_Enter:
            self._open_current(); e.accept(); return
        if e.key() == Qt.Key_Escape:
            self.reject(); e.accept(); return
        super().keyPressEvent(e)
