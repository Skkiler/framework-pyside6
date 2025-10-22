# ui/pages/home_page.py

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout, QGridLayout, QSizePolicy
)
from PySide6.QtCore import QTimer, Qt

from ui.widgets.buttons import Controls, command_button
from ui.widgets.async_button import AsyncTaskButton
from ui.widgets.toast import show_toast, ProgressToast

PAGE = {
    "route": "home",
    "label": "Início",
    "sidebar": True,
    "order": 0,
}

# ------------------------------------------------------------
# Helpers visuais
# ------------------------------------------------------------
def _section(parent: QWidget, title: str, subtitle: str | None = None) -> QFrame:
    """
    Card de conteúdo com título (e opcionalmente subtítulo).
    """
    frame = QFrame(parent)
    frame.setProperty("elevation", "panel")

    outer = QVBoxLayout(frame)
    outer.setContentsMargins(14, 12, 14, 14)
    outer.setSpacing(8)

    # Título
    title_lbl = QLabel(title, frame)
    f = title_lbl.font()
    f.setPointSize(max(13, f.pointSize()))
    f.setBold(True)
    title_lbl.setFont(f)
    outer.addWidget(title_lbl)

    # Subtítulo opcional
    if subtitle:
        sub = QLabel(subtitle, frame)
        sub.setWordWrap(True)
        sub.setStyleSheet("opacity: 0.85;")
        outer.addWidget(sub)

    # Conteúdo
    content = QFrame(frame)
    content.setFrameShape(QFrame.NoFrame)
    inner = QVBoxLayout(content)
    inner.setContentsMargins(0, 4, 0, 0)
    inner.setSpacing(10)
    outer.addWidget(content)

    content.setObjectName("_section_content")
    frame._content = content  # type: ignore[attr-defined]
    return frame


def _chip(text: str) -> Controls.Button:
    btn = Controls.Button(text)
    btn.setProperty("variant", "chip")
    btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
    return btn


# ============================================================
# Subpágina 1 (embutida): home/ferramentas
# ============================================================
class HomeToolsPage(QWidget):
    """
    Subpágina direta de 'home' (home/ferramentas) — exemplo de conteúdo e navegação.
    """
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        hero = _section(self, "Ferramentas", "Exemplo de subpágina embutida em home.")
        lay = hero._content.layout()  # type: ignore[attr-defined]

        tips = QLabel("• Use o breadcrumb no topo para voltar rapidamente.\n"
                      "• Este exemplo também mostra navegação entre níveis.")
        tips.setWordWrap(True)
        lay.addWidget(tips)

        row = QHBoxLayout()
        row.setSpacing(8)
        bt1 = Controls.Button("Abrir Detalhes")
        bt1.setProperty("variant", "primary")
        bt1.clicked.connect(lambda: self._go("home/ferramentas/detalhes"))
        row.addWidget(bt1)

        bt2 = Controls.Button("Voltar à Home")
        bt2.clicked.connect(lambda: self._go("home"))
        row.addWidget(bt2)

        row.addStretch(1)
        lay.addLayout(row)

        root.addWidget(hero)

    def _go(self, path: str):
        win = self.window()
        r = getattr(win, "router", None)
        if r:
            try:
                r.go(path)
            except Exception as e:
                print("[WARN] navegação falhou:", e)


def build_home_tools(*_, **__) -> QWidget:
    return HomeToolsPage()


# ============================================================
# Subpágina 2 (embutida): home/ferramentas/detalhes
# ============================================================
class HomeToolsDetailsPage(QWidget):
    """
    Sub-subpágina (home/ferramentas/detalhes) — mostra ações e micro-conteúdo.
    """
    def __init__(self):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        sec = _section(self, "Detalhes", "Nível 2 da navegação a partir de ‘Ferramentas’.")
        lay = sec._content.layout()  # type: ignore[attr-defined]

        grid = QGridLayout()
        grid.setHorizontalSpacing(8)
        grid.setVerticalSpacing(6)

        grid.addWidget(_chip("Breadcrumb"), 0, 0)
        grid.addWidget(_chip("Histórico"), 0, 1)
        grid.addWidget(_chip("Ctrl+K"),     0, 2)

        desc = QLabel("Explore como a navegação hierárquica funciona e como o histórico "
                      "(Alt+←/Alt+→) respeita os passos entre páginas.")
        desc.setWordWrap(True)
        grid.addWidget(desc, 1, 0, 1, 3)

        lay.addLayout(grid)

        row = QHBoxLayout()
        row.setSpacing(8)
        back = Controls.Button("↩ Voltar")
        back.clicked.connect(lambda: self._go("home/ferramentas"))
        row.addWidget(back)

        home = Controls.Button("Início")
        home.clicked.connect(lambda: self._go("home"))
        row.addWidget(home)
        row.addStretch(1)
        lay.addLayout(row)

        root.addWidget(sec)

    def _go(self, path: str):
        win = self.window()
        r = getattr(win, "router", None)
        if r:
            try:
                r.go(path)
            except Exception as e:
                print("[WARN] navegação falhou:", e)


