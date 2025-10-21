# ui/widgets/toast.py

from __future__ import annotations
from typing import Optional, List, Dict
from PySide6.QtCore import (
    Qt, QTimer, QEasingCurve, QPropertyAnimation, QPoint, Signal
)
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QVBoxLayout,
    QPushButton, QProgressBar
)

from ui.core.frameless_window import FramelessWindow


# ==================== Manager para empilhar/posicionar toasts ====================

class _ToastManager:
    """Gerencia pilha de toasts por tela, cuidando de posição e empilhamento (bottom-right)."""
    _instance: "_ToastManager" = None

    def __new__(cls):
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._per_screen: Dict[int, List[ToastShell]] = {}
            cls._instance._margin = 16
            cls._instance._spacing = 10
        return cls._instance

    def screen_id_for_widget(self, w: Optional[QWidget]) -> int:
        scr = None
        if w is not None:
            wh = w.windowHandle()
            if wh:
                scr = wh.screen()
        if scr is None:
            scr = QGuiApplication.primaryScreen()
        return id(scr) if scr else 0

    def _available_geom_for_screen_id(self, screen_id: int):
        for scr in QGuiApplication.screens():
            if id(scr) == screen_id:
                return scr.availableGeometry()
        # fallback
        return QGuiApplication.primaryScreen().availableGeometry()

    def register(self, toast_shell: "ToastShell", screen_id: int):
        stack = self._per_screen.setdefault(screen_id, [])
        stack.append(toast_shell)
        self._reflow(screen_id)

    def unregister(self, toast_shell: "ToastShell", screen_id: int):
        stack = self._per_screen.get(screen_id, [])
        if toast_shell in stack:
            stack.remove(toast_shell)
            self._reflow(screen_id)

    def reflow_for(self, screen_id: int):
        self._reflow(screen_id)

    def _reflow(self, screen_id: int):
        stack = self._per_screen.get(screen_id, [])
        if not stack:
            return
        area = self._available_geom_for_screen_id(screen_id)
        margin, spacing = self._margin, self._spacing

        next_bottom = area.bottom() - margin
        # Posiciona do bottom para cima (o mais novo é o último da lista)
        for shell in reversed(stack):
            shell.adjustSize()
            w, h = shell.width(), shell.height()
            x_end = area.right() - margin - w
            y_end = next_bottom - h
            if shell.isVisible():
                shell._animate_move_to(QPoint(x_end, y_end), duration=140)
            else:
                shell.move(x_end, y_end)
            next_bottom = y_end - spacing


# ==================== Shell reaproveitando o FramelessWindow ====================

