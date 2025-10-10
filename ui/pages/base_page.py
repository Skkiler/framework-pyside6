# ui/pages/base_page.py

from typing import Protocol

class BasePage(Protocol):
    def on_enter(self): ...
    def on_leave(self): ...
