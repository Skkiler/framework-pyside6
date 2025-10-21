# ui/core/utils/theme_icon_watcher.py

from __future__ import annotations
from pathlib import Path

from PySide6.QtCore import QObject, QFileSystemWatcher, QEvent
from PySide6.QtGui import QIcon, QGuiApplication
from PySide6.QtWidgets import QApplication, QWidget

try:
    from app import settings as S
except Exception:
    S = None

_THEME_CHANGE_EVENTS = tuple(
    e for e in (
        getattr(QEvent, "PaletteChange", None),
        getattr(QEvent, "ApplicationPaletteChange", None),
        getattr(QEvent, "StyleChange", None),
    ) if e is not None
)

class ThemeIconWatcher(QObject):
    """
    Observa mudanças de tema (eventos Qt e alterações no _ui_exec_settings.json)
    e atualiza o ícone do target (e opcionalmente o global) usando settings.resolve_app_icon_path().
    """
    def __init__(self, target: QWidget, *, apply_globally: bool = True):
        super().__init__(target)
        self._target = target
        self._apply_globally = apply_globally
        self._watcher: QFileSystemWatcher | None = None

        # aplica imediatamente
        self.apply_icon()

        # observa mudanças de tema via eventos Qt
        try:
            self._target.installEventFilter(self)
        except Exception:
            pass

        # observa o arquivo de execução (Windows/editores recriam o arquivo)
        try:
            if S and getattr(S, "CACHE_DIR", None):
                json_path = (S.CACHE_DIR / "_ui_exec_settings.json")
                if json_path.exists():
                    self._watcher = QFileSystemWatcher([str(json_path)])
                    self._watcher.fileChanged.connect(self._on_exec_file_changed)
        except Exception:
            self._watcher = None

    # ---- eventos
    def eventFilter(self, watched, event):
        if watched is self._target and event.type() in _THEME_CHANGE_EVENTS:
            self.apply_icon()
        return super().eventFilter(watched, event)

    # ---- reações
    def _on_exec_file_changed(self, changed_path: str):
        # Alguns editores substituem o arquivo → reanexa o watch se necessário
        try:
            p = Path(changed_path)
            if self._watcher and p.exists():
                if str(p) not in set(self._watcher.files()):
                    self._watcher.addPath(str(p))
        except Exception:
            pass
        self.apply_icon()

    # ---- núcleo
    def apply_icon(self):
        if not S or not hasattr(S, "resolve_app_icon_path"):
            return
        try:
            p = S.resolve_app_icon_path()
        except Exception:
            p = None

        if p and Path(p).exists():
            icon = QIcon(str(p))
            try:
                self._target.setWindowIcon(icon)
            except Exception:
                pass

            if self._apply_globally:
                try:
                    QGuiApplication.setWindowIcon(icon)
                except Exception:
                    pass
                # força atualização visual em janelas já abertas
                for w in QApplication.topLevelWidgets():
                    try:
                        w.setWindowIcon(icon)
                    except Exception:
                        pass
