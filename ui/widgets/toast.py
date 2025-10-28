# ui/widgets/toast.py

from __future__ import annotations
from typing import Optional, List, Dict, Callable
import uuid

from PySide6.QtCore import (
    Qt, QTimer, QEasingCurve, QPropertyAnimation, QPoint, Signal, QObject
)
from PySide6.QtGui import QGuiApplication
from PySide6.QtWidgets import (
    QWidget, QLabel, QHBoxLayout, QVBoxLayout,
    QPushButton, QProgressBar, QSpacerItem, QSizePolicy, QFrame
)

from ui.core.frameless_window import FramelessToastDialog
from ui.widgets.titlebar import TitleBar


# ==================== NotificationBus (integração com Centro de Notificações) ====================

class _NotificationBus(QObject):
    """
    Barramento simplificado para integração com o Centro de Notificações.
    Outros módulos (TopBar, página notificações/caixa, ToastManager) podem conectar nestes sinais.

    addEntry(dict):     quando um toast é ocultado (dismiss) e deve aparecer no centro.
                        payload esperado (sugestão): {
                            "id": str, "type": str, "title": str, "text": str,
                            "actions": list[dict], "persist": bool, "expires_on_finish": bool
                        }

    updateEntry(dict):  se o produtor quiser atualizar título/texto/progresso etc. (opcional)
    finishEntry(id):    quando o toast conclui; a central decide remover se expires_on_finish=True.
    removeEntry(id):    remoção forçada (ex.: “limpar todas”).
    """
    addEntry = Signal(dict)
    updateEntry = Signal(dict)
    finishEntry = Signal(str)
    removeEntry = Signal(str)


_bus_singleton: Optional[_NotificationBus] = None


def notification_bus() -> _NotificationBus:
    global _bus_singleton
    if _bus_singleton is None:
        _bus_singleton = _NotificationBus()
    return _bus_singleton


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
                # Se não estiver visível, apenas posiciona silenciosamente
                shell.move(x_end, y_end)
            next_bottom = y_end - spacing


# ==================== Shell reaproveitando o FramelessWindow ====================