class ToastShell(FramelessWindow):
    """
    Mini-janela de notificação flutuante (bottom-right), usando FramelessWindow.
    - Sem focar a aplicação
    - Sem resize por bordas
    - Título minimalista com apenas o botão fechar
    - Conteúdo centralizado, segue o base.qss
    """

    def __init__(self, parent_for_screen: QWidget | None, *, kind: str = "info"):
        super().__init__(None)
        self._parent_ref = parent_for_screen
        self._mgr = _ToastManager()
        self._screen_id: int | None = None

        # Flags para janela de notificação (não rouba foco; sempre no topo)
        self.setWindowFlags(
            Qt.FramelessWindowHint
            | Qt.Tool
            | Qt.WindowStaysOnTopHint
            | Qt.WindowDoesNotAcceptFocus
        )
        self.setAttribute(Qt.WA_TranslucentBackground, True)

        # Dimensões típicas de toast
        self.setMinimumSize(220, 90)
        self.setMaximumWidth(420)

        # Sem resize por bordas, e mínimos baixos (ajudam o layout)
        self.set_edges_enabled(False)
        self.set_min_resize_size(220, 90)

        # ===== Titlebar mínima (apenas fechar) =====
        topbar = QWidget(self)
        topbar.setObjectName("TopBar")
        th = QHBoxLayout(topbar)
        th.setContentsMargins(6, 6, 6, 6)
        th.setSpacing(6)
        th.addStretch(1)
        btn_close = QPushButton("✕", topbar)
        btn_close.setObjectName("TitleBarButton")
        btn_close.setFocusPolicy(Qt.NoFocus)
        btn_close.setCursor(Qt.PointingHandCursor)
        btn_close.clicked.connect(self.close_with_shrink_fade)
        th.addWidget(btn_close, 0)
        self.connect_titlebar(topbar)

        # ===== Conteúdo central =====
        content = QWidget(self)
        content.setObjectName("FramelessContent")
        cv = QVBoxLayout(content)
        cv.setContentsMargins(16, 12, 16, 14)
        cv.setSpacing(10)
        cv.setAlignment(Qt.AlignCenter)

        container = QWidget(self.content())
        lay = QVBoxLayout(container)
        lay.setContentsMargins(1, 1, 1, 1)
        lay.setSpacing(0)
        lay.addWidget(topbar)
        lay.addWidget(content)
        super().setCentralWidget(container)

        self._topbar = topbar
        self._content = content
        self._content_lay = cv

        # Animador de posição (slide-in). Fadear via windowOpacity do próprio FramelessWindow.
        self._anim_pos = QPropertyAnimation(self, b"pos", self)
        self._anim_pos.setEasingCurve(QEasingCurve.OutCubic)

        # Marca o tipo no frame para QSS condicional (opcional)
        frame = self._content.parentWidget().parentWidget()
        if frame:
            frame.setProperty("kind", kind)

    # ---------- integração com manager ----------
    def show_toast(self):
        self._screen_id = self._mgr.screen_id_for_widget(self._parent_ref)
        self._mgr.register(self, self._screen_id)
        self._enter_animation()

    def finish_and_close(self):
        self.close_with_shrink_fade()

    def closeEvent(self, e):
        try:
            if self._screen_id is not None:
                self._mgr.unregister(self, self._screen_id)
        finally:
            return super().closeEvent(e)

    # ---------- animações ----------
    def _enter_animation(self):
        # Evita o fade/bounce padrão do FramelessWindow neste caso específico
        self._first_show_done = True
        self.setWindowOpacity(0.0)

        self.adjustSize()
        self.show()   # necessário para obter geometria/posição finais
        end_pos = self.pos()
        start_pos = QPoint(end_pos.x() + 24, end_pos.y())

        # slide-in
        self._anim_pos.stop()
        self._anim_pos.setDuration(200)
        self._anim_pos.setStartValue(start_pos)
        self._anim_pos.setEndValue(end_pos)
        self._anim_pos.start()

        # fade-in usando windowOpacity (estável em top-level)
        self._animate_fade(0.0, 1.0, dur=180)

    def _animate_move_to(self, target: QPoint, duration: int = 140):
        self._anim_pos.stop()
        self._anim_pos.setDuration(duration)
        self._anim_pos.setStartValue(self.pos())
        self._anim_pos.setEndValue(target)
        self._anim_pos.start()

    # Reflow quando o conteúdo crescer/diminuir
    def resizeEvent(self, ev):
        super().resizeEvent(ev)
        if self._screen_id is not None:
            self._mgr.reflow_for(self._screen_id)


# ==================== Toast simples (auto-fecha) ====================

class Toast(QWidget):
    """API de alto nível para notificação curta que desaparece sozinha."""
    def __init__(self, parent: Optional[QWidget], text: str,
                 kind: str = "info", timeout_ms: int = 2400):
        super().__init__(parent)
        self._shell = ToastShell(parent, kind=kind)

        # Conteúdo
        lbl = QLabel(text, self._shell)
        f = lbl.font(); f.setPointSize(10); f.setBold(True)
        lbl.setFont(f)

        self._shell._content_lay.addWidget(lbl)

        # Timer de vida
        self._life = QTimer(self._shell)
        self._life.setSingleShot(True)
        self._life.timeout.connect(self._shell.finish_and_close)
        self._timeout = timeout_ms

    def show_toast(self):
        self._shell.show_toast()
        self._life.start(self._timeout)


