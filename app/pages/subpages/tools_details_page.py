# app/pages/subpages/tools_details_page.py

from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from ui.widgets.buttons import Controls

PAGE = {
    "route": "home/tools2/detalhes",
    "label": "Detalhes (Ext)",
    "sidebar": False,   # NÃO aparece no Quick Open; acesso via 'tools2' ou histórico
    "order": 13,
}

class HomeToolsExternalDetailsPage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        root.addWidget(QLabel("Sub-Subpágina EXTERNA (home/tools2/detalhes)."))
        btn_up = Controls.Button("Voltar para Ferramentas (Ext)", self)
        btn_up.clicked.connect(lambda: self._go("home/tools2"))
        root.addWidget(btn_up)

        btn_home = Controls.Button("Voltar para Home", self)
        btn_home.clicked.connect(lambda: self._go("home"))
        root.addWidget(btn_home)

    def _go(self, path: str):
        try:
            r = getattr(self.window(), "router", None)
            if r:
                r.go(path)
        except Exception as e:
            print("[WARN] navegação falhou:", e)

def build(*args, **kwargs):
    return HomeToolsExternalDetailsPage()
