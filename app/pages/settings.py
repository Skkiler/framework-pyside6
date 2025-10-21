# ui/pages/settings.py

from __future__ import annotations

from pathlib import Path
import re

from PySide6.QtCore import Qt, QSize, QTimer
from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QComboBox,
    QHBoxLayout, QFrame, QSpacerItem, QSizePolicy,
    QMenu, QDialog, QLineEdit, QPushButton, QToolButton
)

from ui.core.theme_service import ThemeService
from ui.widgets.buttons import Controls
from .theme_editor import ThemeEditorDialog
from ui.core.frameless_window import FramelessDialog
from ui.widgets.titlebar import TitleBar

# onde estão os temas; tenta vir de app.settings, cai para ui/assets/themes
try:
    import app.settings as cfg
    THEMES_DIR_FALLBACK = Path(cfg.THEMES_DIR)
except Exception:
    THEMES_DIR_FALLBACK = Path(__file__).resolve().parents[2] / "assets" / "themes"

PAGE = {
    "route": "Settings",
    "label": "Configurações",
    "sidebar": False,
    "order": 99,
}

# paleta neutra para novos temas
NEUTRAL_VARS = {
    "bg_start": "#222222",
    "bg_end": "#2E2E2E",
    "bg": "#242424",
    "surface": "#2F2F2F",
    "text": "#E8E8E8",
    "text_hover": "#FFFFFF",
    "btn": "#5A5A5A",
    "btn_hover": "#6A6A6A",
    "btn_text": "#FFFFFF",
    "hover": "#505050",
    "accent": "#808080",
    "input_bg": "#151515",
    "box_border": "#666666",
    "checkbox": "#C0C0C0",
    "slider": "#C0C0C0",
    "cond_selected": "#3B3B3B",
    "window_bg": "#242424",
}

