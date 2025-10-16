# ui/core/router.py

from __future__ import annotations

from typing import Dict, Optional
from PySide6.QtWidgets import QStackedWidget, QWidget


class Router(QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self.setObjectName("AppContentArea")
        self._pages: Dict[str, QWidget] = {}
        self._current_name: Optional[str] = None

    def register(self, name: str, widget: QWidget):
        if not name or not isinstance(widget, QWidget):
            raise ValueError("Rota inválida ou widget inválido.")
        self._pages[name] = widget
        self.addWidget(widget)

    def go(self, name: str, params: Optional[dict] = None):
        if name not in self._pages:
            raise KeyError(f"Rota '{name}' não registrada.")
        target = self._pages[name]
        self.setCurrentWidget(target)
        self._current_name = name
        # Se a página aceitar `on_route(params)`, chamamos (DIP)
        on_route = getattr(target, "on_route", None)
        if callable(on_route):
            try:
                on_route(params or {})
            except Exception as e:  # noqa: BLE001
                print(f"[WARN] on_route('{name}') falhou:", e)
