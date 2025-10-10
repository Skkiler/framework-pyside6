# ui/core/router.py

from PySide6.QtWidgets import QStackedWidget, QWidget
from typing import Dict, Optional

class Router(QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AppContentArea")
        self._pages: Dict[str, QWidget] = {}
        self._current_name: Optional[str] = None

    def register(self, name: str, widget: QWidget):
        self._pages[name] = widget
        self.addWidget(widget)

    def go(self, name: str, params: Optional[dict] = None):
        if name not in self._pages:
            raise KeyError(f"Rota '{name}' não registrada.")

        # on_leave da atual (se existir)
        if self._current_name:
            cur = self._pages.get(self._current_name)
            if cur and hasattr(cur, "on_leave"):
                try:
                    cur.on_leave()
                except Exception:
                    pass

        # troca de página
        target = self._pages[name]
        self.setCurrentWidget(target)
        self._current_name = name

        # on_enter da nova (se existir)
        if hasattr(target, "on_enter"):
            try:
                if params is None:
                    target.on_enter()
                else:
                    target.on_enter(params)
            except TypeError:
                try:
                    target.on_enter()
                except Exception:
                    pass
            except Exception:
                pass