class ToastShell(FramelessToastDialog):
    """
    Mini-janela de notificação flutuante (bottom-right), usando FramelessWindow.
    - Sem focar a aplicação
    - Sem resize por bordas
    - Título minimalista com apenas o botão fechar
    - Conteúdo centralizado, segue o base.qss

    Integração com Centro de Notificações:
    - set_center_provider(callable) → callable retorna um dict com os campos para exibir no centro.
    - set_center_finish_id(id: str, persist: bool, expires_on_finish: bool)
      armazena o id e flags para a central poder remover/ficar após término.
    """

    def __init__(self, parent_for_screen: QWidget | None, *, kind: str = "info"):
        super().__init__(None)
        # Marca a janela como 'toast' para QSS com escopo
        try:
            self.setProperty("toast", True)
        except Exception:
            pass
        self._parent_ref = parent_for_screen
        self._mgr = _ToastManager()
        self._screen_id: int | None = None
        self._dismissing = False  # controla animação de ocultar

        # Centro de Notificações (dados fornecidos pelos wrappers Action/Progress)
        self._center_provider: Optional[Callable[[], Dict]] = None
        self._center_id: Optional[str] = None
        self._center_persist: bool = False
        self._center_expires_on_finish: bool = True

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

        # ===== Estrutura no padrão dos FramelessDialog (não modal) =====
        frame = QWidget(self)
        frame.setObjectName("ToastFrame")
        frame.setAttribute(Qt.WA_StyledBackground, True)
        frame.setProperty("toast", True)
        frame.setProperty("kind", kind)

        root = QWidget(frame)
        v = QVBoxLayout(root)
        v.setContentsMargins(12, 12, 12, 12)
        v.setSpacing(8)

        title = ""
        tb = TitleBar(title, parent=root)
        self.connect_titlebar(tb)
        # Fechar pela titlebar oculta o toast (sem destruir)
        try:
            if hasattr(tb, "btn_close"):
                tb.btn_close.clicked.connect(self.dismiss)  # type: ignore[attr-defined]
        except Exception:
            pass
        v.addWidget(tb)

        # Painel interno com borda
        panel = QFrame(root)
        panel.setObjectName("OuterPanel")
        pv = QVBoxLayout(panel)
        pv.setContentsMargins(10, 10, 10, 10)
        pv.setSpacing(8)
        v.addWidget(panel)

        # Conteúdo real do toast
        content = QWidget(panel)
        content.setObjectName("FramelessContent")
        cv = QVBoxLayout(content)
        cv.setContentsMargins(0, 0, 0, 0)
        cv.setSpacing(8)
        cv.setAlignment(Qt.AlignCenter)
        pv.addWidget(content)

        lay = QVBoxLayout(frame)
        lay.setContentsMargins(0, 0, 0, 0)
        lay.setSpacing(0)
        lay.addWidget(root)

        super().setCentralWidget(frame)

        self._topbar = tb
        self._content = content
        self._content_lay = cv

        # Animador de posição (slide-in). Fadear via windowOpacity.
        self._anim_pos = QPropertyAnimation(self, b"pos", self)
        self._anim_pos.setEasingCurve(QEasingCurve.OutCubic)

        # Marca o tipo no frame para QSS condicional (já feito acima)

    # ---------- integração com manager ----------   # (visual/empilhamento)
    def show_toast(self):
        self._screen_id = self._mgr.screen_id_for_widget(self._parent_ref)
        self._mgr.register(self, self._screen_id)
        self._enter_animation()

    # ---------- Integração com Centro de Notificações ----------
    def set_center_provider(self, provider: Callable[[], Dict]):
        self._center_provider = provider

    def set_center_finish_id(self, entry_id: str, *, persist: bool, expires_on_finish: bool = True):
        self._center_id = entry_id
        self._center_persist = bool(persist)
        self._center_expires_on_finish = bool(expires_on_finish)

    def _send_to_center_if_possible(self):
        """
        Envia/atualiza uma entrada na central quando o usuário oculta o toast.
        - Se não houver provider, não faz nada.
        - Define defaults úteis (id/persist/expires_on_finish) caso não tenham sido setados.
        """
        if not self._center_provider:
            return

        entry = dict(self._center_provider() or {})
        # Garante um ID
        if not self._center_id:
            self._center_id = entry.get("id") or uuid.uuid4().hex
        entry["id"] = self._center_id

        # Flags padrão
        entry.setdefault("persist", self._center_persist)
        entry.setdefault("expires_on_finish", self._center_expires_on_finish)

        notification_bus().addEntry.emit(entry)

    # ---------- ações de janela (dismiss/close) ----------
    def dismiss(self):
        """
        Oculta o toast com fade RÁPIDO e remove da pilha, sem destruir.
        Além disso, cria/atualiza uma entrada na Central de Notificações
        que permanece até o término (expires_on_finish=True) ou indefinidamente (persist=True).
        """
        if self._dismissing:
            return
        self._dismissing = True

        def _after():
            try:
                if self._screen_id is not None:
                    self._mgr.unregister(self, self._screen_id)
            finally:
                # Envia para a central
                try:
                    self._send_to_center_if_possible()
                except Exception:
                    pass
                # some apenas da tela; mantém objetos vivos
                self.hide()
                self.setWindowOpacity(1.0)
                self._dismissing = False

        # fade-out curto e discreto
        try:
            self._animate_fade(self.windowOpacity(), 0.0, after=_after, dur=140)
        except Exception:
            _after()

    def notify_finished_to_center(self):
        """Se o toast tiver sido ocultado para a central, avisa a conclusão."""
        if self._center_id:
            notification_bus().finishEntry.emit(self._center_id)

    def finish_and_close(self):
        """Fecha definitivamente com a animação padrão (libera memória)."""
        try:
            self.close_with_shrink_fade()
        except Exception:
            self.close()

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


# ==================== Conteúdo rico (título, texto, ações) ====================

