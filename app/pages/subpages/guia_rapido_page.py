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

        # Passo 4 — Exemplo de "Ver mais" (card)
        card_sec = _section(
            self,
            "Ver mais (card de tutorial)",
            "Card demonstrando recursos desta interface: navegação, atalhos e Quick Open."
        )
        cl = card_sec._content.layout()  # type: ignore[attr-defined]

        # Conteúdo do card
        card = QFrame(self)
        card.setFrameShape(QFrame.NoFrame)
        row = QHBoxLayout(card); row.setContentsMargins(8, 8, 8, 8); row.setSpacing(10)

        icon = QFrame(card); icon.setFixedSize(60, 60); icon.setStyleSheet("background:#111; border-radius:6px;")
        row.addWidget(icon, 0)

        col = QVBoxLayout(); col.setContentsMargins(0,0,0,0); col.setSpacing(4)
        h1 = QLabel("NAVEGAÇÃO", card); f=h1.font(); f.setBold(True); h1.setFont(f)
        p1 = QLabel("Rotas hierárquicas, breadcrumb clicável e histórico (Alt+←/Alt+→).", card); p1.setWordWrap(True)
        h2 = QLabel("ATALHOS", card); f2=h2.font(); f2.setBold(True); h2.setFont(f2)
        p2 = QLabel("Quick Open (Ctrl+K) para abrir páginas rapidamente.", card); p2.setWordWrap(True)
        col.addWidget(h1); col.addWidget(p1); col.addWidget(h2); col.addWidget(p2)
        row.addLayout(col, 1)

        # Botão expandir
        exp = Controls.ExpandMore(card)
        cl.addWidget(exp)
        root.addWidget(card_sec)

    # -------- Toolbar de exemplo --------
    def build_toolbar(self):
        tb = Controls.Toolbar(self)

        # Ações reais desta interface
        def mk_item(text, trigger=None, submenu=None, hover=True):
            return {"text": text, "trigger": trigger, "submenu": submenu, "hover": hover}

        def _win():
            w = self.window()
            return w if w and hasattr(w, "router") else None

        # Botão simples
        tb.add_button("Início", on_click=lambda: self._go("home"))

        # Navegar
        nav_items = [
            mk_item("Home", trigger=lambda: self._go("home")),
            mk_item("Ferramentas", trigger=lambda: self._go("home/ferramentas")),
            mk_item("Guia Rápido", trigger=lambda: self._go("home/guia")),
        ]
        tb.add_menu("Navegar", nav_items, open_mode="both")

        # Comandos do app
        def _open_quick_open():
            w = _win()
            if w and hasattr(w, "_open_quick_open"):
                w._open_quick_open()

        def _toggle_notif():
            w = _win()
            try:
                if w and hasattr(w, "topbar"):
                    w.topbar.openNotificationsRequested.emit()
            except Exception:
                pass

        def _toggle_settings():
            w = _win()
            if w and hasattr(w, "_toggle_settings_panel"):
                w._toggle_settings_panel()

        def _toggle_sidebar():
            w = _win()
            if w and hasattr(w, "_toggle_sidebar"):
                w._toggle_sidebar()

        comandos = [
            mk_item("Buscar (Ctrl+K)", trigger=_open_quick_open),
            mk_item("Notificações", trigger=_toggle_notif),
            mk_item("Configurações", trigger=_toggle_settings),
            mk_item("Menu", trigger=_toggle_sidebar),
        ]
        tb.add_menu("Comandos", comandos, open_mode="hover")

        # Dicas/atalhos — submenus em cascata
        kbd_nav = [
            mk_item("Voltar (Alt+←)", trigger=lambda: (_win() and _win().router.go_back())),
            mk_item("Avançar (Alt+→)", trigger=lambda: (_win() and _win().router.go_forward())),
        ]
        dicas = [
            mk_item("Atalhos de Navegação", submenu=kbd_nav),
            mk_item("Abrir Quick Open (Ctrl+K)", trigger=_open_quick_open),
        ]
        tb.add_menu("Ajuda", dicas, open_mode="hover")

        return tb

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
