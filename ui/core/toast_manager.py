# ui/core/toast_manager.py

from __future__ import annotations
from dataclasses import dataclass, field
from typing import List, Dict, Optional
from datetime import datetime
from PySide6.QtCore import QObject, Signal

from .router import Router
from .command_bus import CommandBus
from .settings import Settings

VALID_TYPES = {"info", "ok", "warning", "error"}

@dataclass
class Toast:
    type: str
    title: str
    text: str
    actions: List[Dict] = field(default_factory=list)
    sticky: bool = False
    persist: bool = False
    ts: str = field(default_factory=lambda: datetime.now().isoformat(timespec="seconds"))
    read: bool = False

class ToastManager(QObject):
    changed = Signal()
    unreadCountChanged = Signal(int)

    _instance: "ToastManager" | None = None

    def __init__(self, router: Router, command_bus: CommandBus, settings: Settings, storage_filename: str = "_ui_toasts.json"):
        super().__init__()
        self._router = router
        self._bus = command_bus
        self._settings = settings
        self._storage_path = settings.path.parent / storage_filename
        self._toasts: List[Toast] = []
        self._unread = 0
        self._load()

    # ---------- singleton ----------
    @classmethod
    def install(cls, router: Router, command_bus: CommandBus, settings: Settings) -> "ToastManager":
        if cls._instance is None:
            cls._instance = ToastManager(router, command_bus, settings)
        return cls._instance

    @classmethod
    def instance(cls) -> "ToastManager":
        if cls._instance is None:
            raise RuntimeError("ToastManager não instalado. Chame install() primeiro.")
        return cls._instance

    # ---------- API pública ----------
    def notify(self, *, type: str, title: str, text: str,
               actions: Optional[List[Dict]] = None, sticky: bool = False, persist: bool = False) -> None:
        t = type.lower().strip()
        if t not in VALID_TYPES:
            t = "info"
        actions = actions or []
        toast = Toast(type=t, title=title, text=text, actions=actions, sticky=sticky, persist=persist)
        self._toasts.insert(0, toast)  # mais recente primeiro
        self._unread += 1
        print("log.toast.show", {"type": t, "title": title, "ts": toast.ts})
        self._enforce_limit_and_maybe_persist(toast)
        self.changed.emit()
        self.unreadCountChanged.emit(self._unread)

    def list(self) -> List[Toast]:
        return list(self._toasts)

    def clear(self) -> None:
        self._toasts.clear()
        self._unread = 0
        self._save()
        self.changed.emit()
        self.unreadCountChanged.emit(self._unread)

    def markAllRead(self) -> None:
        for t in self._toasts:
            t.read = True
        self._unread = 0
        self.unreadCountChanged.emit(self._unread)
        self._save()

    # usado pela página para executar ações
    def trigger_action(self, toast: Toast, action: Dict) -> None:
        a = dict(action or {})
        if "route" in a and a["route"]:
            self._router.go(str(a["route"]), dict(a.get("payload") or {}))
            print("log.toast.action", {"kind": "route", "route": a["route"], "ts": datetime.now().isoformat()})
        elif "command" in a and a["command"]:
            res = self._bus.dispatch(str(a["command"]), dict(a.get("payload") or {}))
            print("log.toast.action", {"kind": "command", "command": a["command"], "ok": res.get("ok", False), "ts": datetime.now().isoformat()})

    # ---------- persistência ----------
    def _enforce_limit_and_maybe_persist(self, last: Toast) -> None:
        max_saved = self._settings.get_int("toast.max_saved", 50)
        persist_enabled = self._settings.get_bool("toast.persist_enabled", True)
        # corta excesso
        if len(self._toasts) > max_saved:
            self._toasts = self._toasts[:max_saved]
        if persist_enabled and last.persist:
            self._save()

    def _load(self) -> None:
        try:
            if self._storage_path.exists():
                import json
                data = json.loads(self._storage_path.read_text(encoding="utf-8"))
                self._toasts = [Toast(**item) for item in data if isinstance(item, dict)]
                # unread baseado nos que não estão marcados como read
                self._unread = sum(1 for t in self._toasts if not t.read)
        except Exception as e:
            print("[WARN] falha ao carregar toasts:", e)
            self._toasts = []
            self._unread = 0

    def _save(self) -> None:
        try:
            import json
            payload = [t.__dict__ for t in self._toasts]
            self._storage_path.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")
        except Exception as e:
            print("[WARN] falha ao salvar toasts:", e)
