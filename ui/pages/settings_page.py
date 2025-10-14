# ui/pages/settings_page.py

from __future__ import annotations

from PySide6.QtCore import Qt, QSize
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox,
    QHBoxLayout, QFrame, QSpacerItem, QSizePolicy,
    QToolButton, QMenu, QDialog, QLineEdit, QPushButton
)
from PySide6.QtGui import QIcon

from ..core.theme_service import ThemeService
from ..widgets.buttons import Controls
from .theme_editor import ThemeEditorDialog
from ..core.frameless_window import FramelessDialog
from ..widgets.titlebar import TitleBar

PAGE = {
    "route": "settings",
    "label": "Configurações",
    "sidebar": False,   # <— NÃO aparece mais na sidebar esquerda
    "order": 99,
}

class SettingsPage(QWidget):
    def __init__(self, theme_service: ThemeService):
        super().__init__()
        self.tm = theme_service
        self._st = self.tm._settings

        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        # ===== Tema =====
        card_theme = QFrame(self)
        card_theme.setObjectName("OuterPanel")
        lt = QVBoxLayout(card_theme)
        lt.setContentsMargins(10, 10, 10, 10)
        lt.setSpacing(8)

        hdr = QLabel("Tema")
        hdr.setProperty("subtle", True)
        lt.addWidget(hdr)

        row = QHBoxLayout()
        row.setContentsMargins(0, 0, 0, 0)
        row.setSpacing(8)

        row.addWidget(QLabel("Selecionar:"))

        self.combo = QComboBox()
        # comportamento: combo expande, botão fica compacto à direita
        self.combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo.setMinimumWidth(160)
        self.combo.setMaximumWidth(16777215)
        row.addWidget(self.combo, 1)

        # Botão de "três pontinhos" com menu (Criar/Editar/Excluir)
        self.btn_more = QToolButton(self)
        self.btn_more.setObjectName("TinyMenuButton")
        self.btn_more.setToolTip("Opções de tema")
        self.btn_more.setPopupMode(QToolButton.InstantPopup)
        self.btn_more.setToolButtonStyle(Qt.ToolButtonIconOnly)
        self.btn_more.setAutoRaise(True)
        self.btn_more.setFixedSize(26, 26)
        self.btn_more.setText("⋯")  # texto => cor vem do QSS

        menu = QMenu(self.btn_more)
        act_new  = menu.addAction("Criar tema")
        act_edit = menu.addAction("Editar tema")
        act_del  = menu.addAction("Excluir tema")
        act_new.triggered.connect(self._new_theme)
        act_edit.triggered.connect(self._edit_theme)
        act_del.triggered.connect(self._delete_theme)
        self.btn_more.setMenu(menu)

        row.addWidget(self.btn_more, 0)
        row.addItem(QSpacerItem(20, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
        lt.addLayout(row)

        hint = QLabel("As mudanças de tema são aplicadas imediatamente, com transição suave.")
        hint.setWordWrap(True)
        lt.addWidget(hint)

        root.addWidget(card_theme)

        # ===== Geral =====
        card_general = QFrame(self)
        card_general.setObjectName("OuterPanel")
        lg = QVBoxLayout(card_general)
        lg.setContentsMargins(10, 10, 10, 10)
        lg.setSpacing(8)

        hdr_g = QLabel("Geral")
        hdr_g.setProperty("subtle", True)
        lg.addWidget(hdr_g)

        # Toggle Splash
        splash_row = QHBoxLayout()
        splash_row.setContentsMargins(0, 0, 0, 0)
        splash_row.setSpacing(8)

        # checked = pular splash => gravar splash=False
        self.tgl_splash = Controls.Toggle(width=34, height=18)
        show_splash = bool(self._st.read("splash", True))  # default: True (mostrar)
        self.tgl_splash.setChecked(not show_splash)        # marcado => NÃO mostrar

        self.lbl_splash = QLabel()
        def _update_splash_label(checked: bool):
            self.lbl_splash.setText(
                "Splash de inicialização desativada" if checked
                else "Mostrar splash na inicialização"
            )

        _update_splash_label(self.tgl_splash.isChecked())

        def _on_toggle(v: bool):
            # salva invertido: v=True (toggle ligado) => splash False (não mostrar)
            self._st.write("splash", not v)
            _update_splash_label(v)

        self.tgl_splash.toggled.connect(_on_toggle)

        splash_row.addWidget(self.tgl_splash)
        splash_row.addWidget(self.lbl_splash)
        splash_row.addStretch(1)
        lg.addLayout(splash_row)

        placeholder = QLabel("Mais opções em breve…")
        placeholder.setStyleSheet("opacity:0.7; font-size:11px;")
        lg.addWidget(placeholder)

        root.addWidget(card_general)
        root.addStretch(1)

        # carregar + ligar combo
        self._reload()
        self.combo.currentTextChanged.connect(
            lambda name: self.tm.apply(name, animate=True, persist=True)
        )

    # ---------- helpers (frameless dialogs) ----------
    def _prompt_text(self, title: str, label: str, initial: str = "") -> tuple[str, bool]:
        """Dialogo frameless simples para entrada de texto."""
        dlg = FramelessDialog(self)
        root = QWidget(dlg)
        v = QVBoxLayout(root); v.setContentsMargins(12, 12, 12, 12); v.setSpacing(10)

        tb = TitleBar(title, parent=root)
        dlg.connect_titlebar(tb)
        v.addWidget(tb)

        v.addWidget(QLabel(label, root))
        edit = QLineEdit(root)
        edit.setText(initial)
        v.addWidget(edit)

        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        btn_ok = QPushButton("OK", root); btn_cancel = QPushButton("Cancel", root)
        btn_ok.clicked.connect(dlg.accept); btn_cancel.clicked.connect(dlg.reject)
        btn_row.addStretch(1); btn_row.addWidget(btn_ok); btn_row.addWidget(btn_cancel)
        v.addLayout(btn_row)

        dlg.setCentralWidget(root)
        dlg.resize(420, 220)
        dlg.shrink_to(QSize(420, 220), center=False)

        ok = dlg.exec() == QDialog.Accepted
        return edit.text(), ok

    def _confirm(self, title: str, message: str) -> bool:
        """Dialogo frameless de confirmação OK/Cancel."""
        dlg = FramelessDialog(self)
        root = QWidget(dlg)
        v = QVBoxLayout(root); v.setContentsMargins(12, 12, 12, 12); v.setSpacing(10)

        tb = TitleBar(title, parent=root)
        dlg.connect_titlebar(tb)
        v.addWidget(tb)

        lab = QLabel(message, root); lab.setWordWrap(True)
        v.addWidget(lab)

        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        btn_ok = QPushButton("OK", root); btn_cancel = QPushButton("Cancel", root)
        btn_ok.clicked.connect(dlg.accept); btn_cancel.clicked.connect(dlg.reject)
        btn_row.addStretch(1); btn_row.addWidget(btn_ok); btn_row.addWidget(btn_cancel)
        v.addLayout(btn_row)

        dlg.setCentralWidget(root)
        dlg.resize(420, 200)
        dlg.shrink_to(QSize(420, 200), center=False)

        return dlg.exec() == QDialog.Accepted

    def _info(self, title: str, message: str) -> None:
        """Dialogo frameless informativo com um botão OK."""
        dlg = FramelessDialog(self)
        root = QWidget(dlg)
        v = QVBoxLayout(root); v.setContentsMargins(12, 12, 12, 12); v.setSpacing(10)

        tb = TitleBar(title, parent=root)
        dlg.connect_titlebar(tb)
        v.addWidget(tb)

        lab = QLabel(message, root); lab.setWordWrap(True)
        v.addWidget(lab)

        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        btn_ok = QPushButton("OK", root)
        btn_ok.clicked.connect(dlg.accept)
        btn_row.addStretch(1); btn_row.addWidget(btn_ok)
        v.addLayout(btn_row)

        dlg.setCentralWidget(root)
        dlg.resize(420, 180)
        dlg.shrink_to(QSize(420, 180), center=False)
        dlg.exec()

    # ---------- data/load ----------
    def _reload(self):
        current = self.tm.current() or self.tm.load_selected_from_settings()
        names = self.tm.available() or []

        self.combo.blockSignals(True)
        self.combo.clear()
        self.combo.addItems(names)
        if current in names:
            self.combo.setCurrentText(current)
        elif names:
            self.combo.setCurrentIndex(0)
        self.combo.blockSignals(False)

    # ---------- actions ----------
    def _new_theme(self):
        name, ok = self._prompt_text("Novo tema", "Nome do tema:")
        if not ok or not name.strip():
            return
        name = name.strip()

        if name in (self.tm.available() or []):
            self._info("Tema existente", f"Já existe um tema chamado '{name}'.")
            return

        base_name = self.tm.current() or (self.tm.available()[0] if self.tm.available() else None)
        base_props = self.tm._repo.load_theme(base_name) if base_name else {}

        dlg = ThemeEditorDialog(name, base_props, self)
        if dlg.exec():
            try:
                new_data = dlg.get_theme_data()
            except AttributeError:
                new_data = {"vars": getattr(dlg, "props", {})}

            self.tm._repo.save_theme(name, new_data)
            self._reload()
            self.tm.apply(name, animate=True, persist=True)

    def _edit_theme(self):
        name = self.combo.currentText().strip()
        if not name:
            return
        props = self.tm._repo.load_theme(name)
        dlg = ThemeEditorDialog(name, props, self)
        if dlg.exec():
            try:
                new_data = dlg.get_theme_data()
            except AttributeError:
                new_data = {"vars": getattr(dlg, "props", {})}
            self.tm._repo.save_theme(name, new_data)
            self.tm.apply(name, animate=True, persist=True)
            self._reload()

    def _delete_theme(self):
        name = self.combo.currentText().strip()
        if not name:
            return
        names = self.tm.available() or []
        if len(names) <= 1:
            self._info("Não permitido", "Você não pode excluir o único tema disponível.")
            return
        if not self._confirm("Confirmar", f"Deseja excluir o tema '{name}'?"):
            return

        self.tm._repo.delete_theme(name)
        fallback_list = self.tm.available() or []
        if not fallback_list:
            self._reload()
            return
        fallback = fallback_list[0]
        self._reload()
        self.combo.setCurrentText(fallback)
        self.tm.apply(fallback, animate=True, persist=True)

    # ---------- factory ----------
    @staticmethod
    def build(task_runner=None, theme_service: ThemeService | None = None):
        if theme_service is None:
            raise ValueError("SettingsPage.build requer theme_service")
        return SettingsPage(theme_service)

# ====== FACTORY (nível de módulo) ======
def build(task_runner=None, theme_service=None):
    return SettingsPage.build(task_runner=task_runner, theme_service=theme_service)