def show_toast(parent: QWidget, text: str, kind: str = "info", timeout_ms: int = 2400) -> Toast:
    t = Toast(parent, text, kind, timeout_ms)
    t.show_toast()
    return t


# ==================== ProgressToast (andamento contínuo) ====================

class ProgressToast(QWidget):
    """
    Notificação flutuante com barra de progresso (determinada/indeterminada).
    Use:
        pt = ProgressToast.start(parent, "Processando…", kind="info", cancellable=True)
        pt.update(3, 10) / pt.set_progress(30) / pt.set_indeterminate(True)
        pt.finish(True, "Concluído!")  # auto fecha após um curto atraso
    """
    cancelled = Signal()

    def __init__(self, parent: Optional[QWidget], text: str,
                 kind: str = "info", cancellable: bool = False):
        super().__init__(parent)
        self._shell = ToastShell(parent, kind=kind)

        root = self._shell._content_lay  # centralizado
        # Linha de título + botão cancelar (opcional)
        line = QHBoxLayout()
        line.setContentsMargins(0, 0, 0, 0)
        line.setSpacing(8)

        self._label = QLabel(text, self._shell)
        f = self._label.font(); f.setPointSize(10); f.setBold(True)
        self._label.setFont(f)
        line.addWidget(self._label, 1)

        self._cancel_btn: Optional[QPushButton] = None
        if cancellable:
            btn = QPushButton("Cancelar", self._shell)
            btn.setCursor(Qt.PointingHandCursor)
            btn.setFocusPolicy(Qt.NoFocus)
            btn.clicked.connect(self._on_cancel_clicked)
            self._cancel_btn = btn
            line.addWidget(btn, 0)

        root.addLayout(line)

        # Barra de progresso (respeita QSS global)
        self._bar = QProgressBar(self._shell)
        self._bar.setRange(0, 100)
        self._bar.setValue(0)
        self._bar.setTextVisible(True)
        self._bar.setFormat("%p%")
        self._bar.setMinimumWidth(260)
        root.addWidget(self._bar)

        self._indeterminate = False
        self._finished = False

    # ----- API pública -----
    @staticmethod
    def start(parent: Optional[QWidget], text: str,
              kind: str = "info", cancellable: bool = False) -> "ProgressToast":
        pt = ProgressToast(parent, text, kind, cancellable)
        pt._shell.show_toast()
        return pt

    def set_text(self, text: str):
        self._label.setText(text)
        self._shell.adjustSize()

    def set_indeterminate(self, on: bool = True):
        """Barra indeterminada (pulsante)."""
        self._indeterminate = on
        if on:
            self._bar.setRange(0, 0)
            self._bar.setFormat("Aguarde…")
        else:
            self._bar.setRange(0, 100)
            self._bar.setFormat("%p%")
            if self._bar.value() < 0 or self._bar.value() > 100:
                self._bar.setValue(0)
        self._shell.adjustSize()

    def set_progress(self, percent: int):
        """Define progresso 0..100 (muda para modo determinado se necessário)."""
        if self._indeterminate:
            self.set_indeterminate(False)
        self._bar.setValue(max(0, min(100, int(percent))))

    def update(self, current: int, total: int):
        """Atalho conveniente para progresso determinado via fração."""
        if total <= 0:
            self.set_indeterminate(True)
            return
        pct = int(round((current / float(total)) * 100))
        self.set_progress(pct)

    def finish(self, success: bool = True, message: Optional[str] = None):
        """Conclui e fecha com feedback final curto."""
        if self._finished:
            return
        self._finished = True

        if message:
            self._label.setText(message)

        # feedback visual rápido
        if success:
            self._bar.setFormat("Concluído")
            self._bar.setValue(100)
        else:
            self._bar.setFormat("Falhou")

        # pequeno atraso para o usuário perceber o estado final
        QTimer.singleShot(500, self._shell.finish_and_close)

    # ----- internos -----
    def _on_cancel_clicked(self):
        self.cancelled.emit()
        self._label.setText("Cancelando…")
        self.set_indeterminate(True)
        # Quem ouvir o sinal decide encerrar o trabalho e depois chama finish()
