# ui/widgets/async_button.py

from __future__ import annotations
from typing import Dict, Any, Optional, Callable

from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool
from PySide6.QtWidgets import QMessageBox, QWidget, QStackedWidget

from .buttons import HoverButton
from .toast import show_toast

try:
    from .loading_overlay import LoadingOverlay
except Exception:  # pragma: no cover
    LoadingOverlay = None  # type: ignore


# --- Worker infra ---
class _TaskSignals(QObject):
    finished = Signal(dict)   # {ok, data?, error?, code?}


class _TaskRunnable(QRunnable):
    def __init__(self, fn, *args, **kwargs):
        super().__init__()
        self.fn = fn
        self.args = args
        self.kwargs = kwargs
        self.signals = _TaskSignals()

    def run(self):
        try:
            res = self.fn(*self.args, **self.kwargs)
        except Exception as e:
            res = {"ok": False, "error": str(e), "code": 0}
        self.signals.finished.emit(res)


def _extract_code(result: dict) -> int:
    if "code" in result and isinstance(result["code"], int):
        return int(result["code"])
    data = result.get("data")
    if isinstance(data, dict) and "code" in data and isinstance(data["code"], int):
        return int(data["code"])
    return 1 if bool(result.get("ok")) else 0


class AsyncTaskButton(HoverButton):
    def __init__(
        self,
        text: str,
        task_runner,
        command_name: str,
        payload: Optional[Dict[str, Any]] = None,
        parent: Optional[QWidget] = None,
        *,
        on_done: Optional[Callable[[dict], None]] = None,
        toast_success: Optional[str] = "Concluído",
        toast_fail: Optional[str]    = "Falha no processo",
        toast_error: Optional[str]   = "Erro na execução",
        use_overlay: bool = True,
        overlay_parent: Optional[QWidget] = None,   # None => resolve automaticamente (PÁGINA atual)
        overlay_message: str = "Processando...",
        block_input: bool = True,                   # bloqueia apenas o conteúdo (não TopBar/Sidebar)
    ):
        super().__init__(text, parent)
        self._runner = task_runner
        self._cmd = command_name
        self._payload = payload or {}
        self._on_done = on_done
        self._t_succ = toast_success
        self._t_fail = toast_fail
        self._t_err  = toast_error
        self._orig_text = text

        self._pool = QThreadPool.globalInstance()

        self._use_overlay = bool(use_overlay and LoadingOverlay is not None)
        self._overlay_parent = overlay_parent
        self._overlay_message = overlay_message
        self._overlay_block_input = bool(block_input)
        self._overlay: Optional[LoadingOverlay] = None

        self.clicked.connect(self._kickoff)

    # ---------- onde ancorar ----------
    def _resolve_overlay_parent(self) -> QWidget:
        """
        Sobe a hierarquia até encontrar um QStackedWidget (a área de conteúdo).
        Retorna o currentWidget() (a PÁGINA), garantindo que o overlay
        seja filho direto da página — assim topbar/sidebar ficam fora.
        """
        if self._overlay_parent:
            return self._overlay_parent

        w: Optional[QWidget] = self
        stack: Optional[QStackedWidget] = None
        while w is not None:
            if isinstance(w, QStackedWidget):
                stack = w
                break
            w = w.parentWidget()

        if stack:
            page = stack.currentWidget()
            if page:
                return page
            return stack  # fallback (raro)

        # fallback seguro: parent imediato (geralmente já é a page)
        return self.parentWidget() or self.window()

    def _ensure_overlay(self) -> Optional[LoadingOverlay]:
        if not self._use_overlay:
            return None
        parent = self._resolve_overlay_parent()
        # se já existe mas o parent mudou, recria
        if self._overlay is None or self._overlay.parent() is not parent:
            if LoadingOverlay is not None:
                self._overlay = LoadingOverlay(
                    parent=parent,
                    message=self._overlay_message,
                    block_input=self._overlay_block_input,
                    background_mode="theme",
                )
        return self._overlay

    # ---------- execução ----------
    def _kickoff(self):
        if not hasattr(self._runner, "run_task"):
            QMessageBox.warning(self, "Erro", "Runner inválido.")
            return

        self.setEnabled(False)

        ov = self._ensure_overlay()
        if ov:
            ov.show(self._overlay_message)
        else:
            self.setText("Executando…")

        job = _TaskRunnable(self._runner.run_task, self._cmd, self._payload)
        job.signals.finished.connect(self._finish)
        self._pool.start(job)

    def _finish(self, result: dict):
        if self._overlay:
            self._overlay.hide()
        self.setEnabled(True)
        self.setText(self._orig_text)

        code = _extract_code(result)
        if code == 1:
            if self._t_succ:
                show_toast(self.window(), self._t_succ, "success", 2000)
        elif code == 2:
            if self._t_fail:
                show_toast(self.window(), f"{self._t_fail}", "warn", 2400)
        else:
            msg = result.get("error", "") or "Erro desconhecido"
            if self._t_err:
                show_toast(self.window(), f"{self._t_err}: {msg}", "error", 2600)

        if callable(self._on_done):
            try:
                self._on_done(result)
            except Exception:
                pass