class ToastContent(QWidget):
    """
    Widget para conteúdo do toast com título, texto e fast actions.
    Emite:
      - actionTriggered(dict) ao clicar em um botão de ação comum.
      - cancelRequested(str) se o botão tiver 'cancel_token'.
        ➜ Convenção: incluir na action { "label": "Cancelar", "cancel_token": "<token>" }
    """
    actionTriggered = Signal(dict)          # {label, route?, command?, payload?}
    cancelRequested = Signal(str)           # token de cancelamento

    def __init__(self, title: str, text: str, *, kind: str = "info",
                 actions: Optional[List[Dict]] = None, sticky: bool = False, parent=None):
        super().__init__(parent)
        self._kind = (kind or "info").lower().strip()
        self._actions = list(actions or [])
        self._sticky = bool(sticky)

        root = QVBoxLayout(self)
        root.setContentsMargins(0, 0, 0, 0)
        root.setSpacing(6)

        # Título
        ttl = QLabel(title or "", self)
        f = ttl.font()
        f.setPointSize(10)
        f.setBold(True)
        ttl.setFont(f)
        ttl.setWordWrap(True)
        root.addWidget(ttl)

        # Texto
        body = QLabel(text or "", self)
        body.setWordWrap(True)
        root.addWidget(body)

        # Ações (se houver)
        if self._actions:
            footer = QHBoxLayout()
            footer.setContentsMargins(0, 4, 0, 0)
            footer.setSpacing(6)
            footer.addItem(QSpacerItem(10, 10, QSizePolicy.Expanding, QSizePolicy.Minimum))
            for a in self._actions:
                label = str(a.get("label", "Abrir"))
                btn = QPushButton(label, self)
                # Botão de cancelar pré-programado:
                if "cancel_token" in a:
                    btn.setObjectName("ToastCancelButton")
                    tok = str(a["cancel_token"])
                    btn.clicked.connect(lambda _=False, t=tok: self.cancelRequested.emit(t))
                else:
                    btn.setObjectName("ToastActionButton")
                    btn.clicked.connect(lambda _=False, act=a: self.actionTriggered.emit(act))
                btn.setCursor(Qt.PointingHandCursor)
                btn.setFocusPolicy(Qt.NoFocus)
                footer.addWidget(btn)
            root.addLayout(footer)

    @property
    def sticky(self) -> bool:
        return self._sticky


# ==================== Toast simples (auto-fecha) ====================

class Toast(QWidget):
    """API de alto nível para notificação curta, somente texto, que desaparece sozinha."""
    def __init__(self, parent: Optional[QWidget], text: str,
                 kind: str = "info", timeout_ms: int = 2400, *, persist: bool = False):
        super().__init__(parent)
        self._shell = ToastShell(parent, kind=kind)

        # Conteúdo
        self._text = text
        lbl = QLabel(text, self._shell)
        f = lbl.font(); f.setPointSize(10); f.setBold(True)
        lbl.setFont(f)
        self._shell._content_lay.addWidget(lbl)

        # Centro: snapshot provider
        entry_id = uuid.uuid4().hex
        def _provider():
            return {
                "id": entry_id,
                "type": kind,
                "title": "",     # toast simples não tem título
                "text": self._text,
                "actions": [],
                "persist": persist,
                "expires_on_finish": True,
            }
        self._shell.set_center_provider(_provider)
        self._shell.set_center_finish_id(entry_id, persist=persist, expires_on_finish=True)

        # Timer de vida
        self._life = QTimer(self._shell)
        self._life.setSingleShot(True)
        self._life.timeout.connect(self._on_autoclose)
        self._timeout = timeout_ms

    def _on_autoclose(self):
        # avisa a central que terminou (se estava oculto/registrado)
        self._shell.notify_finished_to_center()
        self._shell.finish_and_close()

    def show_toast(self):
        self._shell.show_toast()
        self._life.start(self._timeout)


def show_toast(parent: QWidget, text: str, kind: str = "info", timeout_ms: int = 2400, *, persist: bool = False) -> Toast:
    t = Toast(parent, text, kind, timeout_ms, persist=persist)
    t.show_toast()
    return t


# ==================== Toast rico (título, texto, ações, sticky) ====================

class ActionToast(QWidget):
    """
    Notificação flutuante com título, texto e fast actions.
    - Se sticky=True, não se auto-fecha.
    - Emite actionTriggered(dict) ao clicar em um botão de ação.
    - Integra com Centro de Notificações quando ocultado (dismiss).
    """
    actionTriggered = Signal(dict)
    cancelRequested = Signal(str)   # repassa do conteúdo, se houver botão com cancel_token

    def __init__(self, parent: Optional[QWidget], title: str, text: str,
                 *, kind: str = "info", actions: Optional[List[Dict]] = None,
                 sticky: bool = False, timeout_ms: int = 3200, persist: bool = False):
        super().__init__(parent)
        self._title = title
        self._text = text
        self._persist = bool(persist)

        self._shell = ToastShell(parent, kind=kind)
        self._content = ToastContent(title, text, kind=kind, actions=actions, sticky=sticky, parent=self._shell)
        self._shell._content_lay.addWidget(self._content)
        self._content.actionTriggered.connect(self.actionTriggered.emit)
        self._content.cancelRequested.connect(self.cancelRequested.emit)

        # Centro: snapshot provider (para quando ocultar)
        entry_id = uuid.uuid4().hex
        def _provider():
            return {
                "id": entry_id,
                "type": kind,
                "title": self._title,
                "text": self._text,
                "actions": actions or [],
                "persist": self._persist or sticky,  # sticky normalmente deve permanecer
                "expires_on_finish": not (self._persist or sticky),
            }
        self._shell.set_center_provider(_provider)
        self._shell.set_center_finish_id(
            entry_id,
            persist=(self._persist or sticky),
            expires_on_finish=not (self._persist or sticky),
        )

        # Timer de vida (desativado se sticky)
        self._life = QTimer(self._shell)
        self._life.setSingleShot(True)
        self._life.timeout.connect(self._on_autoclose)
        self._timeout = 0 if sticky else int(timeout_ms)

    def _on_autoclose(self):
        # término “natural” do toast → avisa a central, ela remove se for expirar no fim
        self._shell.notify_finished_to_center()
        self._shell.finish_and_close()

    def show_toast(self):
        self._shell.show_toast()
        if self._timeout > 0:
            self._life.start(self._timeout)

    def close(self):
        # Fechamento programático
        self._on_autoclose()


