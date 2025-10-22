# ui/pages/subpages/guia_rapido_page.py

from __future__ import annotations

from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout
from PySide6.QtCore import Qt

from ui.widgets.buttons import Controls

PAGE = {
    "route": "home/guia",
    "label": "Guia Rápido",
    "sidebar": True,     # aparece no Quick Open e na sidebar (se você registrar)
    "order": 5,
}

def _section(parent: QWidget, title: str, subtitle: str | None = None) -> QFrame:
    frame = QFrame(parent)
    frame.setProperty("elevation", "panel")
    outer = QVBoxLayout(frame)
    outer.setContentsMargins(14, 12, 14, 14)
    outer.setSpacing(8)

    t = QLabel(title, frame)
    f = t.font(); f.setPointSize(max(13, f.pointSize())); f.setBold(True)
    t.setFont(f)
    outer.addWidget(t)

    if subtitle:
        s = QLabel(subtitle, frame)
        s.setWordWrap(True)
        s.setStyleSheet("opacity: 0.85;")
        outer.addWidget(s)

    content = QFrame(frame)
    inner = QVBoxLayout(content)
    inner.setContentsMargins(0, 6, 0, 0)
    inner.setSpacing(10)
    outer.addWidget(content)

    content.setObjectName("_section_content")
    frame._content = content  # type: ignore[attr-defined]
    return frame


class QuickGuidePage(QWidget):
    """
    Guia rápido, com passos curtos para explorar as principais features.
    """
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(14)

        hero = _section(
            self,
            "Guia Rápido",
            "Aprenda o essencial em minutos: navegação, histórico, Quick Open e páginas externas."
        )
        h_lay = hero._content.layout()  # type: ignore[attr-defined]

        chips = QHBoxLayout()
        for t in ("Rotas", "Breadcrumb", "Histórico", "Quick Open", "Subpáginas"):
            btn = Controls.Button(t); btn.setProperty("variant", "chip"); chips.addWidget(btn)
        chips.addStretch(1)
        h_lay.addLayout(chips)
        root.addWidget(hero)

        # Passo 1 — navegação
        step1 = _section(
            self,
            "1) Navegue por níveis",
            "Clique abaixo para ir a uma subpágina, observe o breadcrumb e use Alt+←/Alt+→."
        )
        s1 = step1._content.layout()  # type: ignore[attr-defined]
        row1 = QHBoxLayout()
        go_tools = Controls.Button("Ir para Ferramentas (home/ferramentas)")
        go_tools.setProperty("variant", "primary")
        go_tools.clicked.connect(lambda: self._go("home/ferramentas"))
        row1.addWidget(go_tools)
        row1.addStretch(1)
        s1.addLayout(row1)
        root.addWidget(step1)

        # Passo 2 — Quick Open
        step2 = _section(
            self,
            "2) Use o Quick Open",
            "Pressione Ctrl+K e digite parte do nome/rota. Somente rotas com sidebar=True são listadas."
        )
        step2._content.layout().addWidget(QLabel("Experimente procurar por “Guia” ou “Ferramentas”."))
        root.addWidget(step2)

        # Passo 3 — páginas externas
        step3 = _section(
            self,
            "3) Subpágina externa",
            "Este arquivo está em ui/pages/subpages/. Você pode criar outras páginas completas fora do home_page "
            "e referenciá-las por rota (ex.: home/guia, reports/overview etc.)."
        )
        s3 = step3._content.layout()  # type: ignore[attr-defined]
        row3 = QHBoxLayout()
        back_home = Controls.Button("Voltar ao Início")
        back_home.clicked.connect(lambda: self._go("home"))
        row3.addWidget(back_home)
        row3.addStretch(1)
        s3.addLayout(row3)
        root.addWidget(step3)

    def _go(self, path: str):
        win = self.window()
        r = getattr(win, "router", None)
        if r:
            try:
                r.go(path)
            except Exception as e:
                print("[WARN] navegação falhou:", e)


def build(*_, **__) -> QWidget:
    return QuickGuidePage()
