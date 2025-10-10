# ui/core/command_bus.py

from typing import Callable, Dict, Any, Optional

class CommandBus:
    def __init__(self):
        self._handlers: Dict[str, Callable[[Dict[str, Any]], Dict[str, Any]]] = {}

    def register(self, name: str, handler: Callable[[Dict[str, Any]], Dict[str, Any]]) -> None:
        if name in self._handlers:
            raise ValueError(f"Command '{name}' já registrado")
        self._handlers[name] = handler

    def dispatch(self, name: str, payload: Optional[Dict[str, Any]] = None) -> Dict[str, Any]:
        if name not in self._handlers:
            return {"ok": False, "error": f"Comando '{name}' não encontrado"}
        try:
            return self._handlers[name](payload or {})
        except Exception as exc:
            return {"ok": False, "error": str(exc)}
