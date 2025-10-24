# ui/pages/home_page.py

from __future__ import annotations

from PySide6.QtWidgets import (
    QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout, QGridLayout, QSizePolicy
)
from PySide6.QtCore import QTimer, Qt, QDateTime
from PySide6.QtGui import QFontMetrics

from ui.widgets.buttons import Controls, command_button, attach_popover
from ui.widgets.async_button import AsyncTaskButton
from ui.widgets.toast import show_toast, ProgressToast

# <<< NOVO: tentar usar o barramento do centro de notificações (failsafe) >>>
try:
    from ui.widgets.toast import notification_bus  # pode não existir em versões antigas
except Exception:
    notification_bus = None


PAGE = {
    "route": "home",
    "label": "Início",
    "sidebar": True,
    "order": 0,
}


# ------------------------------------------------------------
# Helpers de integração com a caixa de notificações
# ------------------------------------------------------------
def _new_id(prefix: str = "home") -> str:
    return f"{prefix}-{QDateTime.currentMSecsSinceEpoch()}"


def _notify_center_create(kind: str, title: str, text: str, *, sticky: bool, ttl_ms: int | None, ref_id: str) -> None:
    """Cria uma entrada no Centro de Notificações (se disponível)."""
    try:
        bus = notification_bus() if callable(notification_bus) else None
        if bus and hasattr(bus, "addEntry"):
            payload = {
                "id": ref_id,
                "kind": kind,
                "title": title,
                "text": text,
                "sticky": bool(sticky),
            }
            if ttl_ms is not None:
                payload["ttl_ms"] = int(ttl_ms)
            bus.addEntry.emit(payload)
    except Exception:
        pass


def _notify_center_update(ref_id: str, **fields) -> None:
    """Atualiza uma entrada existente (se API estiver disponível)."""
    try:
        bus = notification_bus() if callable(notification_bus) else None
        if bus and hasattr(bus, "updateEntry"):
            data = {"id": ref_id}
            data.update(fields)
            bus.updateEntry.emit(data)
    except Exception:
        pass


def _notify_center_remove(ref_id: str) -> None:
    """Remove uma entrada (se disponível)."""
    try:
        bus = notification_bus() if callable(notification_bus) else None
        if bus and hasattr(bus, "removeEntry"):
            bus.removeEntry.emit(ref_id)
    except Exception:
        pass


# ------------------------------------------------------------
# Helpers visuais
# ------------------------------------------------------------
def _section(parent: QWidget, title: str, subtitle: str | None = None) -> QFrame:
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

    # Subtítulo (opcional)
    if subtitle:
        sub = QLabel(subtitle, frame)
        sub.setWordWrap(True)
        sub.setStyleSheet("opacity: 0.85;")
        outer.addWidget(sub)

    # Conteúdo do card
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
    btn = Controls.Button(text, size_preset="sm")
    btn.setProperty("variant", "chip")
    btn.setProperty("size", "sm")
    btn.setSizePolicy(QSizePolicy.Maximum, QSizePolicy.Fixed)
    _repolish(btn)
    return btn


def _btn(text: str, preset: str = "md", *, variant: str | None = None) -> Controls.Button:
    b = Controls.Button(text, size_preset=preset)
    b.setProperty("size", preset)
    if variant:
        b.setProperty("variant", variant)
    _repolish(b)
    return b


def _repolish(w: QWidget) -> None:
    s = w.style()
    s.unpolish(w)
    s.polish(w)


# ============================================================
# Subpáginas embutidas
# ============================================================
class HomeToolsPage(QWidget):
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

        bt1 = _btn("Abrir Detalhes", "md", variant="primary")
        bt1.clicked.connect(lambda: self._go("home/ferramentas/detalhes"))
        row.addWidget(bt1)

        bt2 = _btn("Voltar à Home", "sm")
        row.addWidget(bt2)
        bt2.clicked.connect(lambda: self._go("home"))

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


