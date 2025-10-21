# app/pages/subpages/tools_page.py

from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel
from ui.widgets.buttons import Controls

PAGE = {
    "route": "home/tools2",      # <- subpágina de 'home' (rota hierárquica)
    "label": "Ferramentas (Ext)",
    "sidebar": True,             # aparece no Quick Open; pode ou não aparecer na sidebar
    "order": 12,
}

class HomeToolsExternalPage(QWidget):
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        root.addWidget(QLabel("Subpágina EXTERNA de Home (home/tools2)."))
        btn = Controls.Button("Ir para Detalhes (home/tools2/detalhes)", self)
        btn.clicked.connect(lambda: self._go("home/tools2/detalhes"))
        root.addWidget(btn)

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
    return HomeToolsExternalPage()
