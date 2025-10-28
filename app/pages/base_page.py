# ui/pages/base_page.py

from ui.core.utils.helpers import *
from typing import Protocol

PAGE = {
    "route": "Settings",
    "label": "Configurações",
    "sidebar": False,
    "order": 99,
}

class BasePage(Protocol):
    """
    Interface base para páginas customizadas.
    Use on_enter/on_leave para lógica de ciclo de vida.
    """
    def on_enter(self): ...
    def on_leave(self): ...