class HomeToolsDetailsPage(QWidget):
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
        back = _btn("↩ Voltar", "sm")
        back.clicked.connect(lambda: self._go("home/ferramentas"))
        row.addWidget(back)

        home = _btn("Início", "sm")
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
# Página Home (raiz)
# ============================================================
class HomePage(QWidget):
    def __init__(self, task_runner):
        super().__init__()

        # ===== Scroll global =====
        outer = QVBoxLayout(self)
        outer.setContentsMargins(0, 0, 0, 0)
        outer.setSpacing(0)

        scroller = Controls.ScrollArea(self)
        scroller.setObjectName("HomeScrollArea")
        scroller.setFrameShape(QFrame.NoFrame)
        outer.addWidget(scroller)

        self.setMinimumSize(900, 640)

        # Conteúdo (transparente para herdar gradiente do #FramelessFrame)
        content = QWidget()
        content.setObjectName("FramelessContent")
        content.setAttribute(Qt.WA_StyledBackground, False)
        scroller.setWidget(content)

        root = QVBoxLayout(content)
        root.setContentsMargins(16, 16, 16, 16)
        root.setSpacing(14)

        # -----------------------------------------------------
        # HERO
        # -----------------------------------------------------
        hero = _section(
            content,
            "Bem-vindo 👋",
            "Este projeto traz um shell com Router, TopBar (breadcrumb), histórico, Quick Open (Ctrl+K), "
            "ThemeService, Settings, toasts e comandos. Esta Home é um guia interativo."
        )
        hero_lay = hero._content.layout()  # type: ignore[attr-defined]

        chips = QHBoxLayout()
        chips.setSpacing(6)
        for t in ("Router", "Breadcrumb", "Histórico", "Quick Open", "Toasts", "Async"):
            btn = Controls.Button(t); btn.setProperty("variant", "chip"); chips.addWidget(btn)
        chips.addStretch(1)
        hero_lay.addLayout(chips)

        cta_row = QHBoxLayout()
        cta_row.setSpacing(8)

        goto_tools = _btn("Abrir Ferramentas", "md", variant="primary")
        goto_tools.clicked.connect(lambda: self._go("home/ferramentas"))
        cta_row.addWidget(goto_tools)

        goto_guide = _btn("Guia Rápido (Subpágina externa)", "sm")
        goto_guide.clicked.connect(lambda: self._go("home/guia"))
        cta_row.addWidget(goto_guide)

        cta_row.addStretch(1)
        hero_lay.addLayout(cta_row)

        root.addWidget(hero)

        # -----------------------------------------------------
        # Navegação (conceitos)
        # -----------------------------------------------------
        nav = _section(
            content,
            "Navegação & Rotas",
            "Rotas são hierárquicas (ex.: home/ferramentas/detalhes), o breadcrumb mostra o caminho "
            "e é clicável. Use Alt+←/Alt+→ para voltar/avançar. A última rota é restaurada ao abrir o app."
        )
        nav_lay = nav._content.layout()  # type: ignore[attr-defined]

        nav_buttons = QHBoxLayout()
        b1 = _btn("Ir para Ferramentas (home/ferramentas)", "sm", variant="primary")
        b1.clicked.connect(lambda: self._go("home/ferramentas"))
        nav_buttons.addWidget(b1)

        b2 = _btn("Ir para Detalhes (home/ferramentas/detalhes)", "sm")
        b2.clicked.connect(lambda: self._go("home/ferramentas/detalhes"))
        nav_buttons.addWidget(b2)

        nav_buttons.addStretch(1)
        nav_lay.addLayout(nav_buttons)

        tip_nav = QLabel("Dica: clique nos itens do breadcrumb para saltar direto para um nível específico.")
        tip_nav.setWordWrap(True)
        nav_lay.addWidget(tip_nav)
        root.addWidget(nav)

        # -----------------------------------------------------
        # Quick Open + Popover
        # -----------------------------------------------------
        qopen = _section(
            content,
            "Quick Open (Ctrl+K) — estilizado",
            "Pressione Ctrl+K para abrir o Quick Open frameless (mesmo tema), filtrando por nome/rota. "
            "Somente páginas com 'sidebar=True' aparecem."
        )
        qopen_lay = qopen._content.layout()  # type: ignore[attr-defined]
        qopen_lay.addWidget(QLabel("Experimente: digite “Ferramentas” ou “home/…”."))

        lbl_hint = QLabel("Mantenha o mouse sobre este texto para saber mais.")
        lbl_hint.setAttribute(Qt.WA_Hover, True)
        qopen_lay.addWidget(lbl_hint)

        attach_popover(
            lbl_hint,
            "Dica (Popover)",
            "Popovers servem para dicas curtas e contextuais sem mudar de tela.",
            "Ctrl+K"
        )

        lbl_hint.setProperty("hasPopover", True)
        _repolish(lbl_hint)
        root.addWidget(qopen)

        # -----------------------------------------------------
        # Ações / Async / Toasts
        # -----------------------------------------------------
        actions = _section(
            content,
            "Ações e Execução",
            "Exemplos de execução síncrona/assíncrona, com feedback visual e bloqueios opcionais."
        )
        a_lay = actions._content.layout()  # type: ignore[attr-defined]

        row_cmds = QHBoxLayout()
        row_cmds.setSpacing(8)

        btn_proc = command_button(
            "Rodar processo (Vazio)",
            "proc_A",
            task_runner,
            {"fast": True},
            disable_while_running=True,
            lock_after_click=False,
            size_preset="sm",
        )
        btn_proc.setProperty("size", "sm")
        btn_proc.setProperty("variant", "primary")
        _repolish(btn_proc)
        row_cmds.addWidget(btn_proc)

        btn_once = command_button(
            "Enviar única vez (trava após)",
            "send_once",
            task_runner,
            {"payload": 1},
            disable_while_running=True,
            lock_after_click=True,
            size_preset="sm",
        )
        btn_once.setProperty("size", "sm")
        btn_once.setProperty("variant", "primary")
        _repolish(btn_once)
        row_cmds.addWidget(btn_once)

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
        btn_async.setProperty("size", "md")
        _repolish(btn_async)
        row_cmds.addWidget(btn_async)

        row_cmds.addStretch(1)
        a_lay.addLayout(row_cmds)

        toast_row = QHBoxLayout()
        toast_row.setSpacing(8)
        btn_toast_curto = _btn("Toast Curto (5s)", "sm", variant="primary")
        btn_toast_curto.clicked.connect(self._demo_toast_curto)
        toast_row.addWidget(btn_toast_curto)

        btn_toast_andamento = _btn("Toast com Progresso (1→5)", "sm", variant="primary")
        btn_toast_andamento.clicked.connect(self._demo_toast_contagem)
        toast_row.addWidget(btn_toast_andamento)

        toast_row.addStretch(1)
        a_lay.addLayout(toast_row)

        tip_actions = QLabel("Dica: ProgressToast aceita .set_progress(), .update(curr,total) e .finish().")
        tip_actions.setWordWrap(True)
        a_lay.addWidget(tip_actions)

        root.addWidget(actions)

        # -----------------------------------------------------
        # Controles rápidos
        # -----------------------------------------------------
        ctrls = _section(
            content,
            "Controles rápidos",
            "Demonstração de presets de tamanho, Expand/Ver mais, Popovers e Slider como progresso."
        )
        c_lay = ctrls._content.layout()  # type: ignore[attr-defined]

        presets_row = QHBoxLayout()
        presets_row.setSpacing(6)
        presets_row.addWidget(_btn("A", "char", variant="primary"))
        for p in ("sm", "md", "lg", "xl"):
            presets_row.addWidget(_btn(f"Preset {p}", p, variant="primary"))
        presets_row.addStretch(1)
        c_lay.addLayout(presets_row)

        details = QFrame()
        dlay = QVBoxLayout(details)
        dlay.setContentsMargins(0, 0, 0, 0)
        dlay.setSpacing(4)
        dlay.addWidget(QLabel("• Linha 1 de detalhes"))
        dlay.addWidget(QLabel("• Linha 2 de detalhes"))
        dlay.addWidget(QLabel("• Linha 3 de detalhes"))

        expand = Controls.ExpandMore(
            details,
            text_collapsed="Ver mais detalhes",
            text_expanded="Ver menos detalhes"
        )
        c_lay.addWidget(expand)

        _fix_expand_width(expand)

        slider_row = QHBoxLayout()
        slider_row.setSpacing(8)

        s_interactive = Controls.Slider()
        s_interactive.setRange(0, 100)
        s_interactive.setValue(30)
        slider_row.addWidget(QLabel("Slider interativo:"))
        slider_row.addWidget(s_interactive)

        self.s_progress = Controls.Slider()
        self.s_progress.setRange(0, 100)
        self.s_progress.setMode("progress")
        self.s_progress.setValue(0)
        self.s_progress.setAttribute(Qt.WA_TransparentForMouseEvents, True)
        slider_row.addWidget(QLabel("Progresso:"))
        slider_row.addWidget(self.s_progress)

        slider_row.addStretch(1)
        c_lay.addLayout(slider_row)

        self._progress_tick = 0
        self._progress_timer = QTimer(self)
        self._progress_timer.timeout.connect(self._tick_progress)
        self._progress_timer.start(80)

        root.addWidget(ctrls)

        # -----------------------------------------------------
        # Lista longa
        # -----------------------------------------------------
        scroll_sec = _section(
            content,
            "Scroll / Lista longa",
            "Abaixo um conteúdo grande — use a rolagem global para navegar."
        )
        s_lay = scroll_sec._content.layout()  # type: ignore[attr-defined]
        for i in range(1, 41):
            s_lay.addWidget(QLabel(f"Item longo #{i} — texto de exemplo para rolagem."))
        root.addWidget(scroll_sec)

        self._toast_scheduled = False

    # --------- helpers de UI ----------
    def _tick_progress(self):
        self._progress_tick = (self._progress_tick + 2) % 101
        self.s_progress.setValue(self._progress_tick)

    def showEvent(self, e):
        super().showEvent(e)
        if not self._toast_scheduled:
            self._toast_scheduled = True
            QTimer.singleShot(
                0,
                lambda: show_toast(
                    self.window(),
                    "Dica: experimente o Quick Open (Ctrl+K).",
                    "info",
                    2600,
                ),
            )

    # ------------------ DEMOS COM “PERMANÊNCIA” ------------------

    def _demo_toast_curto(self):
        """
        Exemplo: tarefa curta.
        - Toast visual rápido + entrada no Centro (TTL curto).
        - Ao concluir, atualiza para 'success' e deixa expirar.
        """
        # Toast visual imediato
        show_toast(self.window(), "Iniciando tarefa curta…", "info", 1600)

        # Entrada temporária no Centro
        ref_id = _new_id("short")
        _notify_center_create(
            kind="info",
            title="Tarefa curta",
            text="Iniciando…",
            sticky=False,
            ttl_ms=6000,   # fica lá por 6s mesmo que o toast feche
            ref_id=ref_id,
        )

        def _done():
            show_toast(self.window(), "Tarefa curta concluída!", "success", 2000)
            # Atualiza a entrada (deixa o mesmo TTL correr)
            _notify_center_update(ref_id, kind="success", title="Tarefa curta", text="Concluída!")

        QTimer.singleShot(5000, _done)

    def _demo_toast_contagem(self):
        """
        Exemplo: progresso 1→5.
        - Entrada no Centro é criada e atualizada a cada tick.
        - Ao finalizar, vira 'success' e pode permanecer (sticky=True) ou expirar.
        """
        total = 5
        pt = ProgressToast.start(self.window(), "Contagem: 0/5…", kind="info", cancellable=False)
        pt.set_progress(0)

        # Entrada no Centro com “permanência” durante o progresso
        ref_id = _new_id("count")
        _notify_center_create(
            kind="info",
            title="Contagem",
            text="0/5…",
            sticky=True,   # permanece visível até terminar
            ttl_ms=None,   # sem TTL enquanto em andamento
            ref_id=ref_id,
        )

        state = {"i": 0}

        def tick():
            state["i"] += 1
            i = state["i"]
            pt.update(i, total)
            msg = f"Contagem: {i}/{total}…"
            pt.set_text(msg)
            # Atualiza entrada no Centro
            _notify_center_update(ref_id, text=f"{i}/{total}…")

            if i >= total:
                pt.finish(success=True, message="Contagem concluída!")
                # Marca como concluído e agora deixa com TTL curto (ex.: 6s)
                _notify_center_update(ref_id, kind="success", text="Concluída!")
                # se quiser que permaneça indefinidamente, comente a linha abaixo
                _notify_center_update(ref_id, ttl_ms=6000, sticky=False)
            else:
                QTimer.singleShot(1000, tick)

        QTimer.singleShot(1000, tick)

    # ------------------------------------------------------------

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


def build(task_runner=None, theme_service=None):
    return HomePage.build(task_runner=task_runner, theme_service=theme_service)


class SleepRunner:
    def run_task(self, name: str, payload: dict) -> dict:
        import time
        time.sleep(5)
        return {"ok": True, "code": 1, "data": {"message": "ok"}}


# ---------------- internal util ----------------
def _fix_expand_width(expand_widget: Controls.ExpandMore):
    btn = expand_widget.btn
    fm = QFontMetrics(btn.font())
    w = max(
        fm.horizontalAdvance("Ver mais detalhes"),
        fm.horizontalAdvance("Ver menos detalhes")
    )
    w += 28
    btn.setMinimumWidth(w)
    btn.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Fixed)
