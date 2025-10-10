# ui/widgets/async_button.py

from __future__ import annotations
from typing import Dict, Any, Optional, Callable

from PySide6.QtCore import QObject, Signal, QRunnable, QThreadPool
from PySide6.QtWidgets import QMessageBox

from .buttons import HoverButton
from .toast import show_toast

# --- Worker infra ---
class _TaskSignals(QObject):
    finished = Signal(dict)   # payload: result dict {ok, data?, error?}

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
            res = {"ok": False, "error": str(e)}
        self.signals.finished.emit(res)

# --- AsyncTaskButton ---
class AsyncTaskButton(HoverButton):
    def __init__(
        self,
        text: str,
        task_runner,
        command_name: str,
        payload: Optional[Dict[str, Any]] = None,
        parent=None,
        on_done: Optional[Callable[[dict], None]] = None,
        toast_success: Optional[str] = "Concluído",
        toast_error: Optional[str]   = "Falha"
    ):
        super().__init__(text, parent)
        self._runner = task_runner
        self._cmd = command_name
        self._payload = payload or {}
        self._on_done = on_done
        self._t_succ = toast_success
        self._t_err  = toast_error
        self._orig_text = text
        self._pool = QThreadPool.globalInstance()

        self.clicked.connect(self._kickoff)

    def _kickoff(self):
        if not hasattr(self._runner, "run_task"):
            QMessageBox.warning(self, "Erro", "Runner inválido.")
            return
        self.setEnabled(False); self.setText("Executando…")
        job = _TaskRunnable(self._runner.run_task, self._cmd, self._payload)
        job.signals.finished.connect(self._finish)
        self._pool.start(job)

    def _finish(self, result: dict):
        self.setEnabled(True); self.setText(self._orig_text)
        ok = bool(result.get("ok"))
        if ok and self._t_succ:
            show_toast(self.window(), self._t_succ, "success", 2000)
        if not ok and self._t_err:
            show_toast(self.window(), f"{self._t_err}: {result.get('error','')}", "error", 2600)
        if callable(self._on_done):
            try: self._on_done(result)
            except: pass
