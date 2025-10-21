# ui/pages/base_page.py

from typing import Protocol

PAGE = {
    "route": "Settings",
    "label": "Configurações",
    "sidebar": False,
    "order": 99,
}
class BasePage(Protocol):
    def on_enter(self): ...
    def on_leave(self): ...