def show_action_toast(parent: QWidget, title: str, text: str, *,
                      kind: str = "info", actions: Optional[List[Dict]] = None,
                      sticky: bool = False, timeout_ms: int = 3200, persist: bool = False) -> ActionToast:
    t = ActionToast(parent, title, text, kind=kind, actions=actions, sticky=sticky, timeout_ms=timeout_ms, persist=persist)
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

    Integração com a Central:
        - Ao ocultar (✕), cria entrada que expira quando finish() for chamado (a menos que persist=True).
        - Opcionalmente, exibe um botão "Cancelar" (interno) e também aceita fast action com cancel_token via ToastContent.
    """
    cancelled = Signal()

    def __init__(self, parent: Optional[QWidget], text: str,
                 kind: str = "info", cancellable: bool = False, *, persist: bool = False):
        super().__init__(parent)
        self._text = text
        self._persist = bool(persist)
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
            btn.setObjectName("ToastCancelButton")
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

        # Centro: snapshot provider (para quando ocultar)
        entry_id = uuid.uuid4().hex
        def _provider():
            return {
                "id": entry_id,
                "type": kind,
                "title": "Processando…",
                "text": self._label.text(),
                "actions": [],  # pode ser atualizado por quem integra
                "persist": self._persist,
                "expires_on_finish": not self._persist,
            }
        self._shell.set_center_provider(_provider)
        self._shell.set_center_finish_id(entry_id, persist=self._persist, expires_on_finish=not self._persist)

    # ----- API pública -----
    @staticmethod
    def start(parent: Optional[QWidget], text: str,
              kind: str = "info", cancellable: bool = False, *, persist: bool = False) -> "ProgressToast":
        pt = ProgressToast(parent, text, kind, cancellable, persist=persist)
        pt._shell.show_toast()
        return pt

    def set_text(self, text: str):
        self._label.setText(text)
        # Atualiza central (se alguém quiser refletir mudanças de texto)
        try:
            entry = {"id": getattr(self._shell, "_center_id", None), "text": text}
            if entry["id"]:
                notification_bus().updateEntry.emit(entry)
        except Exception:
            pass
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
        v = max(0, min(100, int(percent)))
        self._bar.setValue(v)
        # Opcional: refletir na central
        try:
            entry_id = getattr(self._shell, "_center_id", None)
            if entry_id is not None:
                notification_bus().updateEntry.emit({"id": entry_id, "progress": v})
        except Exception:
            pass

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
            try:
                entry_id = getattr(self._shell, "_center_id", None)
                if entry_id:
                    notification_bus().updateEntry.emit({"id": entry_id, "text": message})
            except Exception:
                pass

        # feedback visual rápido
        if success:
            self._bar.setFormat("Concluído")
            self._bar.setValue(100)
        else:
            self._bar.setFormat("Falhou")

        # avisa a central que terminou (remove se expires_on_finish=True)
        self._shell.notify_finished_to_center()

        # pequeno atraso para o usuário perceber o estado final
        QTimer.singleShot(500, self._shell.finish_and_close)

    # ----- internos -----
    def _on_cancel_clicked(self):
        self.cancelled.emit()
        self._label.setText("Cancelando…")
        try:
            entry_id = getattr(self._shell, "_center_id", None)
            if entry_id:
                notification_bus().updateEntry.emit({"id": entry_id, "text": "Cancelando…"})
        except Exception:
            pass
        self.set_indeterminate(True)
        # Quem ouvir o sinal decide encerrar o trabalho e depois chama finish()
