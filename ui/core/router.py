# ui/core/router.py

from PySide6.QtWidgets import QStackedWidget, QWidget
from typing import Dict

class Router(QStackedWidget):
    def __init__(self, parent=None):
        super().__init__(parent)
        self._pages: Dict[str, QWidget] = {}

    def register(self, name: str, widget: QWidget):
        self._pages[name] = widget
        self.addWidget(widget)

    def go(self, name: str):
        self.setCurrentWidget(self._pages[name])
