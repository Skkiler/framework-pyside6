# ui/widgets/async_button.py

from __future__ import annotations
from typing import Dict, Any, Optional, Callable

from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool
from PySide6.QtWidgets import QMessageBox, QWidget, QStackedWidget

from .buttons import HoverButton
from .toast import show_toast, ProgressToast   # usamos ProgressToast para loading

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

        # Política de bloqueio/overlay
        block_input: bool = False,                 # padrão: não trava a tela
        use_overlay: bool = True,                  # só tem efeito se block_input=True
        overlay_parent: Optional[QWidget] = None,  # None => resolve automaticamente (PÁGINA atual)
        overlay_message: str = "Processando...",

        # Progress toast
        progress_text: Optional[str] = "Processando…",
        progress_kind: str = "info",
        progress_cancellable: bool = False,        # pode ligar e conectar pt.cancelled
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

        # overlay e bloqueio
        self._block_input = bool(block_input)
        self._use_overlay = bool(self._block_input and use_overlay and LoadingOverlay is not None)
        self._overlay_parent = overlay_parent
        self._overlay_message = overlay_message
        self._overlay: Optional[LoadingOverlay] = None

        # progress toast – agora SEMPRE permitido (mesmo com overlay)
        self._progress_text = progress_text
        self._progress_kind = progress_kind
        self._progress_cancellable = bool(progress_cancellable)
        self._pt: Optional[ProgressToast] = None

        self.clicked.connect(self._kickoff)

    # ---------- onde ancorar ----------
    def _resolve_overlay_parent(self) -> QWidget:
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

        return self.parentWidget() or self.window()

    def _ensure_overlay(self) -> Optional[LoadingOverlay]:
        if not self._use_overlay:
            return None
        parent = self._resolve_overlay_parent()
        if self._overlay is None or self._overlay.parent() is not parent:
            if LoadingOverlay is not None:
                self._overlay = LoadingOverlay(
                    parent=parent,
                    message=self._overlay_message,
                    block_input=True,
                    background_mode="theme",
                )
        return self._overlay

    # ---------- execução ----------
    def _kickoff(self):
        if not hasattr(self._runner, "run_task"):
            QMessageBox.warning(self, "Erro", "Runner inválido.")
            return

        self.setEnabled(False)

        # 1) Overlay (se aplicável)
        if self._use_overlay:
            ov = self._ensure_overlay()
            if ov:
                ov.show(self._overlay_message)

        # 2) ProgressToast (mesmo com overlay, se tiver texto)
        if self._progress_text:
            self._pt = ProgressToast.start(
                self.window(),
                self._progress_text,
                kind=self._progress_kind,
                cancellable=self._progress_cancellable,
            )
            self._pt.set_indeterminate(True)
        else:
            # fallback mínimo quando não há progress toast
            if not self._use_overlay:
                self.setText("Executando…")

        job = _TaskRunnable(self._runner.run_task, self._cmd, self._payload)
        job.signals.finished.connect(self._finish)
        self._pool.start(job)

    def _finish(self, result: dict):
        # encerra overlay
        if self._overlay:
            self._overlay.hide()

        code = _extract_code(result)
        ok = (code == 1)
        warn = (code == 2)
        err_msg = result.get("error", "") or "Erro desconhecido"

        # fecha/finaliza progress toast (se houver)
        if self._pt is not None:
            if ok:
                self._pt.finish(True, self._t_succ or "Concluído")
            elif warn:
                self._pt.finish(False, self._t_fail or "Falha no processo")
            else:
                self._pt.finish(False, (self._t_err or "Erro") + (f": {err_msg}" if err_msg else ""))
            self._pt = None
        else:
            # Sem progress toast → toasts curtos de resultado
            if ok:
                if self._t_succ:
                    show_toast(self.window(), self._t_succ, "success", 2000)
            elif warn:
                if self._t_fail:
                    show_toast(self.window(), f"{self._t_fail}", "warn", 2400)
            else:
                if self._t_err:
                    show_toast(self.window(), f"{self._t_err}: {err_msg}", "error", 2600)

        # restaura o botão
        self.setEnabled(True)
        self.setText(self._orig_text)

        if callable(self._on_done):
            try:
                self._on_done(result)
            except Exception:
                pass