def build_home_tools_details(*_, **__) -> QWidget:
    return HomeToolsDetailsPage()


# ============================================================
# Página Home (raiz) — tutorial bonito
# ============================================================
class HomePage(QWidget):
    def __init__(self, task_runner):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(14)

        # -----------------------------------------------------
        # HERO
        # -----------------------------------------------------
        hero = _section(
            self,
            "Bem-vindo 👋",
            "Este projeto traz um shell com Router, TopBar (breadcrumb), histórico, Quick Open (Ctrl+K), "
            "ThemeService, Settings, toasts e comandos. Esta Home é um guia interativo."
        )
        hero_lay = hero._content.layout()  # type: ignore[attr-defined]

        chips = QHBoxLayout()
        chips.setSpacing(6)
        for t in ("Router", "Breadcrumb", "Histórico", "Quick Open", "Toasts", "Async"):
            chips.addWidget(_chip(t))
        chips.addStretch(1)
        hero_lay.addLayout(chips)

        cta_row = QHBoxLayout()
        cta_row.setSpacing(8)
        goto_tools = Controls.Button("▶ Abrir Ferramentas")
        goto_tools.setProperty("variant", "primary")
        goto_tools.clicked.connect(lambda: self._go("home/ferramentas"))
        cta_row.addWidget(goto_tools)

        goto_guide = Controls.Button("📘 Guia Rápido (Subpágina externa)")
        goto_guide.clicked.connect(lambda: self._go("home/guia"))
        cta_row.addWidget(goto_guide)

        cta_row.addStretch(1)
        hero_lay.addLayout(cta_row)

        root.addWidget(hero)

        # -----------------------------------------------------
        # Navegação (conceitos)
        # -----------------------------------------------------
        nav = _section(
            self,
            "Navegação & Rotas",
            "Rotas são hierárquicas (ex.: home/ferramentas/detalhes), o breadcrumb mostra o caminho "
            "e é clicável. Use Alt+←/Alt+→ para voltar/avançar. A última rota é restaurada ao abrir o app."
        )
        nav_lay = nav._content.layout()  # type: ignore[attr-defined]

        nav_buttons = QHBoxLayout()
        b1 = Controls.Button("Ir para Ferramentas (home/ferramentas)")
        b1.clicked.connect(lambda: self._go("home/ferramentas"))
        nav_buttons.addWidget(b1)

        b2 = Controls.Button("Ir para Detalhes (home/ferramentas/detalhes)")
        b2.clicked.connect(lambda: self._go("home/ferramentas/detalhes"))
        nav_buttons.addWidget(b2)

        nav_buttons.addStretch(1)
        nav_lay.addLayout(nav_buttons)

        tip_nav = QLabel("Dica: clique nos itens do breadcrumb para saltar direto para um nível específico.")
        tip_nav.setWordWrap(True)
        nav_lay.addWidget(tip_nav)
        root.addWidget(nav)

        # -----------------------------------------------------
        # Quick Open
        # -----------------------------------------------------
        qopen = _section(
            self,
            "Quick Open (Ctrl+K) — estilizado",
            "Pressione Ctrl+K para abrir o Quick Open frameless (mesmo tema), filtrando por nome/rota. "
            "Somente páginas com 'sidebar=True' aparecem."
        )
        qopen_lay = qopen._content.layout()  # type: ignore[attr-defined]
        qopen_lay.addWidget(QLabel("Experimente: digite “Ferramentas” ou “home/…”."))
        root.addWidget(qopen)

        # -----------------------------------------------------
        # Ações / Async / Toasts
        # -----------------------------------------------------
        actions = _section(
            self,
            "Ações e Execução",
            "Abaixo há exemplos de execução síncrona e assíncrona, com overlay e toasts de feedback."
        )
        a_lay = actions._content.layout()  # type: ignore[attr-defined]

        row_cmds = QHBoxLayout()
        row_cmds.setSpacing(8)
        row_cmds.addWidget(
            command_button("Rodar processo (Vazio)", "proc_A", task_runner, {"fast": True})
        )

        btn_async = AsyncTaskButton(
            "Dormir 5s (assíncrono, com overlay)",
            SleepRunner(),
            "ignored",
            {},
            parent=self,
            toast_success="Concluído!",
            toast_error="Falhou",
            use_overlay=True,
            block_input=True,
            overlay_parent=self,
            overlay_message="Processando dados…"
        )
        btn_async.setProperty("variant", "primary")
        row_cmds.addWidget(btn_async)
        row_cmds.addStretch(1)
        a_lay.addLayout(row_cmds)

        # Toasts
        toast_row = QHBoxLayout()
        toast_row.setSpacing(8)
        btn_toast_curto = Controls.Button("Toast Curto (5s)")
        btn_toast_curto.clicked.connect(self._demo_toast_curto)
        toast_row.addWidget(btn_toast_curto)

        btn_toast_andamento = Controls.Button("Toast com Progresso (1→5)")
        btn_toast_andamento.clicked.connect(self._demo_toast_contagem)
        toast_row.addWidget(btn_toast_andamento)
        toast_row.addStretch(1)
        a_lay.addLayout(toast_row)

        tip_actions = QLabel("Dica: ProgressToast aceita .set_progress(), .update(curr,total) e .finish().")
        tip_actions.setWordWrap(True)
        a_lay.addWidget(tip_actions)

        root.addWidget(actions)

        # -----------------------------------------------------
        # Controles diversos
        # -----------------------------------------------------
        ctrls = _section(self, "Controles rápidos")
        c_lay = ctrls._content.layout()  # type: ignore[attr-defined]
        c_lay.addWidget(Controls.Toggle(self))
        c_lay.addWidget(Controls.TextInput("Digite algo…", self))
        root.addWidget(ctrls)

        self._toast_scheduled = False

    # ------------------------------------------------------------------
    # Onboarding toast
    # ------------------------------------------------------------------
    def showEvent(self, e):
        super().showEvent(e)
        if not self._toast_scheduled:
            self._toast_scheduled = True
            QTimer.singleShot(
                0,
                lambda: show_toast(
                    self.window(),
                    "Dica: experimente o Quick Open (Ctrl+K) e o breadcrumb.",
                    "info",
                    2600,
                ),
            )

    # ------------------------------------------------------------------
    # Demos
    # ------------------------------------------------------------------
    def _demo_toast_curto(self):
        show_toast(self.window(), "Iniciando tarefa curta…", "info", 1600)
        QTimer.singleShot(
            5000,
            lambda: show_toast(self.window(), "Tarefa curta concluída!", "success", 2000)
        )

    def _demo_toast_contagem(self):
        total = 5
        pt = ProgressToast.start(self.window(), "Contagem: 0/5…", kind="info", cancellable=False)
        pt.set_progress(0)

        state = {"i": 0}
        def tick():
            state["i"] += 1
            i = state["i"]
            pt.update(i, total)
            pt.set_text(f"Contagem: {i}/{total}…")
            if i >= total:
                pt.finish(success=True, message="Contagem concluída!")
                QTimer.singleShot(600, lambda: show_toast(self.window(), "Concluído!", "success", 1600))
            else:
                QTimer.singleShot(1000, tick)

        QTimer.singleShot(1000, tick)

    def _go(self, path: str):
        win = self.window()
        r = getattr(win, "router", None)
        if r:
            try:
                r.go(path)
            except Exception as e:
                print("[WARN] navegação falhou:", e)

    @staticmethod
    def build(task_runner=None, theme_service=None):
        return HomePage(task_runner)


# Factory
def build(task_runner=None, theme_service=None):
    return HomePage.build(task_runner=task_runner, theme_service=theme_service)


# Runner de exemplo
class SleepRunner:
    def run_task(self, name: str, payload: dict) -> dict:
        import time
        time.sleep(5)
        return {"ok": True, "code": 1, "data": {"message": "ok"}}