def _slugify(name: str) -> str:
    s = re.sub(r"\s+", "_", name.strip())
    s = re.sub(r"[^A-Za-z0-9_\-]", "", s)
    return s[:64] or "novo_tema"


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
        self.combo.setSizePolicy(QSizePolicy.Expanding, QSizePolicy.Fixed)
        self.combo.setMinimumWidth(160)
        self.combo.setMaximumWidth(16777215)
        row.addWidget(self.combo, 1)

        # Botão "…" — QToolButton com menu nativo (InstantPopup)
        self.btn_more = QToolButton(self)
        self.btn_more.setObjectName("TinyMenuButton")
        self.btn_more.setText("…")
        self.btn_more.setToolTip("Opções de tema")
        self.btn_more.setAutoRaise(True)
        self.btn_more.setCursor(Qt.PointingHandCursor)
        self.btn_more.setFixedSize(26, 26)
        self.btn_more.setPopupMode(QToolButton.InstantPopup)

        menu = QMenu(self.btn_more)
        menu.setObjectName("ContextMenu")
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

        self.tgl_splash = Controls.Toggle(width=34, height=18)
        show_splash = bool(self._st.read("splash", True))
        self.tgl_splash.setChecked(not show_splash)

        self.lbl_splash = QLabel()
        def _update_splash_label(checked: bool):
            self.lbl_splash.setText(
                "Splash de inicialização desativada" if checked
                else "Mostrar splash na inicialização"
            )
        _update_splash_label(self.tgl_splash.isChecked())

        def _on_toggle(v: bool):
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

        # carregar + ligar combo (usando FS como fonte de verdade)
        self._reload()
        self.combo.currentTextChanged.connect(
            lambda name: self.tm.apply(name, animate=True, persist=True)
        )

        # >>> NOVO: se alguém criar/apagar/renomear/editar via ThemeService,
        # a lista reflete imediatamente (sem reiniciar app).
        self.tm.themesChanged.connect(lambda _names: self._reload())

    # ---------- helpers (frameless dialogs) ----------
    def _prompt_text(self, title: str, label: str, initial: str = "") -> tuple[str, bool]:
        dlg = FramelessDialog(self)
        root = QWidget(dlg)
        v = QVBoxLayout(root); v.setContentsMargins(12, 12, 12, 12); v.setSpacing(10)

        tb = TitleBar(title, parent=root)
        dlg.connect_titlebar(tb)
        v.addWidget(tb)

        v.addWidget(QLabel(label, root))
        edit = QLineEdit(root); edit.setText(initial)
        v.addWidget(edit)

        btn_row = QHBoxLayout(); btn_row.setSpacing(8)
        btn_ok = QPushButton("OK", root); btn_cancel = QPushButton("Cancel", root)
        btn_ok.clicked.connect(dlg.accept); btn_cancel.clicked.connect(dlg.reject)
        btn_row.addStretch(1); btn_row.addWidget(btn_ok); btn_row.addWidget(btn_cancel)
        v.addLayout(btn_row)

        dlg.setCentralWidget(root)
        dlg.resize(420, 220); dlg.shrink_to(QSize(420, 220), center=False)
        ok = dlg.exec() == QDialog.Accepted
        return edit.text(), ok

    def _confirm(self, title: str, message: str) -> bool:
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
        dlg.resize(420, 200); dlg.shrink_to(QSize(420, 200), center=False)
        return dlg.exec() == QDialog.Accepted

    def _info(self, title: str, message: str) -> None:
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
        dlg.resize(420, 180); dlg.shrink_to(QSize(420, 180), center=False)
        dlg.exec()

    # ---------- fonte de verdade: diretório de temas ----------
    def _repo_themes_dir(self) -> Path:
        """Tenta descobrir a pasta usada pelo repositório; cai no fallback."""
        repo = getattr(self.tm, "_repo", None)
        # incluir 'theme_dir' (singular), que é o atributo do JsonThemeRepository
        for attr in ("theme_dir", "themes_dir", "themes_path", "base_dir", "root", "dir", "path"):
            p = getattr(repo, attr, None)
            if isinstance(p, (str, Path)):
                pp = Path(p)
                if pp.exists():
                    return pp
        return THEMES_DIR_FALLBACK

    def _scan_fs_names(self) -> list[str]:
        d = self._repo_themes_dir()
        d.mkdir(parents=True, exist_ok=True)
        return sorted(p.stem for p in d.glob("*.json"))

    def _default_theme_name(self, names: list[str]) -> str:
        for attr in ("default_theme_name", "default", "DEFAULT_THEME", "DEFAULT"):
            val = getattr(self.tm, attr, None)
            if isinstance(val, str) and val in names:
                return val
        for guess in ("default", "Default", "samurai", "Samurai"):
            if guess in names:
                return guess
        return names[0] if names else ""

    # ---------- data/load ----------
    def _reload(self, select: str | None = None):
        """Recarrega SEM cache, usando o ThemeService como fonte de verdade."""
        names = sorted(self.tm.available())
        current = select or self.tm.current() or self.tm.load_selected_from_settings()

        self.combo.blockSignals(True)
        self.combo.clear()
        self.combo.addItems(names)
        if current in names:
            self.combo.setCurrentText(current)
        elif names:
            self.combo.setCurrentIndex(0)
        self.combo.blockSignals(False)

    # ---------- abrir editor (usando exec() via singleShot) ----------
    def _open_theme_editor(self, name: str, props: dict, on_accept=None):
        dlg = ThemeEditorDialog(name, props, self)
        result = dlg.exec()
        if on_accept and result == QDialog.Accepted:
            on_accept(dlg)

    # ---------- actions ----------
    def _new_theme(self):
        raw, ok = self._prompt_text("Novo tema", "Nome do tema:")
        if not ok or not raw.strip():
            return

        name = _slugify(raw)
        if name in (self._scan_fs_names() or []):
            self._info("Tema existente", f"Já existe um tema chamado '{name}'.")
            return

        # cria tema neutro e salva via serviço (façade)
        initial = {"vars": dict(NEUTRAL_VARS)}
        self.tm.save_theme(name, initial)

        # abre editor; ao aceitar, salva alterações e aplica
        def _accepted(dlg: ThemeEditorDialog):
            try:
                new_data = dlg.get_theme_data()
            except AttributeError:
                new_data = {"vars": getattr(dlg, "props", {})}
            self.tm.save_theme(name, new_data)
            self._reload(select=name)
            self.tm.apply(name, animate=True, persist=True)

        self._open_theme_editor(name, initial, on_accept=_accepted)
        # lista deve refletir imediatamente o novo arquivo
        self._reload(select=name)

    def _edit_theme(self):
        name = self.combo.currentText().strip()
        if not name:
            return
        props = self.tm.load_theme(name)

        def _accepted(dlg: ThemeEditorDialog):
            try:
                new_data = dlg.get_theme_data()
            except AttributeError:
                new_data = {"vars": getattr(dlg, "props", {})}
            self.tm.save_theme(name, new_data)
            self.tm.apply(name, animate=True, persist=True)
            self._reload(select=name)

        self._open_theme_editor(name, props, on_accept=_accepted)

    def _delete_theme(self):
        name = self.combo.currentText().strip()
        if not name:
            return

        names = self._scan_fs_names()
        if len(names) <= 1:
            self._info("Não permitido", "Você não pode excluir o único tema disponível.")
            return

        default_name = self._default_theme_name(names)
        if name == default_name:
            self._info("Não permitido", f"O tema padrão ('{default_name}') não pode ser excluído.")
            return

        if not self._confirm("Confirmar", f"Deseja excluir o tema '{name}'?"):
            return

        self.tm.delete_theme(name)

        # recarrega do FS e aplica o padrão (ou primeiro disponível)
        names_after = self._scan_fs_names()
        if not names_after:
            # segurança: restaura um tema neutro como padrão
            fallback = "default"
            self.tm.save_theme(fallback, {"vars": dict(NEUTRAL_VARS)})
            names_after = [fallback]

        apply_name = default_name if default_name in names_after else names_after[0]
        self._reload(select=apply_name)
        self.tm.apply(apply_name, animate=True, persist=True)

    # ---------- factory ----------
    @staticmethod
    def build(task_runner=None, theme_service: ThemeService | None = None):
        if theme_service is None:
            raise ValueError("SettingsPage.build requer theme_service")
        return SettingsPage(theme_service)


def build(task_runner=None, theme_service=None):
    return SettingsPage.build(task_runner=task_runner, theme_service=theme_service)
