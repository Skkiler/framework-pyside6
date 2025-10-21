# ui/pages/home_page.py

from __future__ import annotations
from PySide6.QtWidgets import QWidget, QVBoxLayout, QLabel, QFrame, QHBoxLayout
from PySide6.QtCore import QTimer, Qt

from ui.widgets.buttons import Controls, command_button
from ui.widgets.async_button import AsyncTaskButton
from ui.widgets.toast import show_toast, ProgressToast   # novos toasts

PAGE = {
    "route": "home",
    "label": "Início",
    "sidebar": True,
    "order": 0,
}

# ------------------------------------------------------------
# Helpers visuais simples para seções
# ------------------------------------------------------------
def _section(parent: QWidget, title: str) -> QFrame:
    """
    Cria um 'card' (QFrame) com título, usando o QSS:
      QWidget[elevation="panel"] { ... }
    """
    frame = QFrame(parent)
    frame.setProperty("elevation", "panel")
    outer = QVBoxLayout(frame)
    outer.setContentsMargins(12, 10, 12, 12)
    outer.setSpacing(10)

    lbl = QLabel(title, frame)
    f = lbl.font()
    f.setPointSize(max(12, f.pointSize()))
    f.setBold(True)
    lbl.setFont(f)
    outer.addWidget(lbl)

    # container interno para conteúdo da seção
    content = QFrame(frame)
    content.setFrameShape(QFrame.NoFrame)
    inner = QVBoxLayout(content)
    inner.setContentsMargins(0, 0, 0, 0)
    inner.setSpacing(8)
    outer.addWidget(content)

    # devolve o frame, e o chamador pode acessar .layout() do content
    # usando um atributo para facilitar:
    content.setObjectName("_section_content")
    frame._content = content  # type: ignore[attr-defined]
    return frame


class HomePage(QWidget):
    def __init__(self, task_runner):
        super().__init__()
        root = QVBoxLayout(self)
        root.setContentsMargins(14, 14, 14, 14)
        root.setSpacing(12)

        # Cabeçalho amigável
        hero = _section(self, "Bem-vindo 👋")
        hero_lay = hero._content.layout()  # type: ignore[attr-defined]
        hero_lay.addWidget(QLabel("Esta é a Home. Abaixo você encontra exemplos prontos de botões e toasts."))
        root.addWidget(hero)

        # =====================================================
        # Seção: Ações principais (mantendo seus botões)
        # =====================================================
        actions = _section(self, "Ações")
        a_lay = actions._content.layout()  # type: ignore[attr-defined]

        # Botão síncrono padrão (já usa Hover “glow”)
        a_lay.addWidget(
            command_button(
                "Rodar processo A (rápido)",
                "proc_A",
                task_runner,
                {"fast": True},
            )
        )

        # Botão assíncrono – BLOQUEIA a tela com overlay
        btn_async = AsyncTaskButton(
            "Dormir 5s (assíncrono)",
            SleepRunner(),
            "ignored",
            {},
            parent=self,
            toast_success="Concluído!",
            toast_error="Falhou",
            # overlay somente quando bloquear — aqui queremos bloquear:
            use_overlay=True,
            block_input=True,
            overlay_parent=self,
            overlay_message="Processando dados…"
        )
        # Visual: podemos marcar como 'primary' se quiser destacar
        btn_async.setProperty("variant", "primary")
        a_lay.addWidget(btn_async)

        root.addWidget(actions)

        # =====================================================
        # Seção: Demos de Toasts (notificação & progresso)
        # =====================================================
        toasts = _section(self, "Demos de Toasts")
        t_lay = toasts._content.layout()  # type: ignore[attr-defined]

        # Linha de botões
        row = QHBoxLayout()
        row.setSpacing(8)

        # 1) Toast curto -> aguarda 5s -> toast de concluído
        btn_toast_curto = Controls.Button("Toast Curto (5s)", self)
        btn_toast_curto.clicked.connect(self._demo_toast_curto)
        row.addWidget(btn_toast_curto)

        # 2) ProgressToast: contagem 1→5 (1s por passo)
        btn_toast_andamento = Controls.Button("Toast de Andamento (1→5)", self)
        btn_toast_andamento.clicked.connect(self._demo_toast_contagem)
        row.addWidget(btn_toast_andamento)

        # estica para alinhar bonito, caso sobre espaço
        row.addStretch(1)
        t_lay.addLayout(row)

        # Dica textual breve
        tip = QLabel("• As notificações aparecem como janelas flutuantes (frameless) no canto inferior direito.\n"
                     "• O ProgressToast aceita .set_progress(), .update(curr,total) e .finish().")
        tip.setWordWrap(True)
        t_lay.addWidget(tip)

        root.addWidget(toasts)

        # =====================================================
        # Seção: Controles (exemplos rápidos)
        # =====================================================
        ctrls = _section(self, "Controles")
        c_lay = ctrls._content.layout()  # type: ignore[attr-defined]
        c_lay.addWidget(Controls.Toggle(self))
        c_lay.addWidget(Controls.TextInput("Digite algo…", self))
        root.addWidget(ctrls)

        self._toast_scheduled = False

    # ------------------------------------------------------------------
    # Toast de onboarding na primeira abertura da página
    # ------------------------------------------------------------------
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

    # ------------------------------------------------------------------
    # DEMOS
    # ------------------------------------------------------------------
    def _demo_toast_curto(self):
        """Mostra um toast curto de início; após 5s, mostra 'concluído'."""
        show_toast(self.window(), "Iniciando tarefa curta…", "info", 1600)

        # Sem bloquear a UI: agenda o toast final em 5s
        QTimer.singleShot(
            5000,
            lambda: show_toast(self.window(), "Tarefa curta concluída!", "success", 2000)
        )

    def _demo_toast_contagem(self):
        """
        Abre um ProgressToast e atualiza de 1 a 5 a cada 1s.
        Ao fim, fecha com sucesso e opcionalmente mostra um toast curto.
        """
        total = 5
        pt = ProgressToast.start(self.window(), "Contagem: 0/5…", kind="info", cancellable=False)
        pt.set_progress(0)  # modo determinado

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

    # ------------------------------------------------------------------
    @staticmethod
    def build(task_runner=None, theme_service=None):
        return HomePage(task_runner)

# ====== FACTORY para o registry ======
def build(task_runner=None, theme_service=None):
    return HomePage.build(task_runner=task_runner, theme_service=theme_service)

# Runner usado pelo botão assíncrono
class SleepRunner:
    def run_task(self, name: str, payload: dict) -> dict:
        import time
        time.sleep(5)                 # “trabalho”
        return {"ok": True, "code": 1, "data": {"message": "ok"}}
