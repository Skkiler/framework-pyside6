# ui/pages/home_page.py

from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from PySide6.QtCore import QTimer

from ..widgets.buttons import Controls, command_button
from ..widgets.async_button import AsyncTaskButton
from ..widgets.toast import show_toast

PAGE = {
    "route": "home",
    "label": "Início",
    "sidebar": True,
    "order": 1,
}

class HomePage(QWidget):
    def __init__(self, task_runner):
        super().__init__()
        lay = QVBoxLayout(self)
        lay.setContentsMargins(14, 14, 14, 14)
        lay.setSpacing(10)

        lay.addWidget(QLabel("Bem-vindo! Esta é a Home."))

        # Botão síncrono padrão (já usa Hover “glow”)
        lay.addWidget(
            command_button(
                "Rodar processo A (rápido)",
                "proc_A",
                task_runner,
                {"fast": True},
            )
        )

        # Botão assíncrono existente
        btn_async = AsyncTaskButton(
            "Dormir 5s (assíncrono)",
            SleepRunner(),
            "ignored",
            {},
            parent=self,
            toast_success="Concluído!",
            toast_error="Falhou",
            use_overlay=True,
            overlay_parent=self,
            overlay_message="Processando dados…"
        )
        lay.addWidget(btn_async)

        # exemplos dos novos controles padrões:
        lay.addWidget(QLabel("Exemplos de controles:"))
        lay.addWidget(Controls.Toggle(self))
        lay.addWidget(Controls.TextInput("Digite algo…", self))

        self._toast_scheduled = False

    def showEvent(self, e):
        super().showEvent(e)
        if not self._toast_scheduled:
            self._toast_scheduled = True
            QTimer.singleShot(
                0,
                lambda: show_toast(
                    self.window(),
                    "Dica: experimente o botão assíncrono",
                    "info",
                    2200,
                ),
            )

    @staticmethod
    def build(task_runner=None, theme_service=None):
        return HomePage(task_runner)

# ====== FACTORY para o registry ======
def build(task_runner=None, theme_service=None):
    return HomePage.build(task_runner=task_runner, theme_service=theme_service)

class SleepRunner:
    def run_task(self, name: str, payload: dict) -> dict:
        import time
        time.sleep(5)                 # “trabalho”
        return {"ok": True, "code": 1, "data": {"message": "ok"}}
